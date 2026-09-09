# MathimateAgent research fork

Independent research scaffold on top of MathimateLM. No UNT/UTSW data, models,
funding, or project code is used. The existing application is unchanged.

**Status:** implementation scaffold and 132-task draft; no empirical results.
The runtime probe and Docker rendering have NOT been exercised in this workspace.
Do not describe automatic contract passes as mathematical or visual correctness.
Read `docs/RESEARCH_PLAN.md` for the scientific design and submission constraints.

## Installation and pilot

Run from the repository root, preferably in WSL/Linux with Docker available:

```bash
python -m pip install -r research/requirements.txt
docker pull manimcommunity/manim:v0.19.0
python -m research.mathimate_agent.cli --validate-only
python -m unittest discover -s research/tests -v
python -m research.mathimate_agent.cli --split dev --conditions A C D E R --limit 2 --allow-draft --out research/runs/pilot-01
```

Reuse existing `.env` Foundry/OpenAI settings from the application. A model key is
required for live generation; no keys enter the render container. Specify an
available model/deployment using the existing settings. Do not paste credentials
into benchmark files or run logs. The model response's reported identity is logged.
Generation is stochastic; the seed controls schedule randomization only.

Before publishing results: audit all prompt requirements and numeric references;
validate probes against correct and deliberately wrong real videos; then mark
reviewed tasks `audited` and freeze the JSONL hash. `--allow-draft` is for pilots.

```bash
python -m research.mathimate_agent.cli --split test --conditions A B C D E R --replicates 1 --out research/runs/frozen-01
python -m research.mathimate_agent.analyze research/runs/frozen-01/results.jsonl
```

The 120 test prompts come from **24 families**, with 5 numeric variants per family.
They are not 120 independent mathematical concepts. Bootstrap intervals resample
families and keep method comparisons paired. Twelve concept-disjoint development
families are separate. The draft has 30 easy, 60 medium and 30 hard test tasks.

## Conditions and budget

| ID | Plan | Render feedback | Runtime contract feedback | Candidate attempts |
|---|---|---|---|---|
| A | No | No | No | 1 |
| B | Yes | No | No | 1 |
| C | No | Yes | No | Up to 3 |
| D | Yes; may replan | Yes | Yes | Up to 3 |
| E | Yes | Yes | No | Up to 3 |
| R | No | No; fresh samples | No | Up to 3 |

All use the same code prompt, provider, task statements, render environment and
external assessment. C/E/R stop at first render. D stops at automatic contract
pass or budget. A/B also render and are assessed; they cannot act on the feedback.
R can select the first rendering candidate but never conditions the next sample
on an error. It is repeated sampling, not feedback repair.

Default D budget: 3 candidate programs, at most 5 total LLM calls (planning and
replanning count), 6000 output tokens per call. Other methods may use fewer calls.
**These are shared caps, not equal actual token costs.** Report measured costs,
quality versus attempts/tokens, and a matched-budget sensitivity experiment before
attributing gains solely to verification. D-E disables replanning by default to isolate the contract-feedback/stopping
policy. Use `--replan` only for a separately labeled D sensitivity ablation.

The optional compiler comparator directly reuses `generate_scene_plan`,
`ScenePlan`, and `compile_scene` on supported graph/equation tasks:

```bash
python -m research.mathimate_agent.controlled --task-id tangent_polynomial-1 --out research/runs/compiler-pilot
```

It uses the original planner's internal two-try plan validation and no free-form
fallback. Do not pool it into A-D or claim it is the entire production pipeline.

## Measurement and limitations

The Docker wrapper hooks `Axes.plot`, `Scene.play`, `Scene.wait`, and rendering.
At action boundaries it records displayed graphs, dots, lines and text. Graph
checks compare sampled **actual curve geometry** in axis coordinates with SymPy
expressions. Line checks compare slope and incidence. Text presence is only text
presence. Movement checks detect changed coordinates, not correct trajectories.

Missing traces and unsupported/manual checks do not pass. `complete_pass` stays
false while essential manual checks are unresolved. `automatic_pass` covers only
the implemented contract subset; report coverage and checker types alongside it.
Graph coverage is partial, not universal symbolic equivalence. Transient events,
occlusion, invisible objects, complex transformations, copied graph objects,
alternative valid primitives, multiple coordinate systems and fine typography can
mislead the current probe. A blind video audit and mutation tests are publication
gates. The in-loop checker is not an independent final judge.

Generated code runs only inside a network-disabled, resource-limited, read-only
container with a fresh output directory. Static source screening is hygiene, not
a security proof. No host execution mode is offered. The writable artifact volume
is not a disk quota; run pilots on a disposable worker with a bounded filesystem
before large/untrusted workloads. This is not an adversarial-agent benchmark.

## Logs and failures

Each run saves manifest (package versions, image digest, source/benchmark hashes),
randomized schedule, JSONL results, and each task's state/events/LLM calls. Every
candidate saves source, render output, video and probe trace. Logs capture prompts,
responses, model identity, usage including cached tokens, call latency, attempts,
selected output and termination. Do not estimate dollars from stale pricing;
convert usage with the actual provider's dated rates, including reasoning output,
caching, rendering and any external judging. No autonomous repeat API retries.

Runs refuse to overwrite an existing directory. Infrastructure/API errors are
recorded and abort the run; they are not relabeled as model failures. Resume and
cross-run merging are intentionally not implemented. Keep the failed ledger,
rerun the full paired block with unchanged settings, and document reruns. The
analysis rejects duplicate cells and incomplete paired designs. It also verifies completion against the saved randomized schedule.
