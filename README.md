# Ani-Math

Ani-Math is a tutor-facing math animation tool for visual math and physics
explanations. A tutor enters a natural-language prompt, and the app
plans, compiles, renders, previews, and downloads a short Manim video.

Production: [https://ani-math.vercel.app](https://ani-math.vercel.app)

## Run locally

Install the [Manim system prerequisites](https://docs.manim.community/en/stable/installation.html),
then run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-local.txt
Copy-Item .env.example .env
```

Add Foundry or OpenAI credentials to `.env`, then start the app:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## How generation works

1. Foundry/OpenAI converts graph-compatible tutor prompts into a constrained JSON scene plan.
2. Pydantic validates the plan, actions, axis ranges, and required parameters.
3. Mathematical caret powers such as `x^2` are normalized to safe Python powers
   such as `x**2` before compilation.
4. The controlled compiler validates function syntax and generates frame-safe
   Manim code with fixed title, visual, and explanation regions. Riemann scenes
   carry an explicit left, right, or center sample type so the explanation and
   rectangle geometry use the same convention.
5. A compiler-rejected plan receives one structured correction attempt before
   the pipeline considers free-form generation.
6. Manim renders locally during development or inside an isolated Vercel Sandbox
   in production.
7. Explicit visual requests that need diagrams, vector fields, flow, geometry, or
   other unsupported primitives route to a visually focused free-form scene.
8. If a render fails, the pipeline tries one repair pass while preserving the
   concrete visual model.

This keeps normal requests on a consistent, deterministic visual layout while
retaining a fallback for concepts outside the controlled compiler.

## Architecture

- `FastAPI` serves the UI and `POST /api/generate`.
- Plain HTML, CSS, and JavaScript provide the single-page tutor interface.
- Foundry/OpenAI produces semantic teaching beats rather than screen coordinates.
- The controlled compiler owns layout, sizing, transitions, and collision checks.
- Local development runs Manim directly and stores artifacts under `renders/`.
- Vercel runs FastAPI as a Fluid compute function and starts a temporary Sandbox
  from a prebuilt Manim runtime snapshot for each render.
- Production returns the MP4 as an inline `data:video/mp4;base64,...` URL, so no
  persistent filesystem or object-storage service is required for the current MVP.

## Configuration

Recommended Foundry variables:

- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_BASE_URL`
- `AZURE_OPENAI_DEPLOYMENT`

Direct OpenAI fallback:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`, default `gpt-5-mini`

Application settings:

- `APP_NAME`, default `Ani-Math`
- `MAX_PROMPT_LENGTH`, default `1800`
- `MANIM_QUALITY_FLAG`, default `-ql`; accepted values are `-ql`, `-qm`, and `-qh`
- `VERCEL_INLINE_VIDEO_MAX_BYTES`, default `2750000`

Production additionally requires:

- `VERCEL_SANDBOX_SNAPSHOT_ID`: ID of the prebuilt Sandbox snapshot containing
  Docker and the `manimcommunity/manim:v0.19.0` image

Vercel supplies Sandbox authentication through its deployment environment. Never
commit Foundry/OpenAI keys, `.env`, `.env.local`, or `.vercel/`.

## Dependency files

- `requirements.txt`: serverless FastAPI, Foundry/OpenAI, and Vercel Sandbox SDK
- `requirements-local.txt`: serverless dependencies plus Manim and Uvicorn
- `requirements-gemini.txt`: local dependencies plus the optional Gemini SDK

Manim is intentionally absent from the root `requirements.txt`. Its native
Cairo/Pango and LaTeX dependencies do not belong in the Vercel function bundle;
production rendering happens in the Sandbox runtime instead.

## Vercel deployment

- Vercel project: `ani-math`
- Production URL: [https://ani-math.vercel.app](https://ani-math.vercel.app)
- Production branch: `master`
- FastAPI entrypoint: `index.py`
- Function timeout: 300 seconds, configured in `vercel.json`

Pushing the production branch triggers a Git-connected deployment. The FastAPI
function performs planning and compilation, sends only the generated scene source
to the Sandbox, runs Manim there, downloads the MP4, and destroys the temporary
Sandbox.

Docker Desktop is not required to deploy or render on Vercel. It is only relevant
if a developer chooses to run a separate local container workflow.

## API

### `POST /api/generate`

Request:

```json
{
  "prompt": "show why the derivative of x^2 is 2x using the definition of the derivative"
}
```

Success response:

```json
{
  "jobId": "uuid",
  "videoUrl": "data:video/mp4;base64,...",
  "code": "...generated Manim code...",
  "repaired": false,
  "initialVideoUrl": null,
  "finalVideoUrl": null
}
```

On Vercel, `videoUrl` is an inline data URL and the two intermediate video URLs
are `null`. Locally, `videoUrl` and available intermediate URLs use paths under
`/renders/<job_id>/...`.

Failure response after the final repair attempt:

```json
{
  "jobId": "uuid",
  "error": "Render failed after one repair attempt.",
  "details": "...final render output..."
}
```

## Main files

- `index.py`: root Vercel FastAPI entrypoint
- `app/main.py`: routes, static mounting, and production video responses
- `app/llm.py`: Foundry/OpenAI prompts, planning, correction, and repair calls
- `app/scene_plan.py`: constrained plan schema and normalization
- `app/scene_compiler.py`: safe expression compiler and controlled layouts
- `app/rendering.py`: planning, compilation, fallback, repair, and render orchestration
- `app/sandbox_rendering.py`: Vercel Sandbox lifecycle and MP4 retrieval
- `app/static/`: one-page Ani-Math interface
- `tests/`: planner, compiler, pipeline, Sandbox, and Vercel response tests

## Tests

Run the full focused suite:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run the representative live benchmark, which uses configured model credentials:

```powershell
.venv\Scripts\python.exe -m scripts.benchmark_pipeline
```

## Optional Gemini variant

The primary application uses the configured Foundry/OpenAI deployment. A separate
Gemini-backed local variant remains available in `app/main_gemini.py`,
`app/gemini_llm.py`, and `app/rendering_gemini.py`.

Install it with:

```powershell
python -m pip install -r requirements-gemini.txt
Copy-Item .env.gemini.example .env
.venv\Scripts\python.exe -m uvicorn app.main_gemini:app --reload
```

Set `GEMINI_API_KEY` and optionally `GEMINI_MODEL`, which defaults to
`gemini-2.5-flash`.

## Known limitations

- No user authentication, queue, database, prompt cache, or object storage
- Render jobs run synchronously within the request lifecycle
- Model planning is not seeded, so semantic details can vary between requests
- Controlled layouts currently focus on graphs, points, secants, tangents, areas,
  Riemann rectangles, and equation transformations
- Unsupported plans may still reach the free-form fallback after structured
  validation and correction fail
- Inline production videos must remain below the configured response budget
- Local Manim rendering requires its system-level dependencies

## Future ideas

- Add post-video refinement buttons such as **Make simpler**, **Elaborate**, and
  **Make more visual**, using the current prompt and generated scene as context.
