# MathimateAgent: proof-grounded visual explanations

Decision date: 9 September 2026. Independent project: no UNT/UT Southwestern data,
infrastructure, affiliation, funding claims, or unpublished ideas are imported.
The previous calculus research plan remains preserved, but is no longer the active plan.

## 1. Research decision and actual repository

Central question: **Does access to Lean proof-state traces, combined with explicit
evidence alignment and bounded repair, improve the faithfulness of LLM-generated
visual proof explanations compared with source-only generation?**

Input is an existing, fixed Lean proof plus an explanation request. Output is a short
visual explanation with links to actual proof states. This is NOT a theorem prover,
not a teacher study, and not a claim that Lean verifies arbitrary animations.

Inspected repository: AnshVKapadia/AniMath, product MathimateLM. `app/llm.py` already
has OpenAI/Foundry configuration, code generation, structured planning, and repair.
Its prompts are calculus/tutor-specific. `scene_plan.py` validates graph/equation
plans. `scene_compiler.py` deterministically compiles these into Manim. `rendering.py`
automatically executes code and has fallback, preemptive repair, and final repair;
these hidden calls are unsuitable as clean experimental conditions. `sandbox_rendering.py`
provides the existing remote rendering route. FastAPI/static UI stays unchanged.

Prior research harness already adds call/token logging, bounded execution, Docker
isolation, paired schedules, and family bootstrap analysis. Reuse the LLM logger and
Docker renderer directly. Replace only calculus contracts with proof-state contracts
and a small deterministic proof-panel compiler. Graph actions cannot represent Lean
goal sets without distorting their semantics, which justifies this new compiler.

New branch: `research/mathimate-agent-lean`, based on `research/mathimate-agent` at
44edadff5ca21dfe9a5532339dad66cb2f856c99. Product master and previous research remain intact.

## 2. Target venue, hard deadline, and submission reality

[Official VeriCodeGen CFP](https://vericodegen.github.io/cfp.html), checked September 9:

- Abstract September 11, 2026 AoE; full paper September 13 AoE. Dates are explicitly
  labeled tentative. Treat them as hard unless organizers publish a change.
- For scheduling: end of September 11 AoE is September 12 at 11:59:59 UTC; end of
  September 13 AoE is September 14 at 11:59:59 UTC. Submit well before these boundaries.
- Four to nine main-text pages including figures/tables; references excluded;
  unlimited appendix. Target four substantive pages, not an inflated nine.
- Workshop-specific `neurips_2026_vericode_workshop.tex` and
  `neurips_2026_vericode.sty`, linked via [Overleaf](https://www.overleaf.com/read/fhmwmtrgwkmc).
- Double blind, including code links and supplements. PDF limit 50 MB, supplement
  100 MB. Describe material LLM use. Do not link this identifiable repository in submission.
- Non-archival, with accepted papers on OpenReview, no formally published proceedings.
- Notification September 29; camera-ready October 14; workshop December 12, Atlanta.
- CFP includes explanations, human-centered verification, proof-assistant integration,
  generated-output checks, benchmarks, and negative results. This is a plausible fit
  via explanation reliability, not proof search. No detailed scoring rubric is posted.
  Minimum three reviews, at least one human; submission requires LLM-review consent.

No still-open, genuinely well-matched backup was confirmed. Do not treat
[MATH-AI](https://mathai-2026.github.io/) as open: its current deadline is September 6.
No claim that a four-day implementation makes acceptance likely. Four days is an
aggressive pilot-and-short-paper schedule, not time for broad validation.
Acceptance is a workshop-paper acceptance, not a NeurIPS main-track acceptance or
an award. The CFP separately offers actual best-paper awards; do not conflate them.

## 3. Prior work and the defensible gap

- [Paperproof](https://github.com/Paper-Proof/paperproof) already visualizes changes in
  Lean hypotheses/goals. Proof visualization itself is not novel.
- [Hattori et al., 2025](https://arxiv.org/abs/2509.09726) translate formal proof steps
  into natural language and summarize along proof structure, including Lean examples.
  LLM explanations from formal proofs are not novel either. Adapt a stepwise
  informalization baseline where feasible; do not claim a reproduction without it.
- [TheoremExplainAgent](https://arxiv.org/abs/2502.19400) is directly relevant to
  generated theorem-explanation videos; inspect its protocol before final comparisons.
- [ManimAgent](https://arxiv.org/abs/2606.30296) is relevant to agentic animation and
  execution/visual feedback. Merely adding a Lean call does not distinguish our method.
- [LeanTutor](https://arxiv.org/abs/2506.08321) uses Lean-grounded LLM feedback and
  offers PeanoBench with paired informal steps/tactics. Check license and task overlap
  before reuse; do not assume external data may be redistributed.
- Existing Lean animation demonstrations include
  [Tactics & Keyframes](https://www.youtube.com/watch?v=KuxFWwwlEtc).
  These further rule out any first-Lean-animation claim.

Potential contribution, still requiring evidence: a constrained proof-to-storyboard
interface plus an empirical separation of renderability, evidence alignment, and
semantic faithfulness under feedback. Agent loops, JSON planning, Docker, and logging
are implementations/adaptations, not new ML algorithms. A small curated evaluation
set supports the study; it is not yet a third major benchmark contribution.

## 4. Minimal system and exact trust boundary

1. Compile a fixed curated proof with a pinned Lean toolchain. Capture complete
   goal-state snapshots at tactic boundaries and audit theorem axiom dependencies.
2. Bind trace to source hash/version. Prompt the model with request, source, and,
   in trace conditions, snapshots. Generate a typed storyboard in one call.
3. Storyboard beats cite before/after snapshot IDs and provide short narration.
   The deterministic compiler copies the cited goal/hypothesis panels into Manim.
4. Execute in the reused restricted Docker renderer. Observe diagnostics and artifact.
5. Verify ID existence, supported transitions, order, duplication, and coverage.
   Full condition supplies these errors and render diagnostics for a replacement plan.
6. Stop on render plus structural pass, three generation attempts, or infrastructure
   failure. Preserve the first renderable candidate if subsequent repairs regress.

State: immutable task/source/hash/toolchain/trace; condition and budgets; current
storyboard; candidate history; render observations; alignment checks; selected artifact;
call/token counts and latency. Actions are generate/revise storyboard and invoke
compile/render/check through a tightly controlled loop. The agent cannot alter the
theorem, add axioms, rewrite the trace, or certify its own narration.

The MVP uses the storyboard as its plan, not an extra marketing planner agent. Trace
extraction is a prerequisite, not repeated proof search. Flat tactic commands can
produce several goals; snapshots preserve all of them. No internal proof DAG or
automation internals are currently extracted. Do not narrate hidden `simp`/`omega`
derivations as observed facts. Start with elementary logic, equality, witnesses, and
natural-number proofs; not advanced calculus formalization.

Lean validates the input theorem relative to its axioms. Structural checks validate
references, NOT the meaning of narration, educational effectiveness, or every pixel.
The renderer itself belongs to the trusted implementation and still needs visual QA.
Hash binding protects against accidental mismatches, not a malicious forged trace.
Only trusted authored proofs run on the host; external Lean code requires sandboxing.

VLM verification: optional layout audit after pilot, not a formal oracle. SymPy:
unnecessary for this MVP; Lean already supplies the mathematical proof. Add it only
for a separately evaluated numerical illustration, never as evidence of logical equivalence.

## 5. Benchmark design

Working label: MathimateAgent proof-explanation evaluation set. Do not launch a
second brand until it is worth maintaining. Target **120 test tasks from at least
30 theorem families**, plus 12 separate-family development tasks. Prefer 60–120 genuinely
distinct proofs over cosmetic variable renaming. Cluster all variants of the same
theorem/family. If only 30–50 audited proofs fit the deadline, report that smaller pilot.

Proposed strata, 20 test items each: equality/rewriting; propositional logic;
quantifiers/witnesses; natural-number arithmetic; induction/recursive reasoning;
elementary functions/sets. Last two require tooling/corpus expansion and are not
supported by the four current seeds. Difficulty: 40 easy, 50 medium, 30 hard, defined
by tactic count, branching and dependencies, not a model's subjective label.

Store JSONL: id, family_id, split, category, difficulty, prompt, statement, tactics,
provenance URL/revision/license, curation status. Derived records store source hash,
toolchain/library lock, complete snapshots, axiom audit, supported transition IDs,
required coverage, compilation/extraction diagnostics. Generate schema from Pydantic.
The current seed schema deliberately permits only draft status: compilation evidence
is a separate output and cannot be asserted by an input flag.

Example: explain `∀ P Q : Prop, P ∧ Q → Q ∧ P`. Tactics introduce P,Q,h, use
constructor, then exact h.2 and exact h.1. Requirements: show the assumption; show
both new obligations; link each discharge to its observed state; preserve order;
never describe a pending goal as proved. First four requirements can be structurally
checked; last one needs narration review or a separately validated semantic checker.

No large annotation effort: automatic extraction/coverage for all tasks, plus a
blinded stratified audit of approximately 30 tasks across selected conditions.
Budget 90–120 short outputs, with a second competent reviewer on 20–25% if available.
Rubric: supported reasoning, correct assumption/goal distinction, no invented tactic
internals, no omitted essential branch, readability. Record disagreements. A model
judge can triage but cannot replace independent ground truth. If no qualified human
audit is feasible, narrow the claim to structural alignment, acknowledging its weakness.

Inject wrong IDs, swapped states, omitted branches, duplicate steps, altered hypotheses,
and false narration into a held-out validation suite. Report which mutations the
checker detects and explicitly which semantic errors it misses. Freeze checks before test.

## 6. Experiments and statistical reporting

| Arm | Input/planning | Repair observation | Status |
|---|---|---|---|
| A | Source-only storyboard, one call | None | Implemented |
| B | Source + trace storyboard, one call | None | Implemented |
| C | Source-only storyboard | Render/schema errors | Implemented |
| D | Source + trace storyboard | Render/schema + alignment errors | Implemented |
| E | Same as D | Render/schema only | Implemented |
| T | Deterministic state viewer, no LLM | None | Implemented |
| R | Independent trace-conditioned samples, equal budget | No feedback | Implemented |

All arms use the same storyboard schema, math-panel renderer, model, decoding settings,
public requirements, and post-hoc evaluator. Thus source-only arms are not freeform
Manim baselines and must not be described as such. The original four-arm planning
experiment is replaced because the research question changed. Primary contrast D–E
isolates alignment feedback. B–A examines trace access. D–B mixes repair and added
compute, so use R before attributing gains to feedback rather than extra sampling.

Primary substantive outcome: blinded semantic faithfulness. Essential secondary
outcomes: structural alignment, first/final render rate, rescue fraction among initially
failed cases, regression fraction, attempts, calls, input/output/cached tokens, and
wall latency. Render success alone is not the paper's contribution. Report actual cost
only using dated provider prices and cached-token accounting. Optional: VLM aesthetics,
video duration, OCR, broader models, user preferences. No student/teacher study.

Run paired conditions on every task; randomize execution order. At least two independent
runs if affordable, acknowledging provider nondeterminism. Report raw numerators and
denominators, paired differences, 95% family-cluster bootstrap intervals (5,000 draws).
Keep repeated runs and variants in the same cluster. For truly independent binary task
pairs, exact McNemar is a secondary check, not a substitute for family clustering.
Predeclare one primary comparison/outcome; label others exploratory or adjust multiple
tests with Holm. Avoid category-level significance claims from 20 items. Do not silently
drop failed tasks, infrastructure failures, or missing paired cells. Current analyzer
implements render/structural summaries and cluster intervals, not human-audit inference.

## 7. Operational failure taxonomy

| Failure | Labeling rule |
|---|---|
| Invalid input proof | Lean nonzero exit/error; exclude before frozen corpus admission |
| Unsupported axiom/gap | Axiom audit outside allowlist; fail corpus admission |
| Trace/provenance failure | Missing snapshot, unresolved terminal goals, hash mismatch |
| Invalid storyboard | JSON/Pydantic failure |
| Hallucinated evidence | Referenced ID absent from trace |
| Unsupported transition | Before/after pair not adjacent in frozen trace |
| Coverage/order error | Missing, duplicated, or permuted required transition |
| Render/tool failure | Existing exception classifier: syntax/import/API/value/timeout |
| Mathematical narration error | Blinded audit: false implication, goal/assumption confusion |
| Invented internal reasoning | Narration claims unobserved automation steps; audit |
| Layout failure | Missing glyphs, unreadable scaling, clipping/overlap; visual audit |
| Repair regression | Previously satisfied render/check becomes unsatisfied |
| Infrastructure failure | Missing executable/provider error/container unavailable; separate |

Allow multiple labels. Store first failing stage separately. API errors from a deterministic
compiler are implementation failures, not automatically model reasoning failures.

## 8. Priorities and skeptical-reviewer mitigation

Must have: real Lean extraction smoke test; fixed checked proof corpus; immutable evidence;
trace-aware storyboard; deterministic renderer; A/B/D/E/T and equal-budget control;
logs; paired metrics; small narration audit; four-page anonymized paper. No frontend work.

Strongly recommended: second audit rater, family holdout, source-based informalization
baseline informed by prior work, checker mutation suite, a few real-library proofs with
proper licensing, archived environment locks and anonymous artifact.

Optional: VLM layout feedback, mathlib breadth, internal proof DAG, geometric animation,
additional models. No fine-tuning, RL, multi-agent role proliferation, or proof search.

Reviewer criticisms and cheapest credible responses:

- "LLM wrapper/existing repair": acknowledge adaptation; provide controlled D–E and
  equal-budget comparisons and concrete failure analysis, not algorithmic novelty claims.
- "Already Paperproof/informalization": include no-LLM trace viewer and stepwise
  informalization baseline. Test narration errors rather than claim first visualization.
- "Lean/Manim too niche": frame as evidence-grounded generation with an explicit trust
  boundary; generalization remains unproven, not asserted.
- "Synthetic benchmark": disclose authored/templated origin, family splits, licenses;
  include independently sourced proofs where feasible; report effective family count.
- "Render does not mean correct": separate render, alignment, and human semantic audit.
- "Engineering, not ML": test a falsifiable behavior hypothesis with matched controls.
  If alignment is trivial or narration does not improve, report that honestly; a polished
  demo alone is weak evidence for this venue.
- "Checking IDs is tautological": agree. Audit narration, measure checker blind spots,
  and compare against T. If T is equally good, simplify the system and report the result.

## 9. Paper package

Candidate titles:

1. MathimateAgent: Evaluating Proof-Grounded Visual Explanations from Lean
2. From Checked Proofs to Visual Explanations: Measuring Faithfulness Beyond Rendering
3. Can Proof-State Feedback Improve LLM-Generated Visual Explanations?

### Draft abstract (prospective; replace with actual findings before submission)

Large language models can generate compelling mathematical explanations, but a
successfully rendered animation need not faithfully represent a proof. We propose
MathimateAgent, a constrained system for producing visual explanations from existing
Lean proofs. Rather than asking a model to invent mathematical intermediate states,
the system extracts tactic-boundary proof states and asks the model to construct a
storyboard whose scenes reference this evidence. A deterministic compiler renders
the referenced states, while an execution-and-alignment loop identifies invalid
references, omitted transitions, and rendering failures for bounded repair. The
approach explicitly separates Lean's validation of the input proof from structural
alignment of the storyboard and semantic faithfulness of its natural-language
narration. We design a paired evaluation comparing source-only generation,
trace-conditioned generation, execution-only repair, alignment-guided repair, and
a non-LLM proof-state viewer. Evaluation combines automatic structural checks with
a small blinded audit of narration and reports compute costs and repair regressions.
The study is intended to establish when formal execution traces help generated
explanations, and where a checked proof still fails to provide guarantees about its
presentation. No empirical improvement is assumed in advance.

Two explicit prospective contributions: (1) an evidence-linked storyboard interface
and bounded inference implementation with a documented trust boundary; (2) a
reproducible comparative study and curated task set distinguishing rendering,
structural alignment, and semantic faithfulness. Neither is established until evaluated.

Four-page outline: Introduction + related work (0.75 page); method and trust boundary
(1 page); evaluation protocol/data (0.75 page); actual results and failures (1 page);
limitations/conclusion (0.5 page). References outside main text; schemas and prompts
in appendix. Allocate space for figures within these budgets.

Figure 1: one proof with before/after goal states, evidence-ID storyboard, generated
panels, and feedback. Shade Lean-checked input, structurally checked links, and
unverified narration differently. This should explain the trust boundary, not imply
an end-to-end formal guarantee.

Figure 2: paired semantic/structural success versus model calls, showing D, E, and
fresh-sampling R with intervals. If data are insufficient, use an audited failure
case showing a correct proof and a misleading explanation, not a fabricated plot.

Table 1: comparison with Paperproof, stepwise informalization, TheoremExplainAgent,
and this system: formal-proof input, proof-state evidence, visualization, feedback,
evaluated faithfulness. Mark unknown attributes unknown until full papers are read.

Main experiment table columns: condition; n proofs/families; first render n/N; final
render n/N; structural pass n/N; audited semantic pass n/N and interval; repair rescue;
mean calls; median latency; tokens/cost. All cells remain blank until real runs.

Limitations: small/nonrepresentative corpus, public-proof contamination, narrow tactic
support, opaque automation, annotations with imperfect agreement, no learning study,
rendering/font risks, no formal narration guarantee, one model and limited repetitions,
unproven transfer outside Lean, possible template advantage. Related-work categories:
proof visualization; formal-to-informal translation; theorem-explanation generation;
proof-assistant interfaces; execution-guided code repair; faithfulness evaluation;
LLM judges and their calibration limitations.

## 10. Four-day execution order and stop gates

1. September 9: run real Lean and template render; inspect four traces/videos. If this
   cannot be made reliable quickly, stop broad corpus work. Finish novelty comparison.
2. September 10: freeze a small admitted corpus and checks; run A/B/D/E/T pilot plus
   equal-budget control. Audit at least ten examples. Decide if there is a research signal.
3. Before September 11 abstract deadline: submit a truthful anonymous abstract only if
   the pilot supports a feasible study. User handles account/author declarations/submission.
4. September 11–12: run frozen paired evaluation, do blinded audit, compute intervals;
   write actual results including negative outcomes. Scale corpus only if reliable.
5. September 13: verify citations, limits, anonymity, disclosures, artifacts and counts;
   submit before AoE. Never trade correctness for the target date.

Current completion: research branch, schema, extraction adapter scaffold, compiler,
bounded loop, paired runner, four draft seeds, eleven passing unit tests, and this plan.
Blocked/unvalidated: actual Lean extraction, Docker render, live model generation,
benchmark expansion/admission, semantic audit, and experimental results. The wider
old harness tests could not run in this session because openai/dotenv are missing.
