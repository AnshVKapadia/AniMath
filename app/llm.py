from __future__ import annotations

from textwrap import dedent

from openai import OpenAI

from app.config import get_settings


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


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set.")

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
