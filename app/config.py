from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent.parent
RENDERS_DIR = BASE_DIR / "renders"
STATIC_DIR = BASE_DIR / "app" / "static"


class Settings(BaseModel):
    openai_api_key: str | None
    openai_model: str
    azure_openai_api_key: str | None
    azure_openai_base_url: str | None
    azure_openai_deployment: str | None
    app_name: str
    max_prompt_length: int
    render_quality_flag: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_openai_base_url=os.getenv("AZURE_OPENAI_BASE_URL"),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        app_name=os.getenv("APP_NAME", "AniMath - Math Animation Tool"),
        max_prompt_length=int(os.getenv("MAX_PROMPT_LENGTH", "600")),
        render_quality_flag=os.getenv("MANIM_QUALITY_FLAG", "-ql"),
    )
