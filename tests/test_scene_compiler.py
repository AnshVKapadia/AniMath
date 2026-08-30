from __future__ import annotations

import unittest

from app.scene_compiler import SceneCompilationError, compile_scene, validate_layout_regions
from app.scene_plan import ScenePlan


def graph_plan(expression: str = "x**2") -> ScenePlan:
    return ScenePlan.model_validate(
        {
            "title": "Derivative at a point",
            "visual_kind": "graph",
            "function_expression": expression,
            "x_range": [-3, 3, 1],
            "y_range": [-1, 6, 1],
            "beats": [
                {
                    "formula": "f(x)=x^2",
                    "explanation": "Start with the graph.",
                    "action": "show_graph",
                },
                {
                    "formula": "f'(1)=2",
                    "explanation": "The tangent has slope two.",
                    "action": "show_tangent",
                    "x_value": 1,
                },
            ],
        }
    )


def labeled_secant_plan() -> ScenePlan:
    return ScenePlan.model_validate(
        {
            "title": "Formal derivative definition",
            "visual_kind": "graph",
            "function_expression": "x**2",
            "x_range": [-2, 4, 1],
            "y_range": [-1, 16, 2],
            "beats": [
                {
                    "formula": "f(x)=x^2",
                    "explanation": "Start with the parabola.",
                    "action": "show_graph",
                },
                {
                    "formula": "m=\\frac{f(x+h)-f(x)}{h}",
                    "explanation": "Use two nearby points to form a secant.",
                    "action": "slide_secant",
                    "x_value": 1,
                    "second_x_value": 2,
                    "target_x_value": 1.2,
                    "point_label": "(x,f(x))",
                    "second_point_label": "(x+h,f(x+h))",
                },
            ],
        }
    )


class SceneCompilerTests(unittest.TestCase):
    def test_reserved_regions_do_not_overlap(self) -> None:
        self.assertEqual(validate_layout_regions(), ())

    def test_compiled_scene_is_valid_python_with_runtime_checks(self) -> None:
        compiled = compile_scene(graph_plan())

        compile(compiled.code, "scene.py", "exec")
        self.assertIn("validate_layout", compiled.code)
        self.assertIn("PACE = 1.5", compiled.code)
        self.assertIn("run_time=0.7 * PACE", compiled.code)
        self.assertIn("y_limited_x", compiled.code)
        self.assertNotIn("colors=[TEAL, BLUE]", compiled.code)
        self.assertIn("VISUAL_CENTER", compiled.code)
        self.assertNotIn(".to_edge(", compiled.code)
        self.assertNotIn(".to_corner(", compiled.code)
        self.assertIn("MathTex('\\\\text{Derivative at a point}'", compiled.code)

    def test_mixed_math_title_renders_latex_instead_of_literal_commands(self) -> None:
        plan = graph_plan().model_copy(
            update={"title": r"Why 1+r+r^2+\cdots=\frac{1}{1-r} for |r|<1"}
        )

        compiled = compile_scene(plan)

        self.assertIn(
            r"\\text{Why }1+r+r^2+\\cdots=\\frac{1}{1-r}\\text{ for }|r|<1",
            compiled.code,
        )
        self.assertNotIn("title = fit_to_box(Text(", compiled.code)

    def test_math_functions_are_translated_to_numpy(self) -> None:
        compiled = compile_scene(graph_plan("sin(x) + exp(-x**2)"))

        self.assertIn("np.sin(x)", compiled.code)
        self.assertIn("np.exp(-x ** 2)", compiled.code)

    def test_secant_point_labels_use_controlled_placement(self) -> None:
        compiled = compile_scene(labeled_secant_plan())

        self.assertIn("place_point_label", compiled.code)
        self.assertIn("'(x,f(x))'", compiled.code)
        self.assertIn("'(x+h,f(x+h))'", compiled.code)
        self.assertIn("fixed_label_direction", compiled.code)
        self.assertIn("ValueTracker(2.0)", compiled.code)
        self.assertIn("animate.set_value(1.2)", compiled.code)
        self.assertIn("run_time=2.4 * PACE", compiled.code)
        self.assertIn("self.wait(3.0)", compiled.code)

    def test_unsafe_expression_is_rejected(self) -> None:
        with self.assertRaises(SceneCompilationError):
            compile_scene(graph_plan("__import__('os').system('echo nope')"))


if __name__ == "__main__":
    unittest.main()
