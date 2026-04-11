from __future__ import annotations

import os
from textwrap import dedent

from google import genai


GEMINI_SYSTEM_PROMPT = dedent(
    """
    You generate short, valid Manim Community Edition scenes for a teacher-facing
    calculus visualization tool.

    Hard requirements:
    - Return only Python code. No markdown fences. No explanations.
    - Use only `from manim import *`.
    - Define exactly one scene class named `GeneratedScene(Scene)`.
    - Keep the animation short and classroom-friendly, roughly 15 to 45 seconds.
    - Focus on common calculus concepts: limits, derivatives, tangent lines,
      integrals, Riemann sums, and simple series.
    - Prioritize mathematical correctness and valid Manim syntax.
    - Use readable labels, simple color choices, and uncluttered layouts.
    - Avoid external files, images, network calls, random data, or unsupported libraries.
    - Do not use LaTeX packages or advanced dependencies beyond standard Manim.
    - Do not use TexTemplate, tex_template customization, MathTex template overrides,
      dvisvgm options, or any custom LaTeX compiler configuration.
    - Ensure the scene can render on a default Manim installation.
    - Keep every visible object inside the frame at all times.
    - Treat the safe layout area as roughly 80 percent of frame width and height.
    - Never place text, formulas, labels, graphs, or braces flush against screen edges.
    - Prefer one main visual with one short title and at most one or two supporting labels.
    - If multiple elements are grouped, use VGroup(...).arrange(...) and then scale the group
      with scale_to_fit_width or scale_to_fit_height before moving it into place.
    - Before animating, scale large formulas, titles, and grouped annotations to fit comfortably.
    - Avoid dense coordinate labels, crowded legends, or long paragraphs.
    - Avoid add_coordinates() unless absolutely necessary. Prefer unlabeled axes for reliability.
    - Avoid get_axis_labels() unless labels are very short and scaled down safely.
    - Prefer manual positioning near the center over repeated to_edge or corner placements.
    - Keep text strings short enough to fit comfortably on screen.

    Implementation guidance:
    - Prefer Axes, NumberPlane, MathTex, Tex, ValueTracker, Dot, Line, Brace,
      Rectangle, and simple transforms/fades.
    - Use default MathTex or simple Text/Tex only. Never construct or modify TexTemplate.
    - Keep construct() compact and deterministic.
    - If text rendering could be fragile, prefer MathTex and minimal Tex usage.
    - After creating titles, formulas, axis labels, or grouped annotations, explicitly call
      scale_to_fit_width or scale before positioning them.
    - When using Axes, prefer fewer labels and a visually centered graph.
    """
).strip()


GEMINI_REPAIR_PROMPT = dedent(
    """
    The following Manim code failed to render. Fix it so it still satisfies the
    original teacher request and renders successfully.

    Return only corrected Python code with:
    - exactly one `GeneratedScene(Scene)` class
    - only `from manim import *`
    - no markdown or commentary
    - no TexTemplate usage or LaTeX template customization
    - keep every element comfortably inside the frame
    - scale down text, formulas, and grouped objects when needed
    - remove crowded labels or edge-hugging layouts
    """
).strip()


class GeminiLLMClient:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        self._model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._client = genai.Client(api_key=api_key)

    def generate_code(self, teacher_prompt: str) -> str:
        prompt = dedent(
            f"""
            Teacher request:
            {teacher_prompt.strip()}

            Produce a single Manim scene named GeneratedScene that explains this
            clearly for a calculus classroom.
            """
        ).strip()
        return self._run(prompt, GEMINI_SYSTEM_PROMPT)

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
        return self._run(prompt, GEMINI_REPAIR_PROMPT)

    def _run(self, user_prompt: str, system_prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            config={
                "system_instruction": system_prompt,
                "temperature": 0.2,
            },
            contents=user_prompt,
        )
        text = (response.text or "").strip()
        if not text:
            raise ValueError("Gemini returned an empty response.")
        return text
