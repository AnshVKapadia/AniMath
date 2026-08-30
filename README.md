# Calc Animator MVP

Minimal tutor-facing calculus visualization tool:

- tutor enters a natural-language calculus prompt
- backend asks Foundry/OpenAI for a constrained scene plan
- a deterministic compiler turns the plan into frame-safe Manim code
- backend renders an MP4 with Manim
- tutor previews and downloads the result for use in a lesson

## Run locally

After installing the [Manim system prerequisites](https://docs.manim.community/en/stable/installation.html), run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-local.txt
Copy-Item .env.example .env
```

Add your Foundry/OpenAI credentials to `.env`, then start the app:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Architecture

This MVP uses one Python service:

- `FastAPI` serves the tutor UI and the API
- plain HTML/CSS/JS keeps the frontend lightweight
- Foundry/OpenAI plans semantic animation beats as validated JSON
- a controlled compiler owns coordinates, sizing, and transitions
- free-form generation remains available as a render fallback
- Manim renders videos into the local `renders/` directory

This keeps the project easy to run locally and simple to deploy on a Python host.

## Files

- `app/main.py`: FastAPI routes and static file mounting
- `app/llm.py`: Foundry/OpenAI prompts and response handling
- `app/scene_plan.py`: constrained scene-plan schema and validation
- `app/scene_compiler.py`: deterministic layouts and runtime collision checks
- `app/rendering.py`: plan, compile, render, fallback, and repair orchestration
- `app/schemas.py`: request and response models
- `app/static/`: one-page frontend
- `renders/`: generated code and videos

## Setup

### 1. Install system prerequisites for Manim

Manim needs additional system packages. Follow the official Manim installation guide for your OS before installing Python dependencies:

- Windows: install the required C++ build tools and FFmpeg
- macOS: install FFmpeg and Cairo/Pango dependencies
- Linux: install FFmpeg, Cairo, Pango, and related development packages

If `python -m manim --version` fails, finish the Manim prerequisite setup first.

### 2. Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```powershell
pip install -r requirements-local.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and fill in your Foundry deployment details:

```powershell
Copy-Item .env.example .env
```

Recommended variables:

- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_BASE_URL`
- `AZURE_OPENAI_DEPLOYMENT`

Optional variables:

- `OPENAI_API_KEY` and `OPENAI_MODEL` provide a direct OpenAI fallback when
  Foundry variables are empty
- `OPENAI_MODEL` default: `gpt-5-mini`
- `APP_NAME` default: `AniMath - Math Animation Tool`
- `MAX_PROMPT_LENGTH` default: `600`
- `MANIM_QUALITY_FLAG` default: `-ql`

### Gemini version

The OpenAI-backed app is unchanged. A separate Gemini-backed version is also included.

Files:

- `app/main_gemini.py`: Gemini FastAPI entrypoint
- `app/gemini_llm.py`: Gemini API integration
- `app/rendering_gemini.py`: Gemini render pipeline

Copy `.env.gemini.example` to `.env` if you want to run the Gemini variant:

```powershell
Copy-Item .env.gemini.example .env
```

Then set:

- `GEMINI_API_KEY`
- optional `GEMINI_MODEL` default: `gemini-2.5-flash`

This project’s Gemini variant defaults to `gemini-2.5-flash` because Google’s official Gemini Developer API pricing/docs currently show it on the free tier. Source: [Gemini Developer API pricing](https://ai.google.dev/pricing), [Gemini API quickstart](https://ai.google.dev/gemini-api/docs/quickstart), [Gemini text generation docs](https://ai.google.dev/gemini-api/docs/text-generation).

## Tutor examples and alternatives

To run the Gemini version instead:

```powershell
uvicorn app.main_gemini:app --reload
```

Try prompts like:

- `show why the derivative of x^2 is 2x`
- `visualize a Riemann sum approaching the integral`
- `animate a tangent line moving along y=x^2`
- `illustrate a geometric series converging`

Run the focused tests with:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run the representative live benchmark with:

```powershell
.venv\Scripts\python.exe -m scripts.benchmark_pipeline
```

## API

### `POST /api/generate`

Request:

```json
{ "prompt": "Show why the derivative of x^2 is 2x" }
```

Success response:

```json
{
  "jobId": "uuid",
  "videoUrl": "/renders/<job_id>/media/videos/scene/480p15/GeneratedScene.mp4",
  "code": "...generated manim code...",
  "repaired": false
}
```

Failure response:

```json
{
  "jobId": "uuid",
  "error": "Render failed after one repair attempt.",
  "details": "...final stderr..."
}
```

## Vercel deployment

The production branch is configured for Vercel. The FastAPI function handles the
UI and Foundry/OpenAI calls, while Manim runs in an isolated Vercel Sandbox created
from a prebuilt runtime snapshot.

Required production variables:

- the Foundry/OpenAI variables listed above
- `VERCEL_SANDBOX_SNAPSHOT_ID`

The root `requirements.txt` is intentionally serverless-only. Use
`requirements-local.txt` for local Manim development and
`requirements-gemini.txt` for the optional Gemini variant.

## Known limitations

- No auth, queue, persistence layer, or object storage
- Render jobs run synchronously in the request cycle
- Rendered videos are returned inline on Vercel and stored locally during development
- The controlled compiler currently supports graph, point, secant, tangent,
  sliding-secant, area, Riemann-rectangle, and equation-transformation scenes
- Unsupported or invalid plans fall back to free-form generation
- Model planning quality depends on the selected Foundry/OpenAI deployment
- Manim rendering will fail until system-level prerequisites are installed
