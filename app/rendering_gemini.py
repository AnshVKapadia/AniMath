from __future__ import annotations

from app.gemini_llm import GeminiLLMClient
from app.rendering import (
    RenderPipelineError,
    RenderResult,
    _elapsed,
    _log,
    _needs_layout_repair,
    _needs_preemptive_repair,
    _normalize_code,
    _render_scene,
)
from app.config import RENDERS_DIR
from time import perf_counter


def run_gemini_generation_pipeline(job_id: str, teacher_prompt: str) -> RenderResult:
    total_start = perf_counter()
    llm = GeminiLLMClient()
    job_dir = RENDERS_DIR / job_id
    media_dir = job_dir / "media"
    job_dir.mkdir(parents=True, exist_ok=True)

    _log(job_id, "llm", "Generating initial Manim code with Gemini")
    generate_start = perf_counter()
    code = _normalize_code(llm.generate_code(teacher_prompt))
    _log(job_id, "llm", f"Initial Gemini code generated in {_elapsed(generate_start)}")
    if _needs_preemptive_repair(code):
        _log(job_id, "repair", "Unsupported LaTeX template usage detected; requesting repair")
        repair_start = perf_counter()
        code = _normalize_code(
            llm.repair_code(
                teacher_prompt,
                code,
                "Remove unsupported TexTemplate or LaTeX template customization. "
                "Use default MathTex/Text/Tex only.",
            )
        )
        _log(job_id, "repair", f"Preemptive Gemini repair completed in {_elapsed(repair_start)}")
    if _needs_layout_repair(code):
        _log(job_id, "repair", "Risky layout detected; requesting frame-fit Gemini repair")
        repair_start = perf_counter()
        code = _normalize_code(
            llm.repair_code(
                teacher_prompt,
                code,
                "The scene risks overflowing the frame. Keep all content inside a safe central "
                "area, reduce labels, avoid add_coordinates and get_axis_labels when possible, "
                "and scale text, formulas, and groups to fit before positioning.",
            )
        )
        _log(job_id, "repair", f"Gemini layout repair completed in {_elapsed(repair_start)}")
    scene_path = job_dir / "scene.py"
    scene_path.write_text(code, encoding="utf-8")
    _log(job_id, "files", f"Saved generated scene to {scene_path}")

    success, details, video_path = _render_scene(
        scene_path=scene_path,
        media_dir=media_dir,
        job_id=job_id,
    )
    if success and video_path:
        _log(job_id, "done", f"Gemini pipeline finished in {_elapsed(total_start)}")
        return RenderResult(job_id=job_id, code=code, repaired=False, video_path=video_path)

    _log(job_id, "repair", "Initial render failed; requesting one Gemini repair pass")
    repair_start = perf_counter()
    repaired_code = _normalize_code(llm.repair_code(teacher_prompt, code, details))
    _log(job_id, "repair", f"Gemini repair code generated in {_elapsed(repair_start)}")
    repaired_path = job_dir / "scene_fixed.py"
    repaired_path.write_text(repaired_code, encoding="utf-8")
    _log(job_id, "files", f"Saved repaired scene to {repaired_path}")

    repaired_success, repaired_details, repaired_video = _render_scene(
        scene_path=repaired_path,
        media_dir=media_dir,
        job_id=job_id,
    )
    if repaired_success and repaired_video:
        _log(job_id, "done", f"Gemini pipeline finished in {_elapsed(total_start)} after repair")
        return RenderResult(
            job_id=job_id,
            code=repaired_code,
            repaired=True,
            video_path=repaired_video,
        )

    _log(job_id, "error", f"Gemini pipeline failed in {_elapsed(total_start)} after repair")
    raise RenderPipelineError(
        "Render failed after one repair attempt.",
        job_id=job_id,
        details=repaired_details,
    )
