from __future__ import annotations

import json
from textwrap import dedent

from openai import OpenAI

from app.config import get_settings
from app.scene_plan import ScenePlan, VisualAction


SYSTEM_PROMPT = dedent(
    """
    You generate short, valid Manim Community Edition scenes for a teacher-facing
    calculus visualization tool.

    Hard requirements:
    - Return only Python code. No markdown fences. No explanations.
    - Use only `from manim import *`.
    - Define exactly one scene class named `GeneratedScene(Scene)`.
    - Keep the animation short and classroom-friendly, roughly 15 to 45 seconds.
    - Focus on common calculus concepts: limits, derivatives, tangent lines,
      integrals, Riemann sums, and simple series intuition.
    - Prioritize mathematical correctness and valid Manim syntax.
    - Use readable labels, simple color choices, and uncluttered layouts.
    - Avoid external files, images, network calls, random data, or unsupported libraries.
    - Do not use LaTeX packages or advanced dependencies beyond standard Manim.
    - Do not use TexTemplate, tex_template customization, MathTex template overrides,
      dvisvgm options, or any custom LaTeX compiler configuration.
    - Keep imports limited to `from manim import *`.
    - Ensure the scene can render on a default Manim installation.

    Implementation guidance:
    - Prefer Axes, NumberPlane, MathTex, Tex, ValueTracker, Dot, Line, Brace,
      Rectangle, and simple transforms/fades.
    - Use default MathTex or simple Text/Tex only. Never construct or modify TexTemplate.
    - Use clear pacing and a compact construct() method.
    - If text rendering could be fragile, prefer MathTex for formulas and minimal Tex usage.
    - Avoid very dense code and avoid referencing undefined variables.
    """
).strip()


REPAIR_PROMPT = dedent(
    """
    The following Manim code failed to render. Fix it so it satisfies the original
    request and renders successfully.

    Return only corrected Python code with:
    - exactly one `GeneratedScene(Scene)` class
    - only `from manim import *`
    - no markdown or commentary
    - no TexTemplate usage or LaTeX template customization
    """
).strip()


SCENE_PLANNER_PROMPT = dedent(
    """
    You design short, mathematically correct calculus animations for a controlled
    Manim compiler. Return only one JSON object. Do not return Python, markdown,
    narration, comments, or keys outside the schema described below.

    The compiler owns all coordinates, sizing, transitions, and collision handling.
    Your job is to choose the teaching sequence and semantic visual actions.

    Schema:
    {
      "title": "short LaTeX title without dollar signs, at most 72 characters",
      "visual_kind": "graph" or "equation",
      "function_expression": "safe Python expression in x" or null,
      "x_range": [minimum, maximum, positive_step],
      "y_range": [minimum, maximum, positive_step],
      "beats": [
        {
          "formula": "short LaTeX formula without dollar signs",
          "explanation": "one short sentence, at most 150 characters",
          "action": "show_graph", "show_point", "show_secant",
                    "slide_secant", "show_tangent", "show_area",
                    "show_riemann", or "show_formula",
          "x_value": number or null,
          "second_x_value": number or null,
          "target_x_value": number or null,
          "interval_start": number or null,
          "interval_end": number or null,
          "dx": positive number or null,
          "point_label": "optional short LaTeX point label" or null,
          "second_point_label": "optional short LaTeX point label" or null
        }
      ]
    }

    Rules:
    - Write title as valid MathTex. Wrap every prose fragment in \\text{...}; for
      example, \\text{Why }1+r+r^2+\\cdots=\\frac{1}{1-r}\\text{ for }|r|<1.
    - Use 4 to 8 beats when the request contains a derivation. Use exactly 8
      for formal definitions and 7 or 8 for other multi-step algebra. Simpler visual intuition
      may use 3 or 4 beats.
    - Keep formulas compact and explanations concrete.
    - Never skip a meaningful algebra step. Each beat should perform one clear
      operation, such as substitution, expansion, cancellation, evaluation,
      or taking a limit. Show the intermediate formula after that operation.
    - For a formal derivative, use separate beats for the definition,
      substitution, expansion, combining or canceling like terms, factoring the
      common h, canceling h, taking the limit, and stating the result. Never
      combine factoring and cancellation into the same beat.
    - For graph plans, function_expression may use x, numbers, arithmetic, powers,
      sin, cos, tan, exp, log, sqrt, abs, pi, and e.
    - Graph plans may use show_formula for algebra-only beats. This keeps the
      current graph overlay visible while the sidebar formula changes.
    - Equation plans must use show_formula for every beat and set
      function_expression to null.
    - show_point and show_tangent require x_value.
    - show_secant requires two different x values.
    - slide_secant requires x_value, second_x_value, and target_x_value. The
      target must be closer to x_value and models a secant approaching a tangent.
      Use it whenever motion helps explain a limiting process.
    - For secants, use point_label and second_point_label when named coordinates
      clarify the reasoning, such as (x,f(x)) and (x+h,f(x+h)).
    - show_point and show_tangent may use point_label for the highlighted point.
    - Keep point labels short; omit them when they do not add teaching value.
    - show_area requires interval_start and interval_end.
    - show_riemann requires interval_start, interval_end, and dx.
    - Keep action values inside the axis ranges.
    - Prefer an equation plan when the concept does not need a coordinate graph.
    - Never put prose in formula and never put LaTeX commands in explanation.
    """
).strip()


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        foundry_values = (
            settings.azure_openai_api_key,
            settings.azure_openai_base_url,
            settings.azure_openai_deployment,
        )
        if any(foundry_values):
            if not all(foundry_values):
                raise ValueError(
                    "AZURE_OPENAI_API_KEY, AZURE_OPENAI_BASE_URL, and "
                    "AZURE_OPENAI_DEPLOYMENT must all be set."
                )
            self._client = OpenAI(
                api_key=settings.azure_openai_api_key,
                base_url=_foundry_base_url(settings.azure_openai_base_url),
            )
            self._model = settings.azure_openai_deployment
        else:
            if not settings.openai_api_key:
                raise ValueError("Foundry or OpenAI API configuration is not set.")
            self._client = OpenAI(api_key=settings.openai_api_key)
            self._model = settings.openai_model

    def generate_code(self, teacher_prompt: str) -> str:
        prompt = dedent(
            f"""
            Teacher request:
            {teacher_prompt.strip()}

            Produce a single Manim scene named GeneratedScene that explains this
            clearly for a calculus classroom.
            """
        ).strip()
        return self._run(prompt, SYSTEM_PROMPT)

    def generate_scene_plan(self, teacher_prompt: str) -> ScenePlan:
        base_prompt = dedent(
            f"""
            Teacher request:
            {teacher_prompt.strip()}

            Produce the JSON scene plan for a concise classroom explanation.
            """
        ).strip()
        prompt = base_prompt
        last_error: ValueError | None = None
        for attempt in range(2):
            raw_plan = self._run(prompt, SCENE_PLANNER_PROMPT)
            try:
                plan = ScenePlan.model_validate(json.loads(_json_object_text(raw_plan)))
                _validate_teaching_depth(teacher_prompt, plan)
                return plan
            except ValueError as exc:
                last_error = exc
                if attempt == 1:
                    break
                prompt = dedent(
                    f"""
                    {base_prompt}

                    Your previous plan was rejected: {exc}

                    Previous plan:
                    {raw_plan}

                    Return a corrected complete JSON plan that addresses the rejection.
                    """
                ).strip()

        assert last_error is not None
        raise last_error

    def repair_code(self, teacher_prompt: str, code: str, error_output: str) -> str:
        prompt = dedent(
            f"""
            Original teacher request:
            {teacher_prompt.strip()}

            Failing code:
            {code}

            Render error:
            {error_output}
            """
        ).strip()
        return self._run(prompt, REPAIR_PROMPT)

    def _run(self, user_prompt: str, system_prompt: str) -> str:
        response = self._client.responses.create(
            model=self._model,
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
        )

        text = getattr(response, "output_text", "").strip()
        if not text:
            raise ValueError("The model returned an empty response.")
        return text


def _foundry_base_url(value: str) -> str:
    base_url = value.strip().rstrip("/")
    if base_url.endswith("/responses"):
        base_url = base_url[: -len("/responses")]
    if not base_url.endswith("/openai/v1"):
        base_url = f"{base_url}/openai/v1"
    return f"{base_url}/"


def _json_object_text(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        cleaned = cleaned[first_newline + 1 :] if first_newline >= 0 else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("The model did not return a JSON scene plan.")
    return cleaned[start : end + 1]


def _validate_teaching_depth(teacher_prompt: str, plan: ScenePlan) -> None:
    normalized_prompt = teacher_prompt.lower()
    formal_definition = (
        "formal definition" in normalized_prompt
        or "definition of a derivative" in normalized_prompt
    )
    if formal_definition and len(plan.beats) < 8:
        raise ValueError(
            "Formal-definition derivations require exactly 8 beats so algebraic steps "
            "are not combined."
        )

    derivation_signals = ("derive", "prove", "show why", "step by step")
    if any(signal in normalized_prompt for signal in derivation_signals) and len(plan.beats) < 6:
        raise ValueError("Derivation requests require at least 6 teaching beats.")

    if "secant" in normalized_prompt and "tangent" in normalized_prompt:
        if not any(beat.action == VisualAction.SLIDE_SECANT for beat in plan.beats):
            raise ValueError(
                "A secant-to-tangent explanation requires a slide_secant beat with visible motion."
            )
