from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Requirement(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^[a-z0-9_]+$')
    description: str
    kind: Literal['graph_function', 'point', 'line_slope', 'text', 'moving_point', 'manual']
    expression: str | None = None
    value: str | None = None
    x: float | None = None
    y: float | None = None
    slope: float | None = None
    tolerance: float = Field(default=0.03, gt=0, le=0.2)
    essential: bool = True

    @model_validator(mode='after')
    def fields_for_kind(self):
        needed = {'graph_function':['expression'], 'point':['x','y'],
                  'line_slope':['x','y','slope'], 'text':['value']}.get(self.kind, [])
        if any(getattr(self, key) is None for key in needed):
            raise ValueError(f'{self.kind} requires {needed}')
        return self

class Task(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^[a-z0-9_-]+$')
    family_id: str
    category: Literal['algebra','functions','calculus','geometry','linear_algebra','probability_statistics']
    difficulty: Literal['easy','medium','hard']
    split: Literal['dev','test']
    prompt: str
    requirements: list[Requirement] = Field(min_length=1)
    provenance: str
    status: Literal['draft','audited'] = 'draft'
    schema_version: str = '0.1'

    @model_validator(mode='after')
    def unique_requirements(self):
        ids = [r.id for r in self.requirements]
        if len(set(ids)) != len(ids):
            raise ValueError('duplicate requirement id')
        return self

    def public_input(self):
        # Never expose expected numeric values or grader internals separately.
        return {'id': self.id, 'prompt': self.prompt,
                'requirements': [{'id':r.id,'description':r.description} for r in self.requirements]}
