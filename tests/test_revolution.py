import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import app.rendering as rendering
from pydantic import ValidationError
from app.revolution import RevolutionPlan, compile_revolution, requests_revolution, plan_revolution


class RevolutionTests(unittest.TestCase):
    def plan(self):
        return RevolutionPlan(supported=True, outer_radius="sqrt(x)", inner_radius="x", axis="x", interval=(0,1))

    def test_pipeline_uses_3d_without_freeform_fallback(self):
        llm = Mock()
        llm._run.return_value = self.plan().model_dump_json()
        video = Path("example.mp4")
        with (patch.object(rendering, "LLMClient", return_value=llm),
              patch.object(Path, "mkdir"), patch.object(Path, "write_text"),
              patch.object(rendering, "_render_scene", return_value=(True, "", video))):
            result = rendering.run_generation_pipeline("3d-test", "Show the washer method")
        self.assertEqual(result.video_path, video)
        self.assertIn("ThreeDScene", result.code)
        llm.generate_scene_plan.assert_not_called()
        llm.generate_code.assert_not_called()

    def test_render_failure_does_not_substitute_2d(self):
        llm = Mock()
        llm._run.return_value = self.plan().model_dump_json()
        with (patch.object(rendering, "LLMClient", return_value=llm),
              patch.object(Path, "mkdir"), patch.object(Path, "write_text"),
              patch.object(rendering, "_render_scene", return_value=(False, "timeout", None)),
              self.assertRaises(rendering.RenderPipelineError)):
            rendering.run_generation_pipeline("3d-failure", "Show the washer method")
        llm.generate_code.assert_not_called()
        llm.repair_code.assert_not_called()

    def test_real_3d_and_disk_variant(self):
        p=self.plan()
        code=compile_revolution(p)
        compile(code,"scene","exec")
        self.assertIn("GeneratedScene(ThreeDScene)",code)
        self.assertIn("INNER_IS_ZERO = False",code)
        self.assertIn("validate_fixed_layout", code)
        self.assertIn("OUTER_TEX", code)
        self.assertIn(r"\sqrt{x}", code)
        self.assertNotIn('Text("Outer radius: sqrt(x)', code)
        p.inner_radius="0"
        self.assertIn("INNER_IS_ZERO = True",compile_revolution(p))

    def test_wrong_axis_rejected(self):
        data=self.plan().model_dump()
        data["axis"]="y"
        with self.assertRaises(ValidationError):
            RevolutionPlan(**data)

    def test_general_radius_functions_and_bounds_compile(self):
        plan = RevolutionPlan(
            supported=True,
            outer_radius="1 + x/2",
            inner_radius="x/4",
            axis="x",
            interval=(0, 2),
        )

        code = compile_revolution(plan)

        self.assertIn("OUTER_EXPRESSION = '1 + x / 2'", code)
        self.assertIn("INNER_EXPRESSION = 'x / 4'", code)
        self.assertIn("X_END = 2.0", code)
        self.assertIn(r"R(x)=", code)
        compile(code, "scene", "exec")

    def test_crossing_or_unsafe_radii_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "outer radius"):
            RevolutionPlan(
                supported=True,
                outer_radius="x",
                inner_radius="1",
                axis="x",
                interval=(0, 1),
            )
        with self.assertRaisesRegex(ValueError, "unsupported radius expression"):
            RevolutionPlan(
                supported=True,
                outer_radius="__import__('os').system('nope')",
                inner_radius="0",
                axis="x",
                interval=(0, 1),
            )

    def test_unsupported_never_substitutes_example(self):
        p=self.plan()
        p.supported=False
        with self.assertRaises(ValueError):
            compile_revolution(p)

    def test_routes_and_extracts(self):
        self.assertTrue(requests_revolution("Animate the disk and washer method in 3D"))
        self.assertFalse(requests_revolution("Show a derivative"))
        llm=Mock()
        llm._run.return_value=self.plan().model_dump_json()
        self.assertEqual(plan_revolution(llm,"washers"),self.plan())
