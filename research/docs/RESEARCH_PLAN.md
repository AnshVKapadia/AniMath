# MathimateAgent: deadline-driven research plan

Prepared September 9, 2026. This is a research proposal and implementation status,
not an experimental paper or a claim of acceptance readiness.

**Recommendation.** Pursue a small empirical study of *specification-guided repair
of renderable mathematical visualization programs*. Keep MathimateAgent as the
system name. Treat the benchmark as a supporting evaluation suite, not a third
independent novelty claim. The central comparison is execution-only repair versus
repair informed by externally checked mathematical/visual contracts. A general
Manim agent, planner, render loop, or VLM critic is already prior art.

**Immediate decision.** The project is plausible for VeriCodeGen under its testing,
property-based validation and repair scope, but the remaining time is roughly four
days. It is not yet submission-ready. A validated checker and credible paired
results matter more than implementing every benchmark category or adding agents.

## 1. Venue verification and deadline

| Item | Current primary-source finding |
|---|---|
| Target | VeriCodeGen / AI for Verifiable Coding, NeurIPS 2026, research-paper track |
| Abstract | September 11, 2026, AoE |
| Paper | September 13, 2026, AoE |
| Length | 4–9 main-text pages, including figures/tables; references excluded; unlimited technical appendix |
| Files | Main PDF at most 50 MB; supplementary ZIP at most 100 MB |
| Format | `neurips_2026_vericode_workshop.tex` and `neurips_2026_vericode.sty`; do not alter style/margins/fonts |
| Review | Double blind, including linked code and supplementary material |
| Other requirements | Disclose methodologically relevant LLM use; required acknowledgement of possible LLM-assisted reviews |
| Notification / camera ready | September 29 / October 14, 2026 |
| Archival status | Not explicitly stated in the reviewed CFP; cannot verify archival or non-archival status |

Source: [official research CFP](https://vericodegen.github.io/cfp.html) and
[linked template](https://www.overleaf.com/read/fhmwmtrgwkmc). The template link
resolved, but its source files were not accessible for inspection here.

The site labels its dates **tentative**. Treat these current dates as binding for
planning; do not assume an extension. Under the conventional end-of-day AoE
interpretation, the abstract cutoff is September 12 at 11:59 UTC (6:59 a.m. CDT),
and the paper cutoff is September 14 at 11:59 UTC (6:59 a.m. CDT). Those clock-time
conversions are inferred from AoE; verify the actual submission-form cutoff.

The workshop emphasizes formal specifications and guarantees, but explicitly
includes compiler feedback, testing, debugging, property-based validation,
independent checking, benchmark design and negative results. Our scope fit is
**conditional**: testing task-specific numerical and geometric contracts is
relevant; “it rendered” alone is weak evidence for this venue. We must not describe
finite sampling or SymPy calculations as an end-to-end formal proof. No detailed
research-paper scoring rubric was found; competition scoring is unrelated.
[Workshop scope](https://vericodegen.github.io/)

Use the [research OpenReview venue](https://openreview.net/group?id=NeurIPS.cc/2026/Workshop/VERICODEGEN).
The later Lean competition deadline is not an extension for this project.

**Backups:** No suitable, still-open backup could be confirmed from the sources
checked. Do not plan around an unverified venue. The current
[MATH-AI site](https://mathai-2026.github.io/) says September 6, superseding older
September 25 announcements; [Verify-Agents](https://verify-agents-workshop.github.io/)
says August 29. Both are closed. Other currently open venues found were tied to
conversation, embodied spatial reasoning, life sciences or correspondence
challenges, requiring an unjustified scope change. This is a limitation of the
verified shortlist, not proof that no open suitable workshop exists anywhere.

## 2. Actual repository audit

Inspected `AnshVKapadia/AniMath`, whose README and application name are MathimateLM.
Base commit: `806d0b94680a37ad7dde2afd6c0467c578bdca3f`; default/production branch:
`master`. Retrieved all 35 tracked text files through the GitHub connection.
No repository `AGENTS.md` was present in the recursive listing.

| Component | Existing implementation | Research decision |
|---|---|---|
| `app/main.py`, `app/static/` | FastAPI generation endpoint and HTML/CSS/JS tutor UI | Preserve; exclude from experiments |
| `app/config.py` | Foundry/OpenAI credentials and model/deployment settings | Reuse; no new provider integration |
| `app/llm.py` | Responses API; structured planner; generation and repair prompts | Reuse client setup; add research prompts and usage logging |
| `app/scene_plan.py` | Pydantic graph/equation plans, 2–8 beats, action parameters, axis checks, caret normalization | Reuse unchanged for compiler comparator |
| `app/scene_compiler.py` | AST expression allowlist; deterministic Manim layouts; graph/point/secant/tangent/area/Riemann/equation actions | Reuse expression validation and whole compiler in supported comparator |
| `app/rendering.py` | Plan→compile→render; fallback generation; one final repair; preemptive LaTeX/layout repairs | Do not call wholesale inside A–D: hidden extra calls confound ablations |
| `app/sandbox_rendering.py` | Vercel Sandbox, network-denied outer environment, Manim 0.19 Docker image | Preserve production path; reuse image for local experiment worker |
| `scripts/benchmark_pipeline.py` | Three representative prompts and elapsed-time/pass logging | Useful smoke examples; insufficient experimental harness |
| `tests/` | Planner/compiler/fallback and deployment tests | Existing focused tests retained and exercised |

A nominal “one-shot” call through the product pipeline would **not** be one shot.
The structured planner can make two calls; free-form generation can trigger two
preemptive repairs; fallback and final repair add further calls. Successful render
currently terminates the product without a general post-render specification
checker. Layout-token heuristics are not video inspection. SDK transport retries
are also not research repair iterations.

The controlled compiler is restricted to a useful subset of mathematics. Feeding
unrestricted geometry/probability tasks through it would entangle architecture
with representational limitations. Therefore A–D use a common free-form generator;
the existing compiler is a separate comparator on supported tasks. This is an
experimental control reason for a new orchestration layer, not a product rewrite.

## 3. Prior work and defensible novelty

| Prior work | What it already covers | Implication |
|---|---|---|
| [Teaching LLMs to Self-Debug](https://arxiv.org/abs/2304.05128) | Code explanation, execution results, iterative repair | Execution feedback is established |
| [TheoremExplainAgent](https://arxiv.org/html/2502.19400v1) | Agentic Manim explanation generation; TheoremExplainBench with 240 theorems | Neither agentic mathematical animation nor its benchmarking is new |
| [ManimAgent](https://arxiv.org/html/2606.30296v1) | Storyboarding, coding, render/crash feedback, VLM keyframe critique, revision; additional cross-task memory | The proposed generic architecture has substantial direct overlap |
| [ManiBench](https://arxiv.org/pdf/2603.13251) | Renderability versus visual-logic drift, version/API issues and coverage; 12-task pilot described in the paper | Even the observation “render success differs from correctness” is prior art |

**Established adaptation:** single-agent orchestration, execution repair,
planning, bounded search, SymPy, runtime instrumentation, controlled compilation.

**Implementation work:** configuration, container wrapper, traces, log schema,
benchmark loader, experiment driver and plotting/statistics scripts.

**Potential empirical contribution, still unproven:** a controlled investigation
of whether lightweight runtime contracts add useful semantic repair information
beyond render errors, and where those contracts themselves fail. The interesting
result can be positive, null, or a documented reliability–cost tradeoff. Do not
claim the first mathematical visualization agent, first Manim benchmark, first
semantic verifier, or a new learning algorithm. The searched literature supports
these cautions; it does not establish that every possible narrower novelty claim
is unique.

Use two explicit contributions:

1. A reproducible evaluation protocol that separates renderability, checked
   contract satisfaction and independently audited visual/mathematical fidelity.
2. A bounded agent implementation and paired ablation of execution-only versus
   specification-guided repair, including verifier errors and repair regressions.

Release the small suite as supporting material under a provisional MathVizBench
name. A third headline benchmark contribution needs evidence of coverage,
annotation quality, discriminative value and meaningful difference from existing
benchmarks. We do not yet have that evidence.

## 4. Minimal agent architecture

State is `(task, public requirements, plan, current code, attempt history,
observations, remaining calls/attempts, selected artifact, termination reason)`.
It is serializable after each action. There is one model-driven controller.

Actions are plan, generate, execute, verify, repair, optionally replan, and stop.
The code never needs a separate planner/reviewer identity or autonomous subagents.
The environment is a fixed Manim image in a network-disabled disposable container.
Observations are syntax rejection, exit status, traceback, timeout, artifact
presence and structured runtime snapshots. Host-side checks compare those
snapshots with independently authored requirements.

The initial plan describes 2–5 ordered steps with goals, objects, mathematical
facts and actions. On execution failure, return the actual diagnostic and prior
code. On a failed supported contract after successful rendering, return the
requirement ID and status; permit a revised plan, then a complete code replacement.
All calls, including planning, count against the budget. Correcting code by
replacement is a practical choice; it is not a novel repair technique.

Default cap: 3 candidates and 5 total calls per task for the full system, with
6,000 output tokens per call and a 150-second render timeout. These are pilot
settings, to be frozen only after measuring costs. Keep the best previously
renderable artifact if a later edit crashes; log both last-attempt and selected
artifact outcomes. Stop on checked automatic contract pass, budget exhaustion,
or infrastructure failure. “Automatic contract pass” is not “task fully solved.”

**SymPy: recommended and implemented for reference expressions.** Validate
expressions with the existing AST allowlist, convert to SymPy without evaluating
untrusted strings, and calculate numerical expectations outside the candidate
container. The current graph checker measures sampled displayed geometry, not
just a formula written by the LLM. Algebraic-equivalence checks on genuinely
executed math objects could be added later; checking a self-reported certificate
would be circular.

**VLM verifier: optional, not in the initial loop.** It is useful for layout,
object omissions and temporal ordering, but adds cost, stochastic judging and
self-confirmation risk. If added, evaluate it separately against a small blind
human audit; give it the original prompt and uniformly selected frames/video,
not the generating model's confidence or self-explanation. A final independent
assessment must not simply reuse the in-loop judge's score. Static frames cannot
fully establish temporal correctness.

## 5. MathVizBench design

Current draft: 120 test prompts = 6 categories × 4 families × 5 parameter variants,
plus 12 disjoint development tasks. Difficulty counts for test tasks are 30 easy,
60 medium and 30 hard. Difficulty is author-assigned and provisional.

| Category | Four test families |
|---|---|
| Algebra | Linear root; repeated quadratic root; completing square; two-line system |
| Functions | Vertical/horizontal translations; inverse line; piecewise continuity |
| Calculus | Secant/tangent; integral area; Riemann refinement; Taylor approximation |
| Geometry | Right triangle; circle sectors; point rotation; similar triangles |
| Linear algebra | Vector addition; diagonal map; projection; shear |
| Probability/statistics | Bernoulli; sample mean; uniform density; Bayes grid |

These 120 variants represent **24 concept families**, not 120 independent
problems. Prefer broadening families over adding numerical paraphrases if time
allows. Keep family IDs and bootstrap by family. Never tune prompts/checkers on
held-out model results, and never place variants from one family in both splits.

Each JSONL record has: stable ID, family ID, category, difficulty, split, prompt,
requirement list, provenance, draft/audited status and schema version. A
requirement has an ID, public description, checker kind, expected parameters,
tolerance and essential flag. Supported kinds are graph_function, point,
line_slope, text, moving_point and manual. The public model input contains the
prompt and requirement descriptions; checker implementation and expected-value
fields are not separately exposed. Requirements may naturally reveal correct
answers, so this is specification-following code generation, not an exam of
unaided mathematical problem solving.

For the derivative example, use requirements for the parabola, fixed point,
visible second-point motion, tangent incidence/slope, and displayed slope value.
Keep the correct direction of approach, fixed-point persistence, secant geometry,
and transition order as explicit review requirements until implemented and
validated. Seeing any moving point is insufficient to certify a secant limit.

**Annotation plan:** no large-scale label collection. Audit all 24 templates and
reference calculations, then spot-check their parameterizations. Generate a small
reference/mutation corpus of correct scenes and scenes with known errors. Review
roughly 24–40 blinded final videos, stratified by method, category, checker verdict
and difficulty, plus all high-impact checker disagreements. Have a second person
review a subset if feasible, report agreement and adjudication, and keep reviewer
recruitment independent of the research labs. The audit sample estimates checker
validity; it does not magically provide full-task ground truth for all 120 items.

**Deadline fallback:** if broad geometry/probability verification is too weak,
freeze a declared graph/calculus subset before testing and make the smaller scope
explicit. Do not report text-label presence as mathematical accuracy across all
six categories. A trustworthy smaller experiment is the feasibility priority.

## 6. Experiments, metrics and statistics

| Condition | Planning | Execution-driven repair | Contract-driven repair | Purpose |
|---|---|---|---|---|
| A | No | No | No | One-shot program generation |
| B | Yes | No | No | Effect of an explicit plan |
| C | No | Yes | No | Standard execution-repair baseline |
| D | Yes, optional replanning | Yes | Yes | Full MathimateAgent |
| E | Yes | Yes | No | Isolate the added verifier/replanning policy |
| R | No | Fresh independent candidates | No | Repeated-sampling control |

A–D alone confound planning and verification in C versus D. E is cheap and
necessary for the intended causal story. R addresses the obvious extra-sampling
explanation. All candidates receive the same public specifications, versioned
code prompt and environment. Evaluate every condition with the same external
measurement. A/B are rendered and graded but cannot repair from that feedback.

The implemented primary D–E comparison disables replanning in both conditions;
D alone receives contract feedback and may continue after a render succeeds.
The `--replan` option enables a separate D sensitivity ablation. Label that
variant explicitly; do not pool replanning-enabled and disabled runs.

Use one model/deployment first, recording actual returned identity, configuration
and date. Freeze it after the development pilot. A second model is strongly
recommended if the first run and budget allow it. Three independent replicates
are better than one; if only one is feasible, explicitly limit inference to that
sampled run. Seed task order and numeric data, and disclose when the API cannot
seed generation.

Budgets are shared ceilings, not matched actual compute. Report success curves
versus candidates and measured tokens/cost, and add one equal-token or equal-call
sensitivity comparison if claiming a compute-independent improvement. A useful
cheap diagnostic forks C/D/E repairs from identical saved first candidates;
this isolates recovery behavior from different initial samples. That paired
candidate-cache experiment is recommended but not yet implemented.

Essential endpoints:

- First-candidate and selected-final render success, over every scheduled task.
- Automatic contract satisfaction, **with checker coverage/type**; report the
  graph/geometric subset separately from text-only checks.
- Independently audited task satisfaction on the prespecified audit sample.
- Conditional recovery: initially failing → selected passing, with the exact
  denominator; separately count initially-renderable semantic failures.
- Calls/tokens, selected and attempted candidate counts, total latency, and
  regression frequency. Dollars are derived from dated provider rates plus
  render/judge charges, not guessed from model names.

Detailed aesthetics, VLM ratings, per-action timings and learning-style metrics
are optional. Runtime/repair failure taxonomy is useful compact supporting
analysis. Do not count infrastructure outages or missing dependencies as model
errors; preserve the interruption ledger and rerun the affected paired block.

For each main percentage show numerator/denominator and a 95% interval. Use a
paired **family-cluster bootstrap** for method differences; all replicates and
variants within a family remain together. Predeclare D–E as primary, D–C and D–R
as secondary. For a truly independent task collection, Wilson intervals and exact
McNemar tests are suitable; ordinary McNemar on these correlated variants would
understate uncertainty. Report effect sizes in percentage points, and avoid
category-level significance claims from 20 highly related items. If many formal
secondary hypothesis tests are added, use Holm correction or label exploratory.

With independent n=120 tasks, a proportion near 0.5 has roughly ±9 percentage
points of 95% sampling uncertainty; clustering can widen it substantially. This
scale cannot reliably resolve small gains. No power or acceptance guarantee is
implied. Current analysis implements paired family bootstrap and rejects missing
method cells or duplicate task/replicate cells.

**Scale:** one replicate of six conditions is 720 task-method episodes. The cap
is 1,680 renders and 2,160 model calls, not a promise that it will consume that
many. Measure 12 development tasks first. Estimate API cost as input/cache/output
token totals times current rates, then add render cost. Set a personal expenditure
limit before a full paid run; no paid run was launched here.

## 7. Operational failure taxonomy

Use a primary earliest blocking category plus secondary tags. Preserve exact
exception class, normalized traceback signature, stage, attempt and transition.
Do not make exclusive categories out of overlapping concepts.

| Label | Operational rule | Review needed? |
|---|---|---|
| Syntax/indentation | Python parsing raises SyntaxError/IndentationError | No |
| Missing import | ImportError/ModuleNotFoundError | Separate package installation failure from code import |
| Undefined name | NameError in candidate code | Usually no |
| API attribute/signature | AttributeError/TypeError, with symbol/version | Confirm against pinned API for hallucinated/deprecated tag |
| Runtime value/domain | ValueError, ZeroDivisionError, nonfinite math | Distinguish model misuse from infrastructure |
| LaTeX/toolchain | LaTeX-related render diagnostic | Check baseline LaTeX installation before blaming candidate |
| Invalid transformation | Exception during transform involving incompatible objects | Traceback tag plus small manual review |
| Specification omission | Failed requirement with valid supported observation | Alternative valid representations can cause false failures |
| Mathematical discrepancy | Sampled curve or line fails numerical contract | Report tolerance and evidence; not proof of every other property |
| Visual/layout | Frame-overflow diagnostic or blind reviewer observation | Yes; overflow heuristic alone is weak |
| Temporal/order | Violated ordered event requirement | Currently manual beyond coarse movement |
| Timeout/resource | Candidate exceeds wall/memory/process budget | Record separately from mathematical incorrectness |
| Repair regression | A previously passing render/check fails on later attempt | Computable from saved histories; not a root-cause class |
| Infrastructure/harness | Docker/API unavailable, transport failure, probe malfunction | Abort/repair infrastructure; preserve missingness |

The current classifier implements broad exception categories. Fine API version,
transformation and temporal tags remain review-assisted; do not claim they are
already fully automated. Seed the taxonomy before looking at comparative results.

## 8. Implementation priorities and status

**Must have for the paper:** frozen task definitions and valid references;
A–E plus a repeated-sampling control; isolated execution; complete attempt/token
logs; a validated contract subset; small independent final-video audit; paired
analysis; anonymized artifact; no invented results or unsupported novelty.

**Implemented now:** a research branch; isolated Python package; existing provider
reuse; A–E/R bounded loop; plan/repair/replan state; fresh Docker render directories;
source screening, time/resource caps; draft runtime probes; SymPy-backed sampled
geometry checks; explicit unknown/manual statuses; 132 draft records and JSON
Schema; manifest/schedule/call logs; analysis CLI; original compiler comparator;
10 research tests. The inspected original application files are unchanged.

**Not yet validated or completed:** real Docker/Manim execution; runtime probe
accuracy on actual videos; live API compatibility with the selected deployment;
mutation corpus; human audit; audited/frozen benchmark; full benchmark run;
candidate-sharing or exact-cost matching; second model; final manuscript/results.
The workspace lacks Docker, Manim and model credentials. Only deterministic
fixture tests and existing tests ran here. This is a clear implementation boundary,
not an end-to-end experimental success claim.

**Strongly recommended:** correct-scene plus semantic-mutation validation;
compiler comparator on supported tasks; small blind second-rater overlap; second
model; shared initial candidate diagnostic; render-success/semantic-success gap
analysis; inspect every checker false acceptance found in the audit.

**Optional:** VLM feedback ablation, temporal monitor refinement, more distinct
families, pretty animations, richer figure styling. No fine-tuning, RL, student or
teacher study, retrieval framework, frontend polish or multi-agent architecture.

## 9. Skeptical reviewer risks and cheapest credible responses

| Criticism | Cheapest credible mitigation |
|---|---|
| “Just an LLM wrapper” | Make the empirical question and controlled measurements the contribution; release trajectories and a reproducible protocol |
| “Execution repair already exists” | Cite it; compare against it; test the incremental value and failure modes of specification feedback |
| “Manim agents already exist” | Directly discuss TheoremExplainAgent/ManimAgent; avoid first-system claims; add a short matched-condition adaptation or qualitative comparison when reproducible |
| “Manim is niche” | Frame it as executable visual programs with continuous/temporal outputs; limit generalization claims; no need to bolt on another domain in four days |
| “Synthetic benchmark” | Disclose template generation, family dependence and AI assistance; audit references; add a few public/independently written prompts only after checking license and provenance |
| “Rendering is not correctness” | Separate all endpoints; use actual geometry checks; retain independent video review and unresolved properties |
| “The checker rewards its own mistakes” | Freeze checker before test; mutation-test it; measure false acceptance/rejection; do not headline only the in-loop score |
| “More compute explains gains” | E/R controls, usage logs, success-versus-budget curves, equal-budget sensitivity |
| “Engineering, not ML research” | Study general feedback/selection tradeoffs and characterize failures; a credible narrow empirical finding can support a workshop paper, but does not guarantee acceptance |
| “Too small/one model” | Family-aware intervals, raw counts, second model if feasible, restrained conclusions |
| “No formal guarantee” | Claim testing of bounded properties, state trusted components/tolerances, and use the CFP's testing/repair scope accurately |

The most serious acceptance threat is overlap plus weak verification, not the
absence of agent marketing. A tiny positive accuracy difference with an
unvalidated evaluator is not a convincing contribution.

## 10. Paper plan

Candidate titles:

1. **Beyond Render Success: Evaluating Specification-Guided Repair of Mathematical Visualization Programs**
2. **MathimateAgent: Execution and Contract Feedback for Mathematical Visualization Code**
3. **What Does Execution Feedback Fix? A Controlled Study of LLM-Generated Mathematical Animations**

Central question: **Under a fixed inference budget, how much does task-specific
contract feedback improve mathematical visualization program reliability beyond
execution-only repair?**

Secondary questions: Which renderable semantic errors are recovered? How much
cost does the checker/repair policy add? When do automatic checks disagree with
independent video assessment? Does planning help after the feedback policy is held
constant?

**Draft abstract (proposal tense; 173 words; replace with measured results before submission):**

Large language models can generate executable mathematical visualization programs,
but successful execution does not establish that an animation satisfies its
mathematical specification. We propose MathimateAgent, a bounded, single-agent
workflow that combines visualization planning, Manim code generation, execution,
and specification-guided repair. The workflow uses runtime observations of
rendered scene objects and deterministic checks of selected mathematical
properties to identify failures that execution errors alone cannot expose. We
design a small evaluation suite spanning six mathematical categories, with
explicit requirements and separate reporting of renderability, checked contract
satisfaction, and independently audited visual fidelity. Our planned experiments
compare one-shot generation, planning, execution-only repair, and the full workflow,
with additional controls for planning and repeated sampling. We will report paired
performance differences, repair regressions, verifier disagreements, and inference
cost under documented budgets. The study tests whether specification feedback
provides useful improvements beyond standard execution repair, rather than
assuming that a more elaborate agent is more reliable. We explicitly distinguish
finite runtime checks from formal correctness guarantees and examine the
limitations of automated evaluation for temporal visual programs.

Keep only two headline contributions from Section 3. Do not add an abstract
results sentence until experiments are finished, including null outcomes.

Four-page allocation, excluding references:

| Section | Approximate space | Content |
|---|---:|---|
| Introduction + related-work contrast | 0.65 page | Problem, question, nearest alternatives, two contributions |
| Method | 0.85 page | State/actions/budget, feedback interfaces, selection, guarantee boundary; Figure 1 |
| Evaluation protocol | 0.85 page | Tasks, contract coverage, baselines, audit, statistical unit; Table 1 |
| Results + failure analysis | 1.20 pages | Actual paired scores, budgets, errors, verifier disagreements; Figure 2 |
| Limitations + conclusion | 0.45 page | Scope, synthetic families, small sample, model/checker limits |

**Figure 1:** one controller loop with plan/code state, isolated Manim execution,
and host-side runtime contracts. Show two feedback edges: runtime error and
renderable contract violation. Place the independent final-video audit outside
the loop. Explicitly mark unverified visual properties rather than implying a
certified final animation.

**Figure 2:** two-panel empirical plot. Left: selected render success and audited
or explicitly labeled contract success versus candidate budget (1, 2, 3), with
family-cluster intervals. Right: transitions from “renderable but contract-failing”
to pass/still-fail/regressed, comparing D and E on shared initial candidates if
that diagnostic is run. If no shared-candidate experiment is available, use a
failure/coverage breakdown and do not imply shared starting states.

**Table 1 / experiment table:** rows A, B, C, E, D, R; columns model, maximum
candidate/call budget, first render n/N, final render n/N, automatic contract
satisfaction n/N plus coverage, audited satisfaction n/N (audit subset only),
mean repairs, total input/output tokens and median latency. Add a D–E paired
difference row with 95% family-bootstrap interval. Keep detailed per-category
counts, resource distributions and complete trajectories in the appendix.

Do not fill table cells with expected gains or illustrative percentages.

Anticipated limitations: 24 synthetic test families; subjective difficulty;
possible model contamination with common math examples; partial observation of
Manim object graphs; equivalent representations missed by probes; short animations
and limited temporal checks; narrow numerical tolerances; unverified visual
readability; noisy human/VLM judges; one model and limited repeats if constrained;
no formal universal guarantees; no cross-domain or educational-benefit evidence.

Related-work categories to cite: execution-guided program repair and Self-Debugging;
ReAct/Reflexion/Self-Refine as appropriate; planning and test-time search;
TheoremExplainAgent, ManimAgent and ManiBench; verifiable code generation and
specification/property-based testing; visual program synthesis and chart/code
evaluation; judge validation and evaluation leakage. Check original papers and
bibliographic metadata before final citation; do not pad the bibliography with
uncorroborated related-work names.

## 11. Execution-order checklist and four-day schedule

1. **Now, September 9:** confirm OpenReview account/profile access and the abstract
   form cutoff; choose the target model/deployment and a run budget. Create the
   abstract record before September 11 AoE; this has not been submitted for you.
2. **September 9:** on a Docker-equipped worker, run one known-good scene, one
   intentional runtime failure and one renderable mathematical mutation. Fix
   runtime/probe issues before paying for broad model generation.
3. **September 9–10:** run the 12-task development pilot; inspect outputs and cost;
   decide the supported contract subset; audit templates and numeric references.
4. **September 10:** freeze prompts/checkers/benchmark/model/budgets. Choose whether
   D replans in the primary contrast. Preregister the primary D–E comparison in a
   timestamped repository protocol; no external registration is necessary.
5. **September 10–11:** run the paired A–E/R experiment on the frozen suite. Prefer
   complete paired coverage and a validated subset over an incomplete broad run.
   Persist every candidate and infrastructure failure. Register the abstract.
6. **September 11–12:** audit blinded videos, validate checker disagreements,
   run the main paired analysis, and add the strongest affordable sensitivity
   check (shared candidates, budget matching, or a second model).
7. **September 12–13:** write the actual four-page paper in the workshop template;
   add measured results and limits; verify references, anonymize code/data, and
   review all figures and claims. Submit ahead of the September 13 AoE deadline.

**Go/no-go gate:** If by September 11 there is no validated semantic measurement
and complete paired pilot, do not invent a broad completed evaluation. A smaller
honest work-in-progress submission is possible only if it already contains a
concrete finding and meets the minimum length. Otherwise carry the project
forward to a later suitable venue. No implementation plan can ensure acceptance.
