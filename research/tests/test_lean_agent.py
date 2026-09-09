import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from research.lean_agent.core import (ProofTask, Snapshot, Trace, Storyboard,
                                     source_for, parse_trace, template, verify, compile_board, run)


def fixture():
    task = ProofTask.model_validate_json(Path('research/lean_agent/seeds.jsonl').read_text().splitlines()[0])
    source, _ = source_for(task)
    trace = Trace(source_sha256=hashlib.sha256(source.encode()).hexdigest(), lean_version='fixture-not-Lean',
                  snapshots=[Snapshot(id='s0', goals='⊢ ∀ P : Prop, P → P'),
                             Snapshot(id='s1', goals='P : Prop\nh : P\n⊢ P'),
                             Snapshot(id='s2', goals='no goals')], axioms=[])
    return task, trace


class FakeModel:
    calls = 0
    def __init__(self, answers):
        self.answers = iter(answers)
        self.prompts = []
    def call(self, *args):
        self.calls += 1
        self.prompts.append(args[0])
        return next(self.answers)


class FakeRenderer:
    def render(self, *args):
        return SimpleNamespace(rendered=True, category='ok', video=None,
                               infrastructure_error=False, details='')


class LeanAgentTests(unittest.TestCase):
    def test_schema_seeds(self):
        for line in Path('research/lean_agent/seeds.jsonl').read_text().splitlines():
            source_for(ProofTask.model_validate_json(line))

    def test_template_is_not_semantic_certificate(self):
        _, trace = fixture()
        result = verify(template(trace), trace)
        self.assertTrue(result['structural_pass'])
        self.assertFalse(result['narration_verified'])

    def test_missing_transition(self):
        _, trace = fixture()
        board = template(trace)
        board.beats.pop()
        self.assertIn('omitted_transition', verify(board, trace)['errors'])

    def test_unknown_reference(self):
        _, trace = fixture()
        board = template(trace)
        board.beats[0].before = 'invented'
        self.assertIn('unknown_state_reference', verify(board, trace)['errors'])

    def test_literal_rendering_and_no_silent_correction(self):
        _, trace = fixture()
        board = template(trace)
        board.beats[0].before = 'invented'
        board.beats[0].narration = "'); __import__('os'); #"
        code = compile_board(board, trace)
        ast.parse(code)
        self.assertIn('MISSING EVIDENCE', code)

    def test_repair_vs_render_only(self):
        task, trace = fixture()
        good = template(trace)
        bad = good.model_copy(deep=True)
        bad.beats.pop()
        for condition, calls, passes in [('D', 2, True), ('E', 1, False)]:
            with tempfile.TemporaryDirectory() as directory:
                model = FakeModel([bad.model_dump_json(), good.model_dump_json()])
                result = run(task, trace, condition, model, FakeRenderer(), Path(directory) / 'run')
                self.assertEqual(result['n_calls'], calls)
                self.assertEqual(result['automatic_pass'], passes)

    def test_provenance_mismatch_rejected(self):
        task, trace = fixture()
        trace.source_sha256 = 'wrong'
        with self.assertRaises(ValueError):
            run(task, trace, 'T', None, FakeRenderer(), Path('unused'))

    def test_resampling_receives_no_feedback(self):
        task, trace = fixture()
        good = template(trace)
        bad = good.model_copy(deep=True)
        bad.beats.pop()
        model = FakeModel([bad.model_dump_json(), good.model_dump_json()])
        with tempfile.TemporaryDirectory() as directory:
            result = run(task, trace, 'R', model, FakeRenderer(), Path(directory) / 'run')
        self.assertEqual(model.prompts[0], model.prompts[1])
        self.assertTrue(result['automatic_pass'])

    def test_parser_fixture_and_axiom_rejection(self):
        task, _ = fixture()
        source, lines = source_for(task)
        messages = [{'severity': 'information', 'pos': {'line': line}, 'data': data}
                    for line, data in zip(lines, ['goal0', 'goal1', 'no goals'])]
        messages.append({'data': "'benchmark_proof' does not depend on any axioms"})
        output = lambda: '\n'.join(json.dumps(m) for m in messages)
        self.assertEqual(len(parse_trace(output(), source, lines, 'fixture').snapshots), 3)
        messages[-1]['data'] = "'benchmark_proof' depends on axioms: [sorryAx]"
        with self.assertRaises(ValueError): parse_trace(output(), source, lines, 'fixture')

    def test_missing_trace_fails_closed(self):
        with self.assertRaises(ValueError): parse_trace('', 'source', [3], 'fixture')

    def test_budget(self):
        task, trace = fixture()
        with tempfile.TemporaryDirectory() as directory:
            result = run(task, trace, 'D', FakeModel(['{}']), FakeRenderer(), Path(directory) / 'run', 1)
            self.assertFalse(result['final_render'])
            self.assertEqual(result['n_calls'], 1)


if __name__ == '__main__': unittest.main()
