"""Run curated corpus only. No network/model calls unless `evaluate` is selected."""
import argparse
import json
import random
from pathlib import Path

from .core import ProofTask, Storyboard, extract, run


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['schema', 'extract', 'evaluate'])
    p.add_argument('--tasks', type=Path, default=Path('research/lean_agent/seeds.jsonl'))
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--conditions', nargs='+', choices=list('ABCDE') + ['R', 'T'], default=['T'])
    p.add_argument('--seed', type=int, default=20260909)
    p.add_argument('--replicates', type=int, default=1)
    p.add_argument('--max-attempts', type=int, default=3)
    p.add_argument('--curated-local-corpus', action='store_true',
                   help='Confirm these Lean tasks were inspected and are trusted local code')
    args = p.parse_args()
    if args.action == 'schema':
        args.out.mkdir(parents=True, exist_ok=False)
        for name, model in [('task', ProofTask), ('storyboard', Storyboard)]:
            (args.out / (name + '.schema.json')).write_text(json.dumps(model.model_json_schema(), indent=2))
        return
    if not args.curated_local_corpus:
        p.error('Lean is executable code: inspect corpus, then pass --curated-local-corpus')
    tasks = [ProofTask.model_validate_json(x) for x in args.tasks.read_text().splitlines() if x.strip()]
    if not tasks or len({t.id for t in tasks}) != len(tasks):
        p.error('Empty corpus or duplicate task IDs')
    if args.replicates < 1 or args.max_attempts < 1 or len(set(args.conditions)) != len(args.conditions):
        p.error('Invalid repetition count, budget, or duplicate conditions')
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'config.json').write_text(json.dumps(vars(args), default=str, indent=2))
    traces = {t.id: extract(t, args.out / 'traces' / t.id) for t in tasks}
    if args.action == 'extract':
        return
    from research.mathimate_agent.execution import DockerExecutor
    from research.mathimate_agent.llm import ResearchLLM
    executor = DockerExecutor()
    executor.preflight()
    schedule = [(t.id, c, r) for t in tasks for c in args.conditions for r in range(args.replicates)]
    random.Random(args.seed).shuffle(schedule)
    (args.out / 'schedule.json').write_text(json.dumps(schedule))
    lookup = {t.id: t for t in tasks}
    with (args.out / 'results.jsonl').open('x') as results:
        for tid, condition, rep in schedule:
            path = args.out / 'runs' / f'{tid}-{condition}-{rep}'
            path.parent.mkdir(parents=True, exist_ok=True)
            llm = None if condition == 'T' else ResearchLLM(args.out / f'{tid}-{condition}-{rep}.calls.jsonl')
            row = run(lookup[tid], traces[tid], condition, llm, executor, path, args.max_attempts)
            row['replicate'] = rep
            (path / 'result.json').write_text(json.dumps(row, indent=2))
            results.write(json.dumps(row) + '\n')
            results.flush()
            if row['infrastructure_error']:
                raise RuntimeError('Infrastructure/harness failure; partial run is not an experiment')


if __name__ == '__main__':
    main()
