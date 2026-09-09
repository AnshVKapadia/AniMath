from __future__ import annotations
import json
from pathlib import Path
from time import perf_counter
from app.llm import LLMClient

SYSTEM = '''Generate executable mathematical visualization programs using Manim Community 0.19.0.
Return only Python source defining GeneratedScene(Scene), with from manim import *.
Use ordinary Axes.plot, Dot, Line, Text or MathTex objects and simple animations.
Keep the scene 8-20 seconds at low quality. No files, network, subprocesses, custom LaTeX,
imports beyond manim/numpy/math, introspection, or changes to Manim internals.
Fulfil every public requirement. Use Text for explicitly requested ASCII labels.
An external runner observes objects during execution; do not emit verification claims.'''
PLAN = '''Plan a short mathematical visualization. Return a JSON object with a scenes list
of 2-5 ordered steps, each containing goal, objects, mathematical_facts, and action.
Cover every requirement. Do not write Python. This is a plan, not a correctness verdict.'''

class ResearchLLM(LLMClient):
    """Reuse the application's provider configuration, with explicit call accounting."""
    def __init__(self, log_path: Path, max_output_tokens=6000):
        super().__init__()
        self._client = self._client.with_options(max_retries=0, timeout=120.0)
        self.log_path = log_path
        self.max_output_tokens = max_output_tokens
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_tokens = 0

    def call(self, user: str, system: str, action: str) -> str:
        started = perf_counter()
        self.calls += 1
        event = {'action':action,'call':self.calls,'model':self._model,
                 'system_prompt':system,'user_prompt':user,
                 'max_output_tokens':self.max_output_tokens}
        try:
            response = self._client.responses.create(model=self._model,
                max_output_tokens=self.max_output_tokens,
                input=[{'role':'system','content':system},{'role':'user','content':user}])
            usage = response.usage.model_dump() if response.usage else {}
            self.input_tokens += usage.get('input_tokens',0)
            self.output_tokens += usage.get('output_tokens',0)
            self.cached_tokens += (usage.get('input_tokens_details') or {}).get('cached_tokens',0)
            event.update(response_id=response.id, response_model=response.model,
                         usage=usage, output=response.output_text)
            if not response.output_text.strip():
                raise ValueError('Empty model response')
            return response.output_text.strip()
        except Exception as exc:
            # Do not serialize transport exceptions that might contain provider URLs or headers.
            event['error_type'] = type(exc).__name__
            raise
        finally:
            event['seconds'] = perf_counter()-started
            with self.log_path.open('a',encoding='utf-8') as f:
                f.write(json.dumps(event)+'\n')
