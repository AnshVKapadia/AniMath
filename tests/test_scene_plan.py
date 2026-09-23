from __future__ import annotations

import unittest

from pydantic import ValidationError

from app.scene_plan import ScenePlan


class ScenePlanTests(unittest.TestCase):
    def test_caret_exponents_are_normalized_to_python_powers(self) -> None:
        plan = ScenePlan.model_validate(
            {
                "title": "Riemann sums",
                "visual_kind": "graph",
                "function_expression": "x^2",
                "beats": [
                    {
                        "formula": "f(x)=x^2",
                        "explanation": "Draw the curve.",
                        "action": "show_graph",
                    },
                    {
                        "formula": r"S_n\to\int_0^2 x^2\,dx",
                        "explanation": "Refine the rectangles.",
                        "action": "show_riemann",
                        "interval_start": 0,
                        "interval_end": 2,
                        "dx": 0.5,
                    },
                ],
            }
        )

        self.assertEqual(plan.function_expression, "x**2")

    def test_graph_plan_accepts_controlled_actions(self) -> None:
        plan = ScenePlan.model_validate(
            {
                "title": "Derivative of a parabola",
                "visual_kind": "graph",
                "function_expression": "x**2",
                "x_range": [-3, 3, 1],
                "y_range": [-1, 6, 1],
                "beats": [
                    {
                        "formula": "f(x)=x^2",
                        "explanation": "Begin with the parabola.",
                        "action": "show_graph",
                    },
                    {
                        "formula": "f'(1)=2",
                        "explanation": "The tangent slope at one is two.",
                        "action": "show_tangent",
                        "x_value": 1,
                    },
                ],
            }
        )

        self.assertEqual(plan.function_expression, "x**2")
        self.assertEqual(len(plan.beats), 2)

    def test_graph_plan_allows_algebra_only_formula_beats(self) -> None:
        plan = ScenePlan.model_validate(
            {
                "title": "Derivative algebra beside a graph",
                "visual_kind": "graph",
                "function_expression": "x**2",
                "beats": [
                    {
                        "formula": "f'(x)=\\lim_{h\\to0}\\frac{f(x+h)-f(x)}{h}",
                        "explanation": "Begin with the formal definition.",
                        "action": "show_formula",
                    },
                    {
                        "formula": "f'(x)=\\lim_{h\\to0}(2x+h)",
                        "explanation": "Cancel the common factor of h.",
                        "action": "show_formula",
                    },
                ],
            }
        )

        self.assertEqual(plan.beats[0].action.value, "show_formula")

    def test_secant_requires_two_distinct_points(self) -> None:
        with self.assertRaises(ValidationError):
            ScenePlan.model_validate(
                {
                    "title": "Secant line",
                    "visual_kind": "graph",
                    "function_expression": "x**2",
                    "beats": [
                        {
                            "formula": "m=0",
                            "explanation": "Use two points.",
                            "action": "show_secant",
                            "x_value": 1,
                            "second_x_value": 1,
                        },
                        {
                            "formula": "m=2",
                            "explanation": "Compare their slope.",
                            "action": "show_graph",
                        },
                    ],
                }
            )

    def test_graph_coordinates_must_stay_inside_axis_range(self) -> None:
        payload = {
            "title": "Derivative of a parabola",
            "visual_kind": "graph",
            "function_expression": "x**2",
            "x_range": [-3, 3, 1],
            "y_range": [-1, 6, 1],
            "beats": [
                {
                    "formula": "f(x)=x^2",
                    "explanation": "Begin with the parabola.",
                    "action": "show_graph",
                },
                {
                    "formula": "f'(1)=2",
                    "explanation": "The tangent slope at one is two.",
                    "action": "show_tangent",
                    "x_value": 10,
                },
            ],
        }

        with self.assertRaisesRegex(ValueError, "x_value must be inside x_range"):
            ScenePlan.model_validate(payload)

    def test_equation_plan_rejects_graph_actions(self) -> None:
        with self.assertRaises(ValidationError):
            ScenePlan.model_validate(
                {
                    "title": "Limit laws",
                    "visual_kind": "equation",
                    "beats": [
                        {
                            "formula": "\\lim_{x\\to 0}x=0",
                            "explanation": "Start with the identity limit.",
                            "action": "show_graph",
                        },
                        {
                            "formula": "0+0=0",
                            "explanation": "Combine the limits.",
                            "action": "show_formula",
                        },
                    ],
                }
            )

    def test_unknown_plan_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ScenePlan.model_validate(
                {
                    "title": "A short equation proof",
                    "visual_kind": "equation",
                    "function_expression": None,
                    "unexpected_layout": "top-left",
                    "beats": [
                        {
                            "formula": "a=b",
                            "explanation": "Begin with the first equation.",
                            "action": "show_formula",
                        },
                        {
                            "formula": "b=c",
                            "explanation": "Transform it into the second equation.",
                            "action": "show_formula",
                        },
                    ],
                }
            )

    def test_second_point_label_requires_a_secant(self) -> None:
        with self.assertRaisesRegex(ValueError, "second_point_label"):
            ScenePlan.model_validate(
                {
                    "title": "A labeled tangent point",
                    "visual_kind": "graph",
                    "function_expression": "x**2",
                    "beats": [
                        {
                            "formula": "f(x)=x^2",
                            "explanation": "Begin with the graph.",
                            "action": "show_graph",
                        },
                        {
                            "formula": "f'(1)=2",
                            "explanation": "Draw the tangent at one.",
                            "action": "show_tangent",
                            "x_value": 1,
                            "second_point_label": "(x+h,f(x+h))",
                        },
                    ],
                }
            )

    def test_sliding_secant_target_must_approach_fixed_point(self) -> None:
        with self.assertRaisesRegex(ValueError, "target must move toward"):
            ScenePlan.model_validate(
                {
                    "title": "A moving secant line",
                    "visual_kind": "graph",
                    "function_expression": "x**2",
                    "x_range": [-3, 4, 1],
                    "beats": [
                        {
                            "formula": "f(x)=x^2",
                            "explanation": "Begin with the graph.",
                            "action": "show_graph",
                        },
                        {
                            "formula": "m=\\frac{f(x+h)-f(x)}{h}",
                            "explanation": "Move the second secant point toward the first.",
                            "action": "slide_secant",
                            "x_value": 1,
                            "second_x_value": 2,
                            "target_x_value": 3,
                        },
                    ],
                }
            )


if __name__ == "__main__":
    unittest.main()
