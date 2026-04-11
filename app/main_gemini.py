from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import RENDERS_DIR, STATIC_DIR, get_settings
from app.rendering import RenderPipelineError
from app.rendering_gemini import run_gemini_generation_pipeline
from app.schemas import GenerateErrorResponse, GenerateRequest, GenerateResponse


load_dotenv()

app = FastAPI(title=f"{get_settings().app_name} (Gemini)")

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

    if len(prompt) > get_settings().max_prompt_length:
        raise HTTPException(
            status_code=422,
            detail=f"Prompt must be {get_settings().max_prompt_length} characters or fewer.",
        )

    job_id = str(uuid4())

    try:
        result = run_gemini_generation_pipeline(job_id=job_id, teacher_prompt=prompt)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
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

    relative_video = result.video_path.relative_to(RENDERS_DIR).as_posix()
    return GenerateResponse(
        jobId=result.job_id,
        videoUrl=f"/renders/{relative_video}",
        code=result.code,
        repaired=result.repaired,
    )
