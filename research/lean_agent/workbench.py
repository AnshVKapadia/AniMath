"""Local single-proof workflow. Each revision is saved; no automatic paid calls."""
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .core import ProofTask, Trace, Storyboard, SYSTEM, extract, source_for, verify, compile_board
from .demo import fixture, page


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def doctor():
    report = {'python_dependencies': {p: importlib.util.find_spec(p) is not None
              for p in ['pydantic', 'openai', 'dotenv']}, 'lean': None, 'docker': None}
    for name, command in [('lean', ['lean', '--version']), ('docker', ['docker', 'info'])]:
        if shutil.which(name):
            try:
                proc = subprocess.run(command, capture_output=True, text=True, timeout=15)
                report[name] = {'available': proc.returncode == 0}
                if name == 'lean':
                    report[name]['version'] = proc.stdout.strip()
            except (OSError, subprocess.TimeoutExpired):
                report[name] = {'available': False}
    try:
        from app.config import get_settings
        s = get_settings()
        azure = [s.azure_openai_api_key, s.azure_openai_base_url, s.azure_openai_deployment]
        report['provider_configured'] = all(azure) if any(azure) else bool(s.openai_api_key)
        report['model'] = s.azure_openai_deployment if any(azure) else s.openai_model
    except ImportError:
        report['provider_configured'] = False
    return report


def new_project(root, task, simulated=False):
    root.mkdir(parents=True, exist_ok=True)
    project = root / (datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    project.mkdir()
    save(project / 'task.json', task.model_dump())
    save(project / 'project.json', {'schema_version': 1, 'simulated': simulated,
                                   'status': 'awaiting_trace'})
    return project


def load_project(project):
    task = ProofTask.model_validate_json((project / 'task.json').read_text(encoding='utf-8'))
    trace = Trace.model_validate_json((project / 'trace.json').read_text(encoding='utf-8'))
    source, _ = source_for(task)
    if hashlib.sha256(source.encode()).hexdigest() != trace.source_sha256:
        raise ValueError('Task changed after trace extraction. Start a new project.')
    return task, source, trace


def export_revision(project, board, revision=None):
    task, source, trace = load_project(project)
    if revision is None:
        revision = project / 'revisions' / uuid.uuid4().hex[:12]
        revision.mkdir(parents=True)
    checks = verify(board, trace)
    save(revision / 'storyboard.json', board.model_dump())
    save(revision / 'verification.json', checks)
    (revision / 'GeneratedScene.py').write_text(compile_board(board, trace), encoding='utf-8')
    simulated = json.loads((project / 'project.json').read_text(encoding='utf-8'))['simulated']
    preview = page(task, source, trace, board, checks)
    if not simulated:
        preview = preview.replace('Simulated input:', 'Locally extracted input:').replace(
            'these states resemble expected Lean output but have not been produced by Lean. This is a UI/data-flow demo, not an experiment.',
            'these states were extracted from Lean. The graphical interpretation and narration are not formally certified.')
    (revision / 'index.html').write_text(preview, encoding='utf-8')
    save(project / 'latest.json', {'revision': revision.name})
    return revision


def generate(project, feedback='', max_calls=3, model=None):
    if not 1 <= max_calls <= 5:
        raise ValueError('Choose 1 to 5 calls per revision')
    task, source, trace = load_project(project)
    previous = None
    if (project / 'latest.json').exists():
        name = json.loads((project / 'latest.json').read_text())['revision']
        previous = json.loads((project / 'revisions' / name / 'storyboard.json').read_text(encoding='utf-8'))
    revision = project / 'revisions' / uuid.uuid4().hex[:12]
    revision.mkdir(parents=True)
    if model is None:
        from research.mathimate_agent.llm import ResearchLLM
        model = ResearchLLM(revision / 'calls.jsonl')
    prompt = {'request': task.prompt, 'proof': source, 'trace': trace.model_dump(),
              'storyboard_schema': Storyboard.model_json_schema(),
              'user_feedback': feedback, 'previous_storyboard': previous}
    save(revision / 'request.json', prompt)
    last = None
    try:
        for attempt in range(max_calls):
            raw = model.call(json.dumps(prompt), SYSTEM, 'revise' if feedback else 'generate')
            (revision / f'candidate-{attempt}.txt').write_text(raw, encoding='utf-8')
            try:
                board = Storyboard.model_validate_json(raw)
                checks = verify(board, trace)
                last = board
                if checks['structural_pass'] and checks['conceptual_plan_pass']:
                    return export_revision(project, board, revision)
                prompt['repair_feedback'] = checks
            except ValueError as exc:
                prompt['repair_feedback'] = {'schema_error': str(exc)}
            prompt['last_candidate'] = raw
        if last is not None:
            # Export invalid candidates for inspection; report failed checks, never certify them.
            return export_revision(project, last, revision)
        raise ValueError('No valid storyboard JSON returned. Inspect candidate logs.')
    except Exception as exc:
        save(revision / 'error.json', {'type': type(exc).__name__})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['doctor', 'start', 'generate', 'revise', 'import', 'render'])
    parser.add_argument('--root', type=Path, default=Path('research/runs/projects'))
    parser.add_argument('--project', type=Path)
    parser.add_argument('--task', default='conjunction_commutes')
    parser.add_argument('--tasks', type=Path, default=Path(__file__).with_name('seeds.jsonl'))
    parser.add_argument('--fixture', action='store_true', help='Explicitly simulated proof input, not a checked proof')
    parser.add_argument('--curated-local-corpus', action='store_true')
    parser.add_argument('--feedback', default='')
    parser.add_argument('--storyboard', type=Path)
    parser.add_argument('--max-calls', type=int, default=3)
    args = parser.parse_args()
    try:
        if args.action == 'doctor':
            print(json.dumps(doctor(), indent=2)); return
        if args.action == 'start':
            if args.fixture:
                task, _, trace, board = fixture()
                project = new_project(args.root, task, True)
            else:
                if not args.curated_local_corpus:
                    parser.error('Inspect Lean tasks before passing --curated-local-corpus')
                tasks = [ProofTask.model_validate_json(line) for line in args.tasks.read_text(encoding='utf-8').splitlines() if line.strip()]
                matching = [task for task in tasks if task.id == args.task]
                if len(matching) != 1:
                    raise ValueError('Task ID must match exactly one corpus item')
                task = matching[0]
                project = new_project(args.root, task)
                print('Project:', project.resolve())
                trace = extract(task, project / 'extraction')
            save(project / 'trace.json', trace.model_dump())
            save(project / 'project.json', {'schema_version': 1, 'simulated': args.fixture, 'status': 'ready'})
            print('Project:', project.resolve())
            if args.fixture:
                print('Preview:', (export_revision(project, board) / 'index.html').resolve())
            else:
                print('Proof extracted. Next: generate --project "' + str(project.resolve()) + '"')
            return
        if args.project is None:
            parser.error('--project is required')
        if args.action in {'generate', 'revise'}:
            if args.action == 'revise' and not args.feedback.strip():
                parser.error('revise requires --feedback')
            revision = generate(args.project, args.feedback, args.max_calls)
            print('Preview:', (revision / 'index.html').resolve())
            print((revision / 'verification.json').read_text())
        elif args.action == 'import':
            if not args.storyboard:
                parser.error('import requires --storyboard')
            board = Storyboard.model_validate_json(args.storyboard.read_text(encoding='utf-8'))
            print('Preview:', export_revision(args.project, board) / 'index.html')
        else:
            from research.mathimate_agent.execution import DockerExecutor
            executor = DockerExecutor(); executor.preflight()
            name = json.loads((args.project / 'latest.json').read_text())['revision']
            revision = args.project / 'revisions' / name
            board = Storyboard.model_validate_json((revision / 'storyboard.json').read_text(encoding='utf-8'))
            _, _, trace = load_project(args.project)
            result = executor.render(compile_board(board, trace), revision / ('render-' + uuid.uuid4().hex[:8]))
            from dataclasses import asdict
            save(revision / 'last-render.json', asdict(result))
            print(result.video or result.category)
    except (ImportError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        # Do not expose transport errors that could contain credential-bearing URLs.
        parser.exit(1, f'{type(exc).__name__}: operation could not finish. Run doctor; inspect project diagnostics.\n')


if __name__ == '__main__':
    main()
