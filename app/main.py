from __future__ import annotations

import base64
import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.config import IS_VERCEL, RENDERS_DIR, STATIC_DIR, get_settings
from app.rendering import (
    RenderInfrastructureError,
    RenderPipelineError,
    run_generation_pipeline,
)
from app.schemas import GenerateErrorResponse, GenerateRequest, GenerateResponse


load_dotenv()


app = FastAPI(title=get_settings().app_name)

RENDERS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/renders", StaticFiles(directory=RENDERS_DIR), name="renders")


@app.get("/", response_class=FileResponse)
async def index() -> Path:
    return STATIC_DIR / "index.html"


@app.post(
    "/api/generate",
    response_model=GenerateResponse,
    responses={500: {"model": GenerateErrorResponse}},
)
async def generate_animation(payload: GenerateRequest) -> GenerateResponse:
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt cannot be empty.")

    job_id = str(uuid4())

    try:
        result = run_generation_pipeline(job_id=job_id, teacher_prompt=prompt)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RenderInfrastructureError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "jobId": exc.job_id,
                "error": str(exc),
                "details": exc.details,
            },
        )
    except RenderPipelineError as exc:
        return JSONResponse(
            status_code=500,
            content={
                "jobId": exc.job_id,
                "error": str(exc),
                "details": exc.details,
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    video_url = _video_url(result.video_path)
    if IS_VERCEL:
        initial_video_url = None
        final_video_url = None
    else:
        initial_video_url = _video_url(result.initial_video_path) if result.initial_video_path else None
        final_video_url = _video_url(result.final_video_path) if result.final_video_path else None
    return GenerateResponse(
        jobId=result.job_id,
        videoUrl=video_url,
        code=result.code,
        repaired=result.repaired,
        initialVideoUrl=initial_video_url,
        finalVideoUrl=final_video_url,
    )


def _video_url(video_path: Path) -> str:
    if not IS_VERCEL:
        relative_video = video_path.relative_to(RENDERS_DIR).as_posix()
        return f"/renders/{relative_video}"

    max_bytes = int(os.getenv("VERCEL_INLINE_VIDEO_MAX_BYTES", str(2_750_000)))
    video_size = video_path.stat().st_size
    if video_size > max_bytes:
        raise ValueError(
            f"Rendered video is {video_size / 1_000_000:.1f} MB, which is too large "
            "for Vercel's inline response. Shorten the animation or use external object storage."
        )
    encoded_video = base64.b64encode(video_path.read_bytes()).decode("ascii")
    return f"data:video/mp4;base64,{encoded_video}"
