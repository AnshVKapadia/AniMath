from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import app.rendering as rendering
from app.scene_plan import ScenePlan


def controlled_plan() -> ScenePlan:
    return ScenePlan.model_validate(
        {
            "title": "Area under a curve",
            "visual_kind": "graph",
            "function_expression": "x**2",
            "x_range": [0, 3, 1],
            "y_range": [0, 9, 1],
            "beats": [
                {
                    "formula": "f(x)=x^2",
                    "explanation": "Draw the function first.",
                    "action": "show_graph",
                },
                {
                    "formula": "\\int_0^2 x^2\\,dx",
                    "explanation": "Shade the accumulated area.",
                    "action": "show_area",
                    "interval_start": 0,
                    "interval_end": 2,
                },
            ],
        }
    )


FREEFORM_CODE = "from manim import *\n\nclass GeneratedScene(Scene):\n    def construct(self):\n        self.add(Dot())\n"


class ControlledPipelineTests(unittest.TestCase):
    def test_controlled_plan_is_saved_and_rendered(self) -> None:
        root = Path("virtual-renders")
        video = root / "video" / "GeneratedScene.mp4"
        llm = Mock()
        llm.generate_scene_plan.return_value = controlled_plan()

        with (
            patch.object(rendering, "RENDERS_DIR", root),
            patch.object(rendering, "LLMClient", return_value=llm),
            patch.object(rendering, "_render_scene", return_value=(True, "", video)),
            patch.object(Path, "mkdir"),
            patch.object(Path, "write_text") as write_text,
        ):
            result = rendering.run_generation_pipeline("controlled-job", "Show an integral")

        self.assertEqual(result.video_path, video)
        self.assertIn("validate_layout", result.code)
        self.assertGreaterEqual(write_text.call_count, 2)
        llm.generate_code.assert_not_called()

    def test_invalid_plan_falls_back_before_rendering(self) -> None:
        root = Path("virtual-renders")
        video = root / "video" / "GeneratedScene.mp4"
        llm = Mock()
        llm.generate_scene_plan.side_effect = ValueError("bad plan")
        llm.generate_code.return_value = FREEFORM_CODE

        with (
            patch.object(rendering, "RENDERS_DIR", root),
            patch.object(rendering, "LLMClient", return_value=llm),
            patch.object(rendering, "_render_scene", return_value=(True, "", video)),
            patch.object(Path, "mkdir"),
            patch.object(Path, "write_text"),
        ):
            result = rendering.run_generation_pipeline("fallback-job", "Show a series")

        self.assertEqual(result.video_path, video)
        self.assertEqual(result.code, FREEFORM_CODE)
        llm.generate_code.assert_called_once()

    def test_failed_controlled_render_uses_freeform_fallback(self) -> None:
        root = Path("virtual-renders")
        video = root / "video" / "GeneratedScene.mp4"
        llm = Mock()
        llm.generate_scene_plan.return_value = controlled_plan()
        llm.generate_code.return_value = FREEFORM_CODE

        with (
            patch.object(rendering, "RENDERS_DIR", root),
            patch.object(rendering, "LLMClient", return_value=llm),
            patch.object(
                rendering,
                "_render_scene",
                side_effect=[(False, "layout failure", None), (True, "", video)],
            ),
            patch.object(Path, "mkdir"),
            patch.object(Path, "write_text"),
        ):
            result = rendering.run_generation_pipeline("retry-job", "Show an integral")

        self.assertTrue(result.repaired)
        self.assertEqual(result.code, FREEFORM_CODE)
        llm.generate_code.assert_called_once()


if __name__ == "__main__":
    unittest.main()
