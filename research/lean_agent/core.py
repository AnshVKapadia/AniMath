from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ProofTask(Strict):
    id: str = Field(pattern=r'^[a-z0-9_-]+$')
    family_id: str
    split: Literal['dev', 'test']
    category: str
    difficulty: Literal['easy', 'medium', 'hard']
    prompt: str
    statement: str
    tactics: list[str] = Field(min_length=1, max_length=30)
    provenance: str
    license: str
    status: Literal['draft'] = 'draft'


class Snapshot(Strict):
    id: str
    goals: str


class Trace(Strict):
    source_sha256: str
    lean_version: str
    snapshots: list[Snapshot]
    axioms: list[str]


class VisualSpec(Strict):
    kind: Literal['introduce_facts', 'split_goal', 'select_fact', 'swap_objects',
                  'choose_witness', 'rewrite_expression', 'show_subset', 'proof_state']
    labels: list[str] = Field(min_length=1, max_length=4)

    @model_validator(mode='after')
    def validate_labels(self):
        expected = {
            'introduce_facts': 2, 'split_goal': 2, 'select_fact': 1,
            'swap_objects': 2, 'choose_witness': 1,
            'rewrite_expression': 2, 'show_subset': 2, 'proof_state': 1,
        }[self.kind]
        if len(self.labels) != expected:
            raise ValueError(f'{self.kind} requires exactly {expected} label(s)')
        if any(not label.strip() or len(label) > 40 or '\n' in label for label in self.labels):
            raise ValueError('Visual labels must be 1-40 characters on one line')
        return self


class Beat(Strict):
    before: str
    after: str
    narration: str = Field(min_length=1, max_length=240)
    visual: VisualSpec


class Storyboard(Strict):
    beats: list[Beat] = Field(min_length=1, max_length=30)


def source_for(task: ProofTask):
    """Only run curated repository tasks, never untrusted Lean on the host.

    This guard rejects obvious gaps but is NOT a sandbox or a complete Lean parser.
    Flat tactic sequences can have multiple goals; each snapshot retains ALL goals.
    """
    content = task.statement + '\n' + '\n'.join(task.tactics)
    if re.search(r'\b(sorry|admit|axiom|unsafe|run_tac|set_option)\b', content):
        raise ValueError('Unsupported proof construct or proof gap')
    if '\n' in task.statement or any('\n' in t for t in task.tactics):
        raise ValueError('MVP accepts single-line statements and tactic commands')
    lines = ['import Lean', f'theorem benchmark_proof : {task.statement} := by']
    trace_lines = []
    for tactic in task.tactics:
        lines.append('  trace_state')
        trace_lines.append(len(lines))
        lines.append('  ' + tactic)
    lines.append('  trace_state')
    trace_lines.append(len(lines))
    lines.append('#print axioms benchmark_proof')
    return '\n'.join(lines) + '\n', trace_lines


def parse_trace(stdout: str, source: str, trace_lines: list[int], version: str):
    """Fail closed on missing/ambiguous messages or unapproved axiom dependencies.

    Lean --json integration must be smoke-tested with the pinned toolchain before
    benchmark admission. Unit fixtures do not establish adapter compatibility.
    """
    messages = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    if any(m.get('severity') in {'error', 'warning'} for m in messages):
        raise ValueError('Lean emitted an error or warning')
    states = []
    for index, line in enumerate(trace_lines):
        matching = [m['data'] for m in messages
                    if m.get('pos', {}).get('line') == line and isinstance(m.get('data'), str)]
        if len(matching) != 1:
            raise ValueError(f'Missing or ambiguous trace at line {line}')
        states.append(Snapshot(id=f's{index}', goals=matching[0]))
    if states[-1].goals.strip() != 'no goals':
        raise ValueError('Final trace does not show proof completion')
    audits = [m.get('data', '') for m in messages if 'benchmark_proof' in m.get('data', '')
              and ('depends on axioms' in m.get('data', '') or 'does not depend on any axioms' in m.get('data', ''))]
    if len(audits) != 1:
        raise ValueError('Missing or ambiguous axiom audit')
    audit = audits[0]
    if 'does not depend on any axioms' in audit:
        axioms = []
    else:
        match = re.search(r'depends on axioms:\s*\[([^]]*)\]', audit)
        if not match:
            raise ValueError('Unrecognized axiom audit format')
        axioms = [x.strip() for x in match[1].split(',') if x.strip()]
    if set(axioms) - {'propext', 'Classical.choice', 'Quot.sound'}:
        raise ValueError('Unapproved axiom dependency')
    return Trace(source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                 lean_version=version, snapshots=states, axioms=axioms)


def extract(task: ProofTask, out: Path, lean='lean'):
    """Trusted authored corpus only. Production service needs isolated Lean execution."""
    out.mkdir(parents=True, exist_ok=False)
    source, lines = source_for(task)
    path = out / 'proof.lean'
    path.write_text(source, encoding='utf-8')
    version = subprocess.run([lean, '--version'], check=True, capture_output=True,
                             text=True, timeout=15).stdout.strip()
    if not re.search(r'version 4\.19\.0(?:\D|$)', version):
        raise ValueError('This experiment pins Lean 4.19.0; select that toolchain')
    result = subprocess.run([lean, '--json', str(path.resolve())], capture_output=True,
                            text=True, timeout=60)
    (out / 'lean.stdout.jsonl').write_text(result.stdout)
    (out / 'lean.stderr.txt').write_text(result.stderr)
    if result.returncode:
        raise ValueError('Lean compilation failed; inspect saved diagnostics')
    trace = parse_trace(result.stdout, source, lines, version)
    (out / 'trace.json').write_text(trace.model_dump_json(indent=2))
    return trace


def verify(board: Storyboard, trace: Trace):
    expected = [(a.id, b.id) for a, b in zip(trace.snapshots, trace.snapshots[1:])]
    actual = [(b.before, b.after) for b in board.beats]
    known = {s.id for s in trace.snapshots}
    errors = []
    if any(a not in known or b not in known for a, b in actual):
        errors.append('unknown_state_reference')
    if any(pair not in expected for pair in actual):
        errors.append('unsupported_transition')
    if any(pair not in actual for pair in expected):
        errors.append('omitted_transition')
    if len(actual) != len(set(actual)):
        errors.append('duplicate_transition')
    if actual != expected and not errors:
        errors.append('transition_order')
    conceptual = all(beat.visual.kind != 'proof_state' for beat in board.beats)
    return {'structural_pass': bool(expected) and not errors,
            'conceptual_plan_pass': conceptual, 'errors': errors,
            'narration_verified': False, 'visual_correctness_verified': False}


def template(trace: Trace):
    return Storyboard(beats=[Beat(before=a.id, after=b.id,
                                 narration='The tactic changes the proof state shown below.',
                                 visual=VisualSpec(kind='proof_state', labels=['Formal step']))
                             for a, b in zip(trace.snapshots, trace.snapshots[1:])])


def compile_board(board: Storyboard, trace: Trace):
    """Compile a constrained graphical plan; narration and metaphors remain unverified.

    Unknown IDs render as explicitly missing evidence so non-verifier baselines
    can still render. There is NO automatic correction of storyboard references.
    """
    states = {s.id: s.goals for s in trace.snapshots}
    frames = [{'before_id': b.before, 'after_id': b.after,
               'before': states.get(b.before, 'MISSING EVIDENCE: ' + b.before),
               'after': states.get(b.after, 'MISSING EVIDENCE: ' + b.after),
               'narration': b.narration, 'kind': b.visual.kind,
               'labels': b.visual.labels} for b in board.beats]
    # repr creates Python string literals, never executable model-supplied code.
    return '''from manim import *
class GeneratedScene(Scene):
    def card(self, label, color=BLUE, width=2.6):
        box = RoundedRectangle(width=width, height=1.25, corner_radius=0.15,
                               color=color, fill_color=color, fill_opacity=0.14)
        text = Text(label, font_size=34)
        if text.width > width - 0.25:
            text.scale((width - 0.25) / text.width)
        return VGroup(box, text)

    def visual(self, frame):
        kind, labels = frame['kind'], frame['labels']
        if kind == 'introduce_facts':
            items = VGroup(*[self.card(x, c) for x, c in zip(labels, [BLUE, GREEN])]).arrange(RIGHT, buff=0.8)
            container = RoundedRectangle(width=6.8, height=2.2, corner_radius=0.2, color=YELLOW)
            cap = Text('Known together', font_size=26).next_to(container, UP)
            items.move_to(container)
            self.play(FadeIn(container), FadeIn(cap), LaggedStart(*[FadeIn(x, shift=UP) for x in items]))
            return VGroup(container, cap, items)
        if kind == 'split_goal':
            whole = self.card(' AND '.join(labels), PURPLE, 5.5)
            parts = VGroup(*[self.card(x, c) for x, c in zip(labels, [BLUE, GREEN])]).arrange(RIGHT, buff=1.1)
            self.play(FadeIn(whole))
            self.play(ReplacementTransform(whole, parts))
            return parts
        if kind == 'select_fact':
            fact = self.card(labels[0], GREEN).shift(LEFT * 3)
            goal = self.card('Goal: ' + labels[0], YELLOW).shift(RIGHT * 3)
            arrow = Arrow(fact.get_right(), goal.get_left(), color=WHITE)
            self.play(FadeIn(fact), FadeIn(goal), GrowArrow(arrow))
            token = self.card(labels[0], GREEN).scale(0.65).move_to(fact)
            self.play(token.animate.move_to(goal))
            return VGroup(fact, goal, arrow, token)
        if kind == 'swap_objects':
            left, right = self.card(labels[0], BLUE), self.card(labels[1], GREEN)
            left.shift(LEFT * 2.3); right.shift(RIGHT * 2.3)
            self.play(FadeIn(left), FadeIn(right))
            self.play(left.animate.shift(RIGHT * 4.6), right.animate.shift(LEFT * 4.6))
            return VGroup(left, right)
        if kind == 'choose_witness':
            target = self.card('Need an example', YELLOW, 4.2)
            witness = self.card(labels[0], GREEN).shift(DOWN * 2)
            self.play(FadeIn(target), FadeIn(witness))
            self.play(witness.animate.move_to(target))
            return VGroup(target, witness)
        if kind == 'rewrite_expression':
            before = self.card(labels[0], BLUE, 5.8)
            after = self.card(labels[1], GREEN, 5.8)
            self.play(FadeIn(before))
            self.play(ReplacementTransform(before, after))
            return after
        if kind == 'show_subset':
            outer = Ellipse(width=7, height=3.8, color=BLUE)
            inner = Ellipse(width=3.2, height=1.8, color=GREEN, fill_opacity=0.18)
            a = Text(labels[1], font_size=30).next_to(outer, UP)
            b = Text(labels[0], font_size=30).move_to(inner)
            self.play(Create(outer), FadeIn(a)); self.play(Create(inner), FadeIn(b))
            return VGroup(outer, inner, a, b)
        before = Text(frame['before'], font_size=25)
        after = Text(frame['after'], font_size=25)
        for obj in (before, after):
            if obj.width > 11: obj.scale(11 / obj.width)
            if obj.height > 3: obj.scale(3 / obj.height)
        self.play(FadeIn(before)); self.play(ReplacementTransform(before, after))
        return after

    def construct(self):
        frames = ''' + repr(frames) + '''
        for frame in frames:
            evidence = Text('Lean evidence: ' + frame['before_id'] + ' → ' + frame['after_id'],
                            font_size=21, color=GRAY_A).to_edge(UP)
            narration = Text(frame['narration'], font_size=26).to_edge(DOWN)
            if narration.width > 12: narration.scale(12 / narration.width)
            self.play(FadeIn(evidence), FadeIn(narration))
            artwork = self.visual(frame)
            self.wait(2)
            self.play(FadeOut(VGroup(evidence, narration, artwork)))
'''


SYSTEM = '''Create a conceptual visual proof storyboard, not a new proof. Output JSON only:
{"beats":[{"before":"s0","after":"s1","narration":"Short explanation",
"visual":{"kind":"split_goal","labels":["Q","P"]}}]}.
Use one beat for each adjacent proof-state transition in order, covering all tactics.
Choose a kind from introduce_facts, split_goal, select_fact, swap_objects,
choose_witness, rewrite_expression, show_subset. Labels must be short and conceptual.
Do not invent intermediate steps hidden inside automated tactics. Explain how the
visible hypotheses and goals change; a goal is an obligation, not an established fact.
The visual metaphor and narration are not formally certified. Do not claim that the
video itself is Lean-verified. Use proof_state only for the no-LLM baseline.'''


def run(task, trace, condition, llm, executor, out, max_attempts=3):
    """A source-only, B traced, C source+render repair, D traced+alignment repair,
    E traced+render repair, R independent traced samples, T no-LLM template.
    """
    if condition not in {'A', 'B', 'C', 'D', 'E', 'R', 'T'} or max_attempts < 1:
        raise ValueError('Invalid condition or budget')
    source, _ = source_for(task)
    if hashlib.sha256(source.encode()).hexdigest() != trace.source_sha256:
        raise ValueError('Proof/trace provenance mismatch')
    out.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    prompt = {'request': task.prompt, 'proof': source,
              'state_ids': [s.id for s in trace.snapshots]}
    if condition in {'B', 'D', 'E', 'R'}:
        prompt['trace'] = trace.model_dump()
    history = []
    selected = None
    attempts = 1 if condition in {'A', 'B', 'T'} else max_attempts
    infrastructure_error = False
    for index in range(attempts):
        event = {'attempt': index, 'rendered': False, 'structural_pass': False}
        try:
            if condition == 'T':
                board = template(trace)
            else:
                action = 'generate' if index == 0 else ('resample' if condition == 'R' else 'repair')
                raw = llm.call(json.dumps(prompt), SYSTEM, action)
                (out / f'candidate-{index}.txt').write_text(raw)
                try:
                    board = Storyboard.model_validate_json(raw)
                except ValueError:
                    event['category'] = 'storyboard_schema'
                    if condition != 'R':
                        prompt['feedback'] = {'category': 'storyboard_schema', 'candidate': raw}
                    history.append(event)
                    continue
            checks = verify(board, trace)
            observation = executor.render(compile_board(board, trace), out / f'attempt-{index}')
            event.update(rendered=observation.rendered, structural_pass=checks['structural_pass'],
                         conceptual_plan_pass=checks['conceptual_plan_pass'],
                         category=observation.category, checks=checks, video=observation.video)
            infrastructure_error = observation.infrastructure_error
            history.append(event)
            if infrastructure_error:
                break
            if observation.rendered and selected is None:
                selected = index
            if observation.rendered and (condition not in {'D', 'R'} or
                                         (checks['structural_pass'] and checks['conceptual_plan_pass'])):
                selected = index
                break
            if condition == 'R':
                continue
            prompt['previous_storyboard'] = board.model_dump()
            prompt['feedback'] = {'rendered': observation.rendered,
                                  'category': observation.category, 'details': observation.details}
            if condition == 'D':
                prompt['feedback']['alignment'] = checks
        except Exception as exc:
            infrastructure_error = True
            event.update(category='infrastructure_or_harness', error_type=type(exc).__name__)
            history.append(event)
            break
    chosen = next((h for h in history if h['attempt'] == selected), {})
    result = {'task_id': task.id, 'family_id': task.family_id, 'condition': condition,
              'replicate': 0, 'source_sha256': trace.source_sha256,
              'first_render': history[0]['rendered'], 'final_render': bool(chosen.get('rendered')),
              'automatic_pass': bool(chosen.get('structural_pass')),
              'conceptual_plan_pass': bool(chosen.get('conceptual_plan_pass')),
              'semantic_faithfulness': None, 'selected_attempt': selected,
              'n_attempts': len(history), 'seconds': perf_counter() - started,
              'input_tokens': getattr(llm, 'input_tokens', 0),
              'output_tokens': getattr(llm, 'output_tokens', 0),
              'n_calls': getattr(llm, 'calls', 0), 'infrastructure_error': infrastructure_error,
              'history': history}
    (out / 'result.json').write_text(json.dumps(result, indent=2))
    return result
