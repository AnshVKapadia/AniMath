from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)


class GenerateResponse(BaseModel):
    jobId: str
    videoUrl: str
    code: str
    repaired: bool
    initialVideoUrl: str | None = None
    finalVideoUrl: str | None = None


class GenerateErrorResponse(BaseModel):
    jobId: str
    error: str
    details: str
