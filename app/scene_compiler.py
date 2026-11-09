from __future__ import annotations

import ast
import re
import textwrap
from dataclasses import dataclass

from app.scene_plan import SceneBeat, ScenePlan, VisualAction, VisualKind


SAFE_FRAME = (-6.2, 6.2, -3.55, 3.55)
LAYOUT_REGIONS = {
    "title": (-5.9, 5.9, 2.98, 3.54),
    "visual": (-6.0, 1.25, -3.05, 2.55),
    "sidebar": (2.15, 6.0, -3.05, 2.55),
}

_ALLOWED_NAMES = {"x", "pi", "e"}
_ALLOWED_FUNCTIONS = {"sin", "cos", "tan", "exp", "log", "sqrt", "abs"}
_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.USub,
    ast.UAdd,
)


class SceneCompilationError(ValueError):
    pass


@dataclass(frozen=True)
class CompiledScene:
    code: str
    layout_issues: tuple[str, ...]


def compile_scene(plan: ScenePlan) -> CompiledScene:
    issues = validate_layout_regions()
    if issues:
        raise SceneCompilationError("; ".join(issues))

    expression = None
    if plan.visual_kind == VisualKind.GRAPH:
        assert plan.function_expression is not None
        expression = _compile_expression(plan.function_expression)

    code = _render_code(plan, expression)
    compile(code, "<compiled_scene>", "exec")
    return CompiledScene(code=code, layout_issues=())


def validate_layout_regions() -> tuple[str, ...]:
    issues: list[str] = []
    frame_left, frame_right, frame_bottom, frame_top = SAFE_FRAME
    for name, (left, right, bottom, top) in LAYOUT_REGIONS.items():
        if left < frame_left or right > frame_right or bottom < frame_bottom or top > frame_top:
            issues.append(f"{name} region exceeds the safe frame")

    names = list(LAYOUT_REGIONS)
    for index, first_name in enumerate(names):
        for second_name in names[index + 1 :]:
            if _rectangles_overlap(LAYOUT_REGIONS[first_name], LAYOUT_REGIONS[second_name]):
                issues.append(f"{first_name} and {second_name} regions overlap")
    return tuple(issues)


def _rectangles_overlap(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
    padding: float = 0.12,
) -> bool:
    first_left, first_right, first_bottom, first_top = first
    second_left, second_right, second_bottom, second_top = second
    return not (
        first_right + padding <= second_left
        or second_right + padding <= first_left
        or first_top + padding <= second_bottom
        or second_top + padding <= first_bottom
    )


def _compile_expression(expression: str) -> str:
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:
        raise SceneCompilationError("function_expression is not valid Python syntax") from exc

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise SceneCompilationError(
                f"function_expression contains unsupported syntax: {type(node).__name__}"
            )
        if isinstance(node, ast.Name):
            if node.id not in _ALLOWED_NAMES | _ALLOWED_FUNCTIONS:
                raise SceneCompilationError(f"unsupported expression name: {node.id}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCTIONS:
                raise SceneCompilationError("only approved math functions may be called")
            if len(node.args) != 1 or node.keywords:
                raise SceneCompilationError("math functions must receive exactly one argument")

    transformed = _NumpyFunctionTransformer().visit(tree)
    ast.fix_missing_locations(transformed)
    return ast.unparse(transformed.body)


class _NumpyFunctionTransformer(ast.NodeTransformer):
    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id in _ALLOWED_FUNCTIONS:
            function_name = "absolute" if node.id == "abs" else node.id
            return ast.copy_location(
                ast.Attribute(value=ast.Name(id="np", ctx=ast.Load()), attr=function_name, ctx=node.ctx),
                node,
            )
        if node.id == "pi":
            return ast.copy_location(
                ast.Attribute(value=ast.Name(id="np", ctx=ast.Load()), attr="pi", ctx=node.ctx),
                node,
            )
        if node.id == "e":
            return ast.copy_location(
                ast.Attribute(value=ast.Name(id="np", ctx=ast.Load()), attr="e", ctx=node.ctx),
                node,
            )
        return node


def _render_code(plan: ScenePlan, expression: str | None) -> str:
    title = repr(_title_latex(plan.title))
    if plan.visual_kind == VisualKind.GRAPH:
        body = _render_graph_body(plan, expression or "x")
    else:
        body = _render_equation_body(plan)

    return f'''from manim import *


SAFE_LEFT = -6.2
SAFE_RIGHT = 6.2
SAFE_BOTTOM = -3.55
SAFE_TOP = 3.55
VISUAL_CENTER = LEFT * 2.375 + DOWN * 0.25
SIDEBAR_CENTER = RIGHT * 4.075 + DOWN * 0.25
VISUAL_WIDTH = 7.05
VISUAL_HEIGHT = 5.35
SIDEBAR_WIDTH = 3.55
SIDEBAR_HEIGHT = 5.20
PACE = 1.5


def fit_to_box(mobject, width, height):
    if mobject.width > width:
        mobject.scale_to_fit_width(width)
    if mobject.height > height:
        mobject.scale_to_fit_height(height)
    return mobject


def place_point_label(tex, point, visual, direction):
    label = fit_to_box(MathTex(tex, font_size=24), 2.6, 0.55)
    label.next_to(point, direction, buff=0.13)
    label.set_x(np.clip(
        label.get_center()[0],
        visual.get_left()[0] + label.width / 2 + 0.05,
        visual.get_right()[0] - label.width / 2 - 0.05,
    ))
    label.set_y(np.clip(
        label.get_center()[1],
        visual.get_bottom()[1] + label.height / 2 + 0.05,
        visual.get_top()[1] - label.height / 2 - 0.05,
    ))
    return label


def place_converging_label(tex, point, visual, direction, separation):
    label = place_point_label(tex, point, visual, direction)
    label.set_opacity(float(np.clip((separation - 0.08) / 0.25, 0.0, 1.0)))
    return label


def boxes_overlap(first, second, padding=0.12):
    return not (
        first.get_right()[0] + padding <= second.get_left()[0]
        or second.get_right()[0] + padding <= first.get_left()[0]
        or first.get_top()[1] + padding <= second.get_bottom()[1]
        or second.get_top()[1] + padding <= first.get_bottom()[1]
    )


def validate_layout(named_mobjects):
    for name, mobject in named_mobjects.items():
        if (
            mobject.get_left()[0] < SAFE_LEFT
            or mobject.get_right()[0] > SAFE_RIGHT
            or mobject.get_bottom()[1] < SAFE_BOTTOM
            or mobject.get_top()[1] > SAFE_TOP
        ):
            raise ValueError(f"{{name}} exceeds the safe frame")

    names = list(named_mobjects)
    for index, first_name in enumerate(names):
        for second_name in names[index + 1:]:
            if boxes_overlap(named_mobjects[first_name], named_mobjects[second_name]):
                raise ValueError(f"{{first_name}} overlaps {{second_name}}")


def validate_inside_visual(mobject, visual, padding=0.08):
    if (
        mobject.get_left()[0] < visual.get_left()[0] - padding
        or mobject.get_right()[0] > visual.get_right()[0] + padding
        or mobject.get_bottom()[1] < visual.get_bottom()[1] - padding
        or mobject.get_top()[1] > visual.get_top()[1] + padding
    ):
        raise ValueError("graph overlay exceeds the visual region")


class GeneratedScene(Scene):
    def construct(self):
        title = fit_to_box(MathTex({title}, font_size=34), 11.8, 0.56)
        title.move_to(UP * 3.26)
{textwrap.indent(body, '        ')}
'''


def _title_latex(title: str) -> str:
    value = title.strip()
    if "\\text{" in value:
        return value

    has_math = re.search(r"[\\^_=<>|]", value) is not None
    if not has_math:
        escaped = value.replace("\\", r"\\textbackslash{}")
        escaped = escaped.replace("{", r"\{").replace("}", r"\}")
        return rf"\text{{{escaped}}}"

    mixed_title = re.fullmatch(
        r"(Why|How|When)\s+(.+?)(?:\s+(for|when|where)\s+(.+))?", value
    )
    if mixed_title:
        lead, formula, connector, condition = mixed_title.groups()
        if connector is None:
            return rf"\text{{{lead} }}{formula}"
        return rf"\text{{{lead} }}{formula}\text{{ {connector} }}{condition}"
    return value


def _render_graph_body(plan: ScenePlan, expression: str) -> str:
    x_range = repr(list(plan.x_range))
    y_range = repr(list(plan.y_range))
    beat_blocks = "\n".join(
        _render_graph_beat(plan, beat, index) for index, beat in enumerate(plan.beats)
    )
    return f'''function = lambda x: {expression}
axes = Axes(
    x_range={x_range},
    y_range={y_range},
    x_length=6.85,
    y_length=4.85,
    tips=False,
    axis_config={{"include_numbers": False, "stroke_width": 2}},
)
graph = axes.plot(function, color=BLUE, stroke_width=4)
visual = VGroup(axes, graph)
fit_to_box(visual, VISUAL_WIDTH, VISUAL_HEIGHT)
visual.move_to(VISUAL_CENTER)

sidebar_probe = Rectangle(width=SIDEBAR_WIDTH, height=SIDEBAR_HEIGHT)
sidebar_probe.set_stroke(opacity=0).set_fill(opacity=0)
sidebar_probe.move_to(SIDEBAR_CENTER)
validate_layout({{"title": title, "visual": visual, "sidebar": sidebar_probe}})

self.play(Write(title), run_time=0.7 * PACE)
graph_visible = False
current_overlay = None
current_sidebar = None
{beat_blocks}
self.wait(0.6 * PACE)'''


def _render_graph_beat(plan: ScenePlan, beat: SceneBeat, index: int) -> str:
    formula = repr(beat.formula)
    explanation = repr(_explanation_tex(beat.explanation))
    action_code = _graph_action_code(plan, beat, index)
    reading_time = _reading_time(beat)
    clear_overlay = ""
    if beat.action not in {VisualAction.SHOW_GRAPH, VisualAction.SHOW_FORMULA}:
        clear_overlay = '''if current_overlay is not None:
    self.play(FadeOut(current_overlay), run_time=0.3 * PACE)
    current_overlay = None'''
    return f'''# Beat {index + 1}
formula_{index} = fit_to_box(MathTex({formula}), SIDEBAR_WIDTH, 1.35)
explanation_{index} = fit_to_box(
    Tex({explanation}, font_size=23), SIDEBAR_WIDTH, 2.8
)
sidebar_{index} = VGroup(formula_{index}, explanation_{index}).arrange(DOWN, buff=0.45)
fit_to_box(sidebar_{index}, SIDEBAR_WIDTH, SIDEBAR_HEIGHT)
sidebar_{index}.move_to(SIDEBAR_CENTER)
validate_layout(dict(title=title, visual=visual, sidebar=sidebar_{index}))

{clear_overlay}
if not graph_visible:
    self.play(Create(axes), Create(graph), run_time=1.0 * PACE)
    graph_visible = True
if current_sidebar is None:
    self.play(FadeIn(sidebar_{index}), run_time=0.55 * PACE)
else:
    self.play(FadeTransform(current_sidebar, sidebar_{index}), run_time=0.55 * PACE)
current_sidebar = sidebar_{index}
{action_code}
self.wait({reading_time!r})'''


def _graph_action_code(plan: ScenePlan, beat: SceneBeat, index: int) -> str:
    if beat.action in {VisualAction.SHOW_GRAPH, VisualAction.SHOW_FORMULA}:
        return ""
    if beat.action == VisualAction.SHOW_POINT:
        label_code = ""
        label_item = ""
        if beat.point_label:
            label_code = f'''point_label_{index} = place_point_label(
    {beat.point_label!r}, point_{index}.get_center(), visual, UR
)'''
            label_item = f", point_label_{index}"
        return f'''x_value = {beat.x_value!r}
point_{index} = Dot(axes.c2p(x_value, function(x_value)), color=YELLOW, radius=0.09)
{label_code}
overlay_{index} = VGroup(point_{index}{label_item})
validate_inside_visual(overlay_{index}, visual)
self.play(FadeIn(overlay_{index}), run_time=0.45 * PACE)
current_overlay = overlay_{index}'''
    if beat.action == VisualAction.SHOW_SECANT:
        label_code = ""
        label_items: list[str] = []
        if beat.point_label:
            label_code += f'''first_label_{index} = place_point_label(
    {beat.point_label!r}, first_point, visual, first_label_direction
)
'''
            label_items.append(f"first_label_{index}")
        if beat.second_point_label:
            label_code += f'''second_label_{index} = place_point_label(
    {beat.second_point_label!r}, second_point, visual, second_label_direction
)
'''
            label_items.append(f"second_label_{index}")
        label_arguments = "".join(f", {item}" for item in label_items)
        return f'''x_first = {beat.x_value!r}
x_second = {beat.second_x_value!r}
first_point = axes.c2p(x_first, function(x_first))
second_point = axes.c2p(x_second, function(x_second))
first_dot = Dot(first_point, color=YELLOW, radius=0.08)
second_dot = Dot(second_point, color=YELLOW, radius=0.08)
secant_line = Line(first_point, second_point, color=YELLOW, stroke_width=4)
slope_rises = second_point[1] >= first_point[1]
first_label_direction = UL if slope_rises else DL
second_label_direction = DR if slope_rises else UR
{label_code}overlay_{index} = VGroup(
    secant_line,
    first_dot,
    second_dot{label_arguments},
)
validate_inside_visual(overlay_{index}, visual)
self.play(FadeIn(overlay_{index}), run_time=0.55 * PACE)
current_overlay = overlay_{index}'''
    if beat.action == VisualAction.SLIDE_SECANT:
        label_code = ""
        label_items: list[str] = []
        if beat.point_label:
            label_code += f'''fixed_label_{index} = place_point_label(
    {beat.point_label!r}, fixed_point, visual, fixed_label_direction
)
'''
            label_items.append(f"fixed_label_{index}")
        if beat.second_point_label:
            label_code += f'''moving_label_{index} = always_redraw(
    lambda: place_converging_label(
        {beat.second_point_label!r},
        moving_point(),
        visual,
        moving_label_direction,
        abs(moving_x_{index}.get_value() - fixed_x),
    )
)
'''
            label_items.append(f"moving_label_{index}")
        label_arguments = "".join(f", {item}" for item in label_items)
        return f'''fixed_x = {beat.x_value!r}
moving_x_{index} = ValueTracker({beat.second_x_value!r})
fixed_point = axes.c2p(fixed_x, function(fixed_x))
moving_point = lambda: axes.c2p(
    moving_x_{index}.get_value(), function(moving_x_{index}.get_value())
)
fixed_dot = Dot(fixed_point, color=YELLOW, radius=0.08)
moving_dot = always_redraw(lambda: Dot(moving_point(), color=YELLOW, radius=0.08))
secant_line = always_redraw(
    lambda: Line(fixed_point, moving_point(), color=YELLOW, stroke_width=4)
)
slope_rises = moving_point()[1] >= fixed_point[1]
fixed_label_direction = UL if slope_rises else DL
moving_label_direction = DR if slope_rises else UR
{label_code}overlay_{index} = VGroup(
    secant_line,
    fixed_dot,
    moving_dot{label_arguments},
)
validate_inside_visual(overlay_{index}, visual)
self.play(FadeIn(overlay_{index}), run_time=0.55 * PACE)
self.play(
    moving_x_{index}.animate.set_value({beat.target_x_value!r}),
    run_time=2.4 * PACE,
    rate_func=smooth,
)
current_overlay = overlay_{index}'''
    if beat.action == VisualAction.SHOW_TANGENT:
        label_code = ""
        label_item = ""
        if beat.point_label:
            label_code = f'''tangent_label_{index} = place_point_label(
    {beat.point_label!r}, tangent_dot.get_center(), visual, UR
)'''
            label_item = f", tangent_label_{index}"
        return f'''x_value = {beat.x_value!r}
h = 1e-3
slope = (function(x_value + h) - function(x_value - h)) / (2 * h)
x_left = max({plan.x_range[0]!r}, x_value - 1.15)
x_right = min({plan.x_range[1]!r}, x_value + 1.15)
y_value = function(x_value)
if abs(slope) > 1e-9:
    y_padding = ({plan.y_range[1]!r} - {plan.y_range[0]!r}) * 0.02
    y_limited_x = sorted([
        x_value + ({plan.y_range[0]!r} + y_padding - y_value) / slope,
        x_value + ({plan.y_range[1]!r} - y_padding - y_value) / slope,
    ])
    x_left = max(x_left, y_limited_x[0])
    x_right = min(x_right, y_limited_x[1])
tangent = Line(
    axes.c2p(x_left, y_value + slope * (x_left - x_value)),
    axes.c2p(x_right, y_value + slope * (x_right - x_value)),
    color=YELLOW,
    stroke_width=4,
)
tangent_dot = Dot(axes.c2p(x_value, function(x_value)), color=YELLOW)
{label_code}
overlay_{index} = VGroup(tangent, tangent_dot{label_item})
validate_inside_visual(overlay_{index}, visual)
self.play(FadeIn(overlay_{index}), run_time=0.55 * PACE)
current_overlay = overlay_{index}'''
    if beat.action == VisualAction.SHOW_AREA:
        return f'''overlay_{index} = axes.get_area(
    graph,
    x_range=[{beat.interval_start!r}, {beat.interval_end!r}],
    color=TEAL,
    opacity=0.38,
)
validate_inside_visual(overlay_{index}, visual)
self.play(FadeIn(overlay_{index}), run_time=0.55 * PACE)
current_overlay = overlay_{index}'''
    if beat.action == VisualAction.SHOW_RIEMANN:
        return f'''overlay_{index} = axes.get_riemann_rectangles(
    graph,
    x_range=[{beat.interval_start!r}, {beat.interval_end!r}],
    dx={beat.dx!r},
    stroke_width=1,
    fill_opacity=0.45,
    color=[TEAL, BLUE],
)
validate_inside_visual(overlay_{index}, visual)
self.play(FadeIn(overlay_{index}), run_time=0.65 * PACE)
current_overlay = overlay_{index}'''
    raise SceneCompilationError(f"unsupported graph action: {beat.action.value}")


def _render_equation_body(plan: ScenePlan) -> str:
    blocks: list[str] = []
    for index, beat in enumerate(plan.beats):
        formula = repr(beat.formula)
        explanation = repr(_explanation_tex(beat.explanation))
        reading_time = _reading_time(beat)
        blocks.append(
            f'''formula_{index} = fit_to_box(MathTex({formula}), VISUAL_WIDTH, VISUAL_HEIGHT)
formula_{index}.move_to(VISUAL_CENTER)
explanation_{index} = fit_to_box(
    Tex({explanation}, font_size=24), SIDEBAR_WIDTH, SIDEBAR_HEIGHT
)
explanation_{index}.move_to(SIDEBAR_CENTER)
validate_layout(dict(title=title, visual=formula_{index}, sidebar=explanation_{index}))
if current_formula is None:
    self.play(Write(formula_{index}), FadeIn(explanation_{index}), run_time=0.75 * PACE)
else:
    self.play(
        ReplacementTransform(current_formula, formula_{index}),
        FadeOut(current_explanation),
        FadeIn(explanation_{index}),
        run_time=0.75 * PACE,
    )
current_formula = formula_{index}
current_explanation = explanation_{index}
self.wait({reading_time!r})'''
        )
    return f'''self.play(Write(title), run_time=0.7 * PACE)
current_formula = None
current_explanation = None
{chr(10).join(blocks)}
self.wait(0.6 * PACE)'''


def _wrapped_text(value: str) -> str:
    return "\n".join(textwrap.wrap(value, width=29, break_long_words=False, break_on_hyphens=False))


_EXPLANATION_MATH = re.compile(
    r"\$[^$]+\$|sqrt\([^()]+\)|\b[A-Za-z](?:\([A-Za-z]\))?\^[+-]?\d+(?:\.\d+)?\b|\b(?:dx|dy|dz|pi)\b"
)


def _explanation_tex(value: str) -> str:
    """Render prose through LaTeX while preserving common inline mathematics."""
    math_fragments: list[str] = []

    def protect(match: re.Match[str]) -> str:
        token = match.group(0)
        if token.startswith("$"):
            latex = token[1:-1]
        else:
            latex = _plain_math_to_latex(token)
        marker = f"ANIMATHMATHTOKEN{len(math_fragments)}END"
        math_fragments.append(latex)
        return marker

    protected = _EXPLANATION_MATH.sub(protect, _wrapped_text(value))
    escaped = _escape_tex_text(protected).replace("\n", r"\\")
    for index, fragment in enumerate(math_fragments):
        escaped = escaped.replace(f"ANIMATHMATHTOKEN{index}END", f"${fragment}$")
    return escaped


def _plain_math_to_latex(value: str) -> str:
    sqrt_match = re.fullmatch(r"sqrt\(([^()]+)\)", value)
    if sqrt_match:
        return rf"\sqrt{{{sqrt_match.group(1)}}}"
    value = re.sub(r"\^([+-]?\d+(?:\.\d+)?)", r"^{\1}", value)
    if value == "pi":
        return r"\pi"
    return value


def _escape_tex_text(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in value)


def _reading_time(beat: SceneBeat) -> float:
    explanation_words = len(beat.explanation.split())
    formula_units = max(1, len(beat.formula) // 12)
    return round(min(6.0, max(3.0, (explanation_words + formula_units) / 3.2)), 2)
