import json
import tempfile
import unittest
from pathlib import Path
from research.lean_agent.demo import fixture
from research.lean_agent.workbench import new_project, save, export_revision, generate, load_project


class Model:
    def __init__(self, answers):
        self.answers = iter(answers)
        self.prompts = []
    def call(self, prompt, *args):
        self.prompts.append(json.loads(prompt))
        return next(self.answers)


class WorkbenchTests(unittest.TestCase):
    def project(self, root):
        task, _, trace, board = fixture()
        project = new_project(root, task, True)
        save(project / 'trace.json', trace.model_dump())
        return project, board

    def test_revision_preservation_and_feedback(self):
        with tempfile.TemporaryDirectory() as directory:
            project, board = self.project(Path(directory))
            first = export_revision(project, board)
            original = (first / 'storyboard.json').read_bytes()
            model = Model([board.model_dump_json()])
            second = generate(project, 'Explain both goals', model=model)
            self.assertNotEqual(first, second)
            self.assertEqual(original, (first / 'storyboard.json').read_bytes())
            self.assertEqual(model.prompts[0]['user_feedback'], 'Explain both goals')
            self.assertIn('Simulated input', (second / 'index.html').read_text())

    def test_schema_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            project, board = self.project(Path(directory))
            model = Model(['{}', board.model_dump_json()])
            generate(project, model=model)
            self.assertIn('schema_error', model.prompts[1]['repair_feedback'])

    def test_missing_ids_preview_does_not_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            project, board = self.project(Path(directory))
            board.beats[0].before = 'absent'
            revision = export_revision(project, board)
            self.assertIn('MISSING EVIDENCE', (revision / 'index.html').read_text())
            self.assertFalse(json.loads((revision / 'verification.json').read_text())['structural_pass'])

    def test_changed_proof_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            project, board = self.project(Path(directory))
            task = json.loads((project / 'task.json').read_text())
            task['statement'] = 'True'
            save(project / 'task.json', task)
            with self.assertRaises(ValueError): load_project(project)

    def test_unique_project_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            first, _ = self.project(Path(directory))
            second, _ = self.project(Path(directory))
            self.assertNotEqual(first, second)


if __name__ == '__main__': unittest.main()
