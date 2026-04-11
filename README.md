# Calc Animator MVP

Minimal teacher-facing calculus visualization tool:

- teacher enters a natural-language calculus prompt
- backend asks OpenAI for Manim code
- app saves the code to disk
- backend renders an MP4 with Manim
- frontend previews and downloads the result

## Architecture

This MVP uses one Python service:

- `FastAPI` serves the teacher UI and the API
- plain HTML/CSS/JS keeps the frontend lightweight
- OpenAI generates and optionally repairs Manim code
- Manim renders videos into the local `renders/` directory

This keeps the project easy to run locally and simple to deploy on a Python host.

## Files

- `app/main.py`: FastAPI routes and static file mounting
- `app/llm.py`: OpenAI prompt and response handling
- `app/rendering.py`: save code, run Manim, retry once on failure
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
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and fill in your OpenAI key:

```powershell
Copy-Item .env.example .env
```

Required variables:

- `OPENAI_API_KEY`

Optional variables:

- `OPENAI_MODEL` default: `gpt-5-mini`
- `APP_NAME` default: `Calc Animator MVP`
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

## Run locally

```powershell
uvicorn app.main:app --reload
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

To run the Gemini version instead:

```powershell
uvicorn app.main_gemini:app --reload
```

Try prompts like:

- `show why the derivative of x^2 is 2x`
- `visualize a Riemann sum approaching the integral`
- `animate a tangent line moving along y=x^2`
- `illustrate a geometric series converging`

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

## Deployment recommendation

For v1, deploy this as a single Python service on a host that supports Manim system dependencies:

- best fit: Render or Railway with Docker or a Python service that includes FFmpeg and Cairo/Pango dependencies
- not recommended for rendering: Vercel, because Manim rendering depends on heavier system packages and local video output

If you later want Vercel for the frontend, keep rendering on a separate Python backend.

## Known limitations

- No auth, queue, persistence layer, or object storage
- Render jobs run synchronously in the request cycle
- Output files are stored on local disk only
- Model quality depends on the selected OpenAI model
- Manim rendering will fail until system-level prerequisites are installed
