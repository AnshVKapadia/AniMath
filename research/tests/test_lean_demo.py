import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research.lean_agent.demo import main


class DemoTests(unittest.TestCase):
    def test_offline_demo_outputs_are_honestly_labeled(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'demo'
            with patch('sys.argv', ['demo', '--out', str(out)]):
                main()
            self.assertEqual({p.name for p in out.iterdir()}, {
                'proof.lean', 'simulated-trace.json', 'storyboard.json',
                'GeneratedScene.py', 'verification.json', 'index.html'})
            page = (out / 'index.html').read_text(encoding='utf-8')
            self.assertIn('Simulated input', page)
            self.assertIn('not formally verified', page)
            self.assertIn('Conceptual animation', page)
            self.assertIn("f.kind==='split_goal'", page)


if __name__ == '__main__':
    unittest.main()
