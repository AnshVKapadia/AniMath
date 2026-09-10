# Iterative single-proof workbench

This is a local command-line workflow, not a hosted application. It connects the
existing LLM provider to graphical storyboards and keeps revision history. It does
not yet accept arbitrary uploaded Lean files: real input uses the curated JSONL task
format. All output stays under research/runs/projects by default.

## Quick start (PowerShell, repository root, environment active)

```powershell
git pull --ff-only origin research/mathimate-agent-lean
python -m pip install -r research/requirements.txt
python -m research.lean_agent.workbench doctor
python -m research.lean_agent.workbench start --fixture
```

Start prints a unique project folder and the path to its first preview. Open the
printed index.html. No manual output folder naming is required. `--fixture` is an
explicit simulated-trace mode: it cannot be used as evidence of real Lean performance.

Copy the printed project path into a variable (replace the example):

```powershell
$project = 'C:\path\to\AniMath\research\runs\projects\PRINTED-PROJECT-ID'
```

## Generate and revise with the actual LLM

Requires the existing application provider configuration. Add OPENAI_API_KEY and
OPENAI_MODEL to the repository-root .env through your editor, or configure the
existing AZURE_OPENAI_API_KEY, AZURE_OPENAI_BASE_URL, AZURE_OPENAI_DEPLOYMENT trio.
Never paste API keys into chat, commit them, or include them in shared artifacts.
Doctor checks configuration presence, not credential validity or model availability.
Generation sends the proof, trace, and feedback to that provider and incurs API costs.

```powershell
python -m research.lean_agent.workbench generate --project "$project" --max-calls 3
python -m research.lean_agent.workbench revise --project "$project" --feedback "Explain what P and Q mean before splitting the goal." --max-calls 3
```

Each prints a new preview path and check results. Revisions include candidate outputs,
provider logs, storyboard JSON, structural verification, preview HTML, and Manim source.
No narration or metaphor is automatically certified. `conceptual_plan_pass` only means
the plan uses graphical action types rather than the raw-state baseline.

You can also edit a copy of a storyboard JSON yourself and import it without API calls:

```powershell
python -m research.lean_agent.workbench import --project "$project" --storyboard '.\edited-storyboard.json'
```

The previous revision remains intact. Check failures remain visible; importing a plan
does not certify its validity. The latest pointer refers to the newest inspectable
revision, even if structural checks fail. Keep one process per project at a time.

## Use real Lean input

Install/select Lean 4.19.0 with your usual approved setup. Inspect the authored tasks
in seeds.jsonl before executing: Lean source is executable code, and this local adapter
is not a sandbox. Start without --fixture:

```powershell
python -m research.lean_agent.workbench start --task conjunction_commutes --curated-local-corpus
```

Only successful compilation and trace parsing creates a ready project. Failure leaves
the project/extraction diagnostics for inspection. There is no silent fixture fallback.
After success, use generate/revise with the new printed project path. To use a different
curated corpus, pass --tasks path/to/tasks.jsonl and its matching --task ID.

## Render the latest revision as an MP4

Requires working Docker with the existing manimcommunity/manim:v0.19.0 image installed.

```powershell
python -m research.lean_agent.workbench render --project "$project"
```

This reuses the isolated container runner; it prints the video path on success and
saves last-render.json with diagnostics. Rendering does not prove semantic validity.
Rendering errors are recorded; automatic model repair currently covers storyboard
schema/alignment, not an integrated render-and-revise cycle in this workbench. The
batch experimental loop still supports execution-feedback repair.

## Verification status

18 Python tests passed in the development environment (including mocked model calls,
revision preservation, schema repair, invalid-reference previews, and proof hash checks).
Doctor ran successfully. Live API calls, real Lean extraction, Docker MP4 rendering,
and visual browser QA remain unvalidated here because the needed tools/configuration
are unavailable. Browser and Manim share storyboard actions, but their visual outputs
are not guaranteed identical. Real end-to-end validation is the next acceptance gate.

The present vocabulary is still limited: cards, goal splitting, witness selection,
expression changes, and nested-set illustrations. This is not yet arbitrary geometry,
calculus visualization, or automatic discovery of new visual metaphors.
