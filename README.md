# AniMath

AniMath turns a tutor's natural-language prompt into a short Manim animation. Enter a concept, preview the explanation, and download the video.

[Try the live demo](https://ani-math.vercel.app/)

![Riemann rectangles approximate the area under the graph of x squared](docs/examples/riemann.gif)

| Example | Prompt to try |
| --- | --- |
| [Riemann sums](docs/examples/riemann.mp4) | Visualize Riemann rectangles for the area under f(x)=x^2 from x=0 to x=2, then show the definite integral. |
| [Geometric series](docs/examples/geometric-series.mp4) | Explain algebraically why the geometric series 1 + r + r^2 + ... equals 1/(1-r) for absolute value of r less than 1. Use equation transformations rather than a graph. |

## How it works

I built AniMath to make custom visual explanations easier to create during tutoring. The main engineering challenge was turning a flexible prompt into a scene whose math, narration, and layout agree.

1. Foundry or OpenAI proposes a structured scene plan. Pydantic validates its actions and parameters.
2. The compiler turns the plan into Manim code and controls the layout. A Riemann sum uses the same sample-point setting for its rectangles and written explanation.
3. Manim renders locally or in a temporary Vercel Sandbox. Requests outside the compiler's supported scenes can use a free-form fallback.

Start with [the FastAPI route](app/main.py), [scene schema](app/scene_plan.py), or [compiler](app/scene_compiler.py).

## Run locally

Install the [Manim system prerequisites](https://docs.manim.community/en/stable/installation.html), including LaTeX for equations. In PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-local.txt
Copy-Item .env.example .env
```

Fill in all three Azure variables for Foundry, or set `OPENAI_API_KEY` for direct OpenAI access. Then run:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app
```

Open [the local app](http://127.0.0.1:8000) or [the API docs](http://127.0.0.1:8000/docs). Run the tests without model credentials:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
```

## Deployment

Vercel runs FastAPI from `index.py`. Configure model credentials and set `VERCEL_SANDBOX_SNAPSHOT_ID` to a Sandbox snapshot with Docker and `manimcommunity/manim:v0.19.0`. Rendering runs synchronously and returns the MP4 inline. The default video budget is 2,750,000 bytes, configurable via `VERCEL_INLINE_VIDEO_MAX_BYTES`.
