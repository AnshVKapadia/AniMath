from __future__ import annotations

import unittest
from unittest.mock import Mock

from app.llm import LLMClient, _validate_teaching_depth
from app.scene_plan import ScenePlan


def shallow_formal_plan() -> ScenePlan:
    beats = [
        {
            "formula": f"s_{index}=s_{index + 1}",
            "explanation": "Apply one algebraic operation.",
            "action": "show_formula",
        }
        for index in range(7)
    ]
    return ScenePlan.model_validate(
        {
            "title": "A formal derivative derivation",
            "visual_kind": "graph",
            "function_expression": "x**2",
            "beats": beats,
        }
    )


class TeachingDepthTests(unittest.TestCase):
    def test_formal_definition_requires_eight_beats(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly 8 beats"):
            _validate_teaching_depth(
                "Show why this works using the formal definition of a derivative.",
                shallow_formal_plan(),
            )

    def test_secant_to_tangent_requires_visible_motion(self) -> None:
        with self.assertRaisesRegex(ValueError, "slide_secant"):
            _validate_teaching_depth(
                "Show a secant becoming a tangent.",
                shallow_formal_plan(),
            )

    def test_shallow_plan_gets_one_structured_revision(self) -> None:
        shallow = shallow_formal_plan()
        complete_payload = shallow.model_dump(mode="json")
        complete_payload["beats"].append(
            {
                "formula": "f'(x)=2x",
                "explanation": "State the completed derivative.",
                "action": "show_formula",
                "x_value": None,
                "second_x_value": None,
                "target_x_value": None,
                "interval_start": None,
                "interval_end": None,
                "dx": None,
                "point_label": None,
                "second_point_label": None,
            }
        )
        complete = ScenePlan.model_validate(complete_payload)
        client = LLMClient.__new__(LLMClient)
        client._run = Mock(
            side_effect=[shallow.model_dump_json(), complete.model_dump_json()]
        )

        plan = client.generate_scene_plan(
            "Explain this using the formal definition of a derivative."
        )

        self.assertEqual(len(plan.beats), 8)
        self.assertEqual(client._run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
