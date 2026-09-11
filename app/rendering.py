from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from app.config import IS_VERCEL, RENDERS_DIR, get_settings
from app.llm import LLMClient, UnsupportedVisualPlanError
from app.scene_compiler import compile_scene


VIDEO_SUFFIX = "GeneratedScene.mp4"
FORBIDDEN_SNIPPETS = (
    "TexTemplate(",
    "tex_template",
    "dvi_to_svg_args",
    "tex_compiler=",
    "output_format=",
)
LAYOUT_RISK_SNIPPETS = (
    ".add_coordinates(",
    ".get_axis_labels(",
    ".to_edge(",
    ".to_corner(",
    ".arrange_in_grid(",
)


class RenderPipelineError(Exception):
    def __init__(self, message: str, *, job_id: str, details: str) -> None:
        super().__init__(message)
        self.job_id = job_id
        self.details = details


@dataclass
class RenderResult:
    job_id: str
    code: str
    repaired: bool
    video_path: Path
    initial_video_path: Path | None = None
    final_video_path: Path | None = None


def run_generation_pipeline(job_id: str, teacher_prompt: str) -> RenderResult:
    total_start = perf_counter()
    llm = LLMClient()
    job_dir = RENDERS_DIR / job_id
    media_dir = job_dir / "media"
    job_dir.mkdir(parents=True, exist_ok=True)

    controlled = False
    _log(job_id, "plan", "Generating a structured scene plan")
    plan_start = perf_counter()
    try:
        plan = llm.generate_scene_plan(teacher_prompt, plan_validator=compile_scene)
        compiled = compile_scene(plan)
        code = _normalize_code(compiled.code)
        plan_path = job_dir / "scene_plan.json"
        plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        controlled = True
        _log(job_id, "plan", f"Controlled scene compiled in {_elapsed(plan_start)}")
        _log(job_id, "files", f"Saved structured plan to {plan_path}")
    except ValueError as exc:
        if isinstance(exc, UnsupportedVisualPlanError):
            _log(
                job_id,
                "visual",
                f"Controlled layout cannot represent the requested visual model: {exc}",
            )
        else:
            _log(job_id, "fallback", f"Structured plan was not usable: {exc}")
        code = _generate_freeform_code(llm, teacher_prompt, job_id)

    scene_path = job_dir / "scene.py"
    scene_path.write_text(code, encoding="utf-8")
    _log(job_id, "files", f"Saved generated scene to {scene_path}")

    success, details, video_path = _render_scene(
        scene_path=scene_path,
        media_dir=media_dir / ("controlled" if controlled else "freeform"),
        job_id=job_id,
    )
    if success and video_path:
        _log(job_id, "done", f"Pipeline finished in {_elapsed(total_start)}")
        return RenderResult(
            job_id=job_id,
            code=code,
            repaired=False,
            video_path=video_path,
            initial_video_path=video_path,
            final_video_path=video_path,
        )

    if controlled:
        _log(job_id, "fallback", "Controlled render failed; trying the free-form generator")
        fallback_start = perf_counter()
        code = _generate_freeform_code(llm, teacher_prompt, job_id)
        fallback_path = job_dir / "scene_fallback.py"
        fallback_path.write_text(code, encoding="utf-8")
        _log(job_id, "files", f"Saved free-form fallback scene to {fallback_path}")
        success, details, video_path = _render_scene(
            scene_path=fallback_path,
            media_dir=media_dir / "fallback",
            job_id=job_id,
        )
        if success and video_path:
            _log(job_id, "done", f"Fallback rendered in {_elapsed(fallback_start)}")
            return RenderResult(
                job_id=job_id,
                code=code,
                repaired=True,
                video_path=video_path,
                final_video_path=video_path,
            )

    _log(job_id, "repair", "Initial render failed; requesting one repair pass")
    repair_start = perf_counter()
    repaired_code = _normalize_code(llm.repair_code(teacher_prompt, code, details))
    _log(job_id, "repair", f"Repair code generated in {_elapsed(repair_start)}")
    repaired_path = job_dir / "scene_fixed.py"
    repaired_path.write_text(repaired_code, encoding="utf-8")
    _log(job_id, "files", f"Saved repaired scene to {repaired_path}")

    repaired_success, repaired_details, repaired_video = _render_scene(
        scene_path=repaired_path,
        media_dir=media_dir / "repaired",
        job_id=job_id,
    )
    if repaired_success and repaired_video:
        _log(job_id, "done", f"Pipeline finished in {_elapsed(total_start)} after repair")
        return RenderResult(
            job_id=job_id,
            code=repaired_code,
            repaired=True,
            video_path=repaired_video,
            initial_video_path=video_path,
            final_video_path=repaired_video,
        )

    _log(job_id, "error", f"Pipeline failed in {_elapsed(total_start)} after repair")
    raise RenderPipelineError(
        "Render failed after one repair attempt.",
        job_id=job_id,
        details=repaired_details,
    )


def _generate_freeform_code(llm: LLMClient, teacher_prompt: str, job_id: str) -> str:
    _log(job_id, "llm", "Generating free-form Manim code")
    generate_start = perf_counter()
    code = _normalize_code(llm.generate_code(teacher_prompt))
    _log(job_id, "llm", f"Free-form code generated in {_elapsed(generate_start)}")
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
        _log(job_id, "repair", f"Preemptive repair completed in {_elapsed(repair_start)}")
    if _needs_layout_repair(code):
        _log(job_id, "repair", "Risky layout detected; requesting frame-fit repair")
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
        _log(job_id, "repair", f"Layout repair completed in {_elapsed(repair_start)}")
    return code


def _normalize_code(code: str) -> str:
    cleaned = code.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_+-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    if "from manim import *" not in cleaned:
        cleaned = f"from manim import *\n\n{cleaned}"

    return cleaned.strip() + "\n"


def _needs_preemptive_repair(code: str) -> bool:
    return any(snippet in code for snippet in FORBIDDEN_SNIPPETS)


def _needs_layout_repair(code: str) -> bool:
    text_heavy_signals = sum(code.count(token) for token in ("MathTex(", "Tex(", "Text("))
    return any(snippet in code for snippet in LAYOUT_RISK_SNIPPETS) or text_heavy_signals >= 4


def _render_scene(
    scene_path: Path,
    media_dir: Path,
    job_id: str | None = None,
) -> tuple[bool, str, Path | None]:
    if IS_VERCEL:
        from app.sandbox_rendering import render_scene_in_sandbox

        if job_id:
            _log(job_id, "render", "Starting Manim render in Vercel Sandbox")
        render_start = perf_counter()
        result = render_scene_in_sandbox(scene_path, media_dir)
        if job_id:
            _log(job_id, "render", f"Sandbox render finished in {_elapsed(render_start)}")
        return result

    settings = get_settings()
    command = [
        sys.executable,
        "-m",
        "manim",
        settings.render_quality_flag,
        str(scene_path),
        "GeneratedScene",
        "--media_dir",
        str(media_dir),
    ]

    if job_id:
        _log(job_id, "render", f"Starting Manim render: {' '.join(command)}")
    render_start = perf_counter()

    try:
        process = subprocess.Popen(
            command,
            cwd=scene_path.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError as exc:
        return False, str(exc), None

    output_lines: list[str] = []
    assert process.stdout is not None
    for raw_line in process.stdout:
        line = raw_line.rstrip()
        output_lines.append(line)
        if job_id and line:
            _log(job_id, "manim", line)

    return_code = process.wait()
    combined_output = "\n".join(line for line in output_lines if line).strip()

    if job_id:
        _log(job_id, "render", f"Manim exited in {_elapsed(render_start)} with code {return_code}")

    if return_code != 0:
        return False, combined_output or "Manim exited with a non-zero status.", None

    video_path = _find_video(media_dir)
    if not video_path:
        return False, combined_output or "Render completed but no mp4 file was found.", None

    if job_id:
        _log(job_id, "render", f"Found output video at {video_path}")

    return True, combined_output, video_path


def _find_video(media_dir: Path) -> Path | None:
    candidates = sorted(media_dir.rglob(VIDEO_SUFFIX))
    return candidates[0] if candidates else None


def _log(job_id: str, stage: str, message: str) -> None:
    print(f"[job {job_id}] [{stage}] {message}", flush=True)


def _elapsed(start_time: float) -> str:
    return f"{perf_counter() - start_time:.2f}s"
