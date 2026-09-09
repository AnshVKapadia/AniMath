# MathimateAgent: Lean-grounded explanation research

This is the active pivot. The original calculus harness and product are preserved.
See [the complete revised research plan](../docs/LEAN_RESEARCH_PLAN.md).

## Status

Implemented: typed task/storyboard/trace contracts; conservative Lean JSON message
adapter; fixed-proof hash binding and axiom allowlist; deterministic Manim compiler;
bounded A/B/C/D/E/T loop; per-candidate logs; randomized paired evaluation schedule;
four explicitly unvalidated development tasks; eleven passing fixture-based unit tests.

NOT demonstrated: compatibility with a real Lean 4.19.0 process, a rendered animation,
a live model run, narration faithfulness, a validated benchmark, or an empirical gain.
Lean and Docker are absent in the current execution environment. Downloading Lean
was blocked. Existing provider dependencies also need installation in a run environment.

## Commands (from repository root)

```bash
python -m unittest research.tests.test_lean_agent -v
python -m research.lean_agent.cli schema --out research/runs/lean-schema
# Install/select Lean 4.19.0 through your normal approved setup first.
# Inspect every task: Lean is executable code. This adapter is NOT a sandbox.
python -m research.lean_agent.cli extract --out research/runs/lean-smoke --curated-local-corpus
# Install existing app/research requirements and configure existing provider settings.
# Docker must be running, with manimcommunity/manim:v0.19.0 available locally.
python -m research.lean_agent.cli evaluate --out research/runs/lean-template --conditions T --curated-local-corpus
python -m research.lean_agent.cli evaluate --out research/runs/lean-pilot --conditions A B C D E R T --replicates 2 --curated-local-corpus
python -m research.mathimate_agent.analyze research/runs/lean-pilot/results.jsonl
```

Output directories must be new. No automatic network downloads. Extraction recompiles
every proof before evaluation. Do not silently admit failed extraction tasks. Freeze
the admitted corpus and toolchain before running test conditions. The existing analyzer
reports `automatic_contract_proxy`; here that means STRUCTURAL ALIGNMENT ONLY, not
semantic faithfulness. Human-audit analysis remains to be implemented.

The toolchain file is scoped here, not the product root. The CLI checks the actual
Lean version. Source has one theorem with a fixed name, one-line statement, and a flat
list of tactic commands; snapshots preserve the entire goal set. This does not extract
an internal dependency graph or expose internal reasoning of automation tactics.

`D` feeds deterministic alignment failures back to the LLM. `E` gives render feedback
only, isolating that additional feedback with the same trace representation. `A/C`
receive proof source and state IDs but not the goal snapshots. `B` receives snapshots
without repair. `T` uses a deterministic storyboard with generic captions. All use
the same renderer; all are scored by the same evaluator. The schema itself is a plan;
there is no separate planner call in the MVP. `D/E/C` allow three generation calls;
`A/B` one. `R` independently resamples with the same maximum calls and the same
render-plus-alignment selection rule as D, without exposing feedback to the model.

Reuses `ResearchLLM` and `DockerExecutor`; the latter still emits its old calculus
probe, which is irrelevant to Lean evidence and must never be scored as proof validity.
All rendered math panels are copied from snapshots. Unknown IDs show missing evidence,
not silently corrected states. Narration is visibly labeled unverified. The container
has no network or provider credentials. For deployment with external Lean input, add
an isolated Lean worker: string filtering is only corpus hygiene, not security.

## Immediate gate

Run extraction on the four development seeds with actual Lean; verify message positions,
final `no goals`, and axiom output. If the adapter fails, repair it against saved real
diagnostics, not fixtures. Then render T and inspect glyphs/layout. Only after both
gates should any paid model sweep begin. No sample videos or success rates exist yet.
