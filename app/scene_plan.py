from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VisualKind(StrEnum):
    GRAPH = "graph"
    EQUATION = "equation"


class VisualAction(StrEnum):
    SHOW_GRAPH = "show_graph"
    SHOW_POINT = "show_point"
    SHOW_SECANT = "show_secant"
    SLIDE_SECANT = "slide_secant"
    SHOW_TANGENT = "show_tangent"
    SHOW_AREA = "show_area"
    SHOW_RIEMANN = "show_riemann"
    SHOW_FORMULA = "show_formula"


class SceneBeat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formula: str = Field(min_length=1, max_length=120)
    explanation: str = Field(min_length=1, max_length=150)
    action: VisualAction
    x_value: float | None = None
    second_x_value: float | None = None
    target_x_value: float | None = None
    interval_start: float | None = None
    interval_end: float | None = None
    dx: float | None = Field(default=None, gt=0)
    point_label: str | None = Field(default=None, min_length=1, max_length=56)
    second_point_label: str | None = Field(default=None, min_length=1, max_length=56)

    @model_validator(mode="after")
    def validate_action_parameters(self) -> "SceneBeat":
        point_actions = {
            VisualAction.SHOW_POINT,
            VisualAction.SHOW_SECANT,
            VisualAction.SLIDE_SECANT,
            VisualAction.SHOW_TANGENT,
        }
        if self.point_label is not None and self.action not in point_actions:
            raise ValueError(f"{self.action.value} cannot use point_label")
        secant_actions = {VisualAction.SHOW_SECANT, VisualAction.SLIDE_SECANT}
        if self.second_point_label is not None and self.action not in secant_actions:
            raise ValueError("second_point_label can only be used with a secant action")

        if self.action in {VisualAction.SHOW_POINT, VisualAction.SHOW_TANGENT}:
            if self.x_value is None:
                raise ValueError(f"{self.action.value} requires x_value")
        elif self.action in secant_actions:
            if self.x_value is None or self.second_x_value is None:
                raise ValueError(f"{self.action.value} requires x_value and second_x_value")
            if self.x_value == self.second_x_value:
                raise ValueError("secant points must have different x values")
            if self.action == VisualAction.SLIDE_SECANT:
                if self.target_x_value is None:
                    raise ValueError("slide_secant requires target_x_value")
                if self.target_x_value == self.x_value:
                    raise ValueError("target_x_value cannot equal the fixed secant point")
                if abs(self.target_x_value - self.x_value) >= abs(
                    self.second_x_value - self.x_value
                ):
                    raise ValueError("slide_secant target must move toward the fixed point")
        elif self.action in {VisualAction.SHOW_AREA, VisualAction.SHOW_RIEMANN}:
            if self.interval_start is None or self.interval_end is None:
                raise ValueError(f"{self.action.value} requires an interval")
            if self.interval_start >= self.interval_end:
                raise ValueError("interval_start must be less than interval_end")
            if self.action == VisualAction.SHOW_RIEMANN and self.dx is None:
                raise ValueError("show_riemann requires dx")
        return self


class ScenePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=72)
    visual_kind: VisualKind
    function_expression: str | None = Field(default=None, max_length=80)
    x_range: tuple[float, float, float] = (-3.0, 3.0, 1.0)
    y_range: tuple[float, float, float] = (-2.0, 6.0, 1.0)
    beats: list[SceneBeat] = Field(min_length=2, max_length=8)

    @field_validator("function_expression", mode="before")
    @classmethod
    def normalize_function_expression(cls, value: object) -> object:
        if isinstance(value, str):
            return value.replace("^", "**")
        return value

    @model_validator(mode="after")
    def validate_scene(self) -> "ScenePlan":
        self._validate_axis_range("x_range", self.x_range)
        self._validate_axis_range("y_range", self.y_range)

        graph_actions = {
            VisualAction.SHOW_GRAPH,
            VisualAction.SHOW_POINT,
            VisualAction.SHOW_SECANT,
            VisualAction.SLIDE_SECANT,
            VisualAction.SHOW_TANGENT,
            VisualAction.SHOW_AREA,
            VisualAction.SHOW_RIEMANN,
        }
        if self.visual_kind == VisualKind.GRAPH:
            if not self.function_expression:
                raise ValueError("graph plans require function_expression")
            self._validate_graph_coordinates()
        else:
            if self.function_expression is not None:
                raise ValueError("equation plans require a null function_expression")
            if any(beat.action in graph_actions for beat in self.beats):
                raise ValueError("equation plans can only use show_formula")
        return self

    def _validate_graph_coordinates(self) -> None:
        minimum, maximum, _ = self.x_range
        for beat in self.beats:
            values = {
                "x_value": beat.x_value,
                "second_x_value": beat.second_x_value,
                "target_x_value": beat.target_x_value,
                "interval_start": beat.interval_start,
                "interval_end": beat.interval_end,
            }
            for name, value in values.items():
                if value is not None and not minimum <= value <= maximum:
                    raise ValueError(f"{name} must be inside x_range")

    @staticmethod
    def _validate_axis_range(name: str, values: tuple[float, float, float]) -> None:
        minimum, maximum, step = values
        if minimum >= maximum:
            raise ValueError(f"{name} minimum must be less than maximum")
        if step <= 0 or step > maximum - minimum:
            raise ValueError(f"{name} step must be positive and fit inside the range")
