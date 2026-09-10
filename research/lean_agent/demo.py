"""Offline storyboard demo using an explicitly simulated Lean trace.

This demonstrates the data flow and structural verifier. It is not evidence that
Lean extraction, LLM generation, or Manim rendering works in the current machine.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

from .core import Beat, ProofTask, Snapshot, Storyboard, Trace, compile_board, source_for, verify


def fixture():
    tasks = [ProofTask.model_validate_json(line) for line in
             Path('research/lean_agent/seeds.jsonl').read_text(encoding='utf-8').splitlines()
             if line.strip()]
    task = next(task for task in tasks if task.id == 'conjunction_commutes')
    source, _ = source_for(task)
    trace = Trace(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        lean_version='SIMULATED FIXTURE — NOT RUN THROUGH LEAN',
        snapshots=[
            Snapshot(id='s0', goals='⊢ ∀ P Q : Prop, P ∧ Q → Q ∧ P'),
            Snapshot(id='s1', goals='P Q : Prop\nh : P ∧ Q\n⊢ Q ∧ P'),
            Snapshot(id='s2', goals='case left\nP Q : Prop\nh : P ∧ Q\n⊢ Q\n\ncase right\nP Q : Prop\nh : P ∧ Q\n⊢ P'),
            Snapshot(id='s3', goals='P Q : Prop\nh : P ∧ Q\n⊢ P'),
            Snapshot(id='s4', goals='no goals'),
        ],
        axioms=[],
    )
    board = Storyboard(beats=[
        Beat(before='s0', after='s1', narration='Assume we already know both P and Q.'),
        Beat(before='s1', after='s2', narration='To prove Q and P together, split the task into proving Q and proving P.'),
        Beat(before='s2', after='s3', narration='The Q part of our original assumption completes the first task.'),
        Beat(before='s3', after='s4', narration='The P part completes the remaining task, so the proof is finished.'),
    ])
    return task, source, trace, board


def page(task, source, trace, board, checks):
    frames = []
    states = {state.id: state.goals for state in trace.snapshots}
    for index, beat in enumerate(board.beats, 1):
        frames.append({'step': index, 'before': states[beat.before],
                       'after': states[beat.after], 'narration': beat.narration})
    data = json.dumps(frames).replace('</', '<\\/')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>MathimateAgent fixture demo</title><style>
body{{font:17px system-ui;background:#0c1222;color:#eef2ff;margin:0}}main{{max-width:1050px;margin:35px auto;padding:24px}}
.warning{{background:#542f08;border:1px solid #f59e0b;padding:12px;border-radius:10px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.card{{background:#172036;border:1px solid #334155;border-radius:14px;padding:20px}}pre{{white-space:pre-wrap;font:18px ui-monospace;color:#c7d2fe}}
.explain{{font-size:24px;line-height:1.45}}button{{padding:10px 16px;margin-right:8px;font-size:16px}}small{{color:#a5b4fc}}
@media(max-width:760px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><main>
<h1>MathimateAgent storyboard preview</h1>
<p class="warning"><strong>Simulated input:</strong> these states resemble expected Lean output but have not been produced by Lean. This is a UI/data-flow demo, not an experiment.</p>
<p><strong>Proof request:</strong> {html.escape(task.prompt)}</p><p><strong>Theorem:</strong> {html.escape(task.statement)}</p>
<p><small>Structural verifier: {html.escape(json.dumps(checks))}</small></p>
<h2 id="title"></h2><div class="grid"><section class="card"><h3>Formal evidence</h3><h4>Before</h4><pre id="before"></pre><h4>After</h4><pre id="after"></pre></section>
<section class="card"><h3>Plain-language explanation</h3><p class="explain" id="narration"></p><p><small>This narration is not formally verified.</small></p></section></div>
<p><button onclick="move(-1)">Previous</button><button onclick="move(1)">Next</button></p>
<details><summary>Generated Lean source</summary><pre>{html.escape(source)}</pre></details>
<script>const frames={data};let i=0;function show(){{const f=frames[i];title.textContent=`Step ${{f.step}} of ${{frames.length}}`;before.textContent=f.before;after.textContent=f.after;narration.textContent=f.narration}}function move(d){{i=(i+d+frames.length)%frames.length;show()}}show();</script>
</main></body></html>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=Path('research/runs/fixture-demo'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    task, source, trace, board = fixture()
    checks = verify(board, trace)
    (args.out / 'proof.lean').write_text(source, encoding='utf-8')
    (args.out / 'simulated-trace.json').write_text(trace.model_dump_json(indent=2), encoding='utf-8')
    (args.out / 'storyboard.json').write_text(board.model_dump_json(indent=2), encoding='utf-8')
    (args.out / 'GeneratedScene.py').write_text(compile_board(board, trace), encoding='utf-8')
    (args.out / 'verification.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')
    (args.out / 'index.html').write_text(page(task, source, trace, board, checks), encoding='utf-8')
    print(f'Created offline preview: {(args.out / "index.html").resolve()}')
    print('Structural verification:', json.dumps(checks))
    print('Reminder: simulated trace, no Lean/LLM/Manim execution occurred.')


if __name__ == '__main__':
    main()
