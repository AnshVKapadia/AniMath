import json
import tempfile
import unittest
from pathlib import Path
from research.mathimate_agent.schema import Task
from research.mathimate_agent.agent import run
from research.mathimate_agent.execution import Observation, source_check
from research.mathimate_agent.verification import verify, expression


def task():
    return Task(id='test-1',family_id='f',category='calculus',difficulty='easy',split='dev',
        prompt='Plot x squared.',provenance='unit fixture',requirements=[
        {'id':'graph','kind':'graph_function','description':'Plot x squared','expression':'x**2'},
        {'id':'visual','kind':'manual','description':'Use readable pacing'}])

def observed(expr=lambda x:x*x):
    return Observation(True,'ok',trace={'snapshots':[{'graphs':[{'points':[[x/10,expr(x/10)] for x in range(-10,11)]}]}]})

class FakeLLM:
    calls=0;input_tokens=0;output_tokens=0;cached_tokens=0
    def __init__(self):self.prompts=[]
    def call(self,user,system,action):
        self.calls+=1;self.prompts.append((user,action));return '# deterministic test fixture'

class FakeExecutor:
    def __init__(self,observations):self.observations=iter(observations)
    def render(self,code,directory):return next(self.observations)

class ResearchTests(unittest.TestCase):
    def test_wrong_but_renderable_graph_fails(self):
        self.assertFalse(verify(task(),observed(lambda x:2*x))['automatic_pass'])
        self.assertTrue(verify(task(),observed())['automatic_pass'])
    def test_manual_and_no_trace_are_not_certified(self):
        self.assertFalse(verify(task(),observed())['complete_pass'])
        self.assertFalse(verify(task(),Observation(True,'ok'))['automatic_pass'])
    def test_empty_contract_not_vacuous_pass(self):
        t=task();t.requirements=t.requirements[1:]
        self.assertFalse(verify(t,observed())['automatic_pass'])
    def test_no_host_eval_in_expression_parser(self):
        with self.assertRaises(ValueError):expression('__import__("os").system("id")')
        with self.assertRaises(ValueError):expression('x**1000000')
    def test_hygiene_filter(self):
        with self.assertRaises(ValueError):source_check('import os\nclass GeneratedScene: pass')
    def test_C_stops_at_render_D_repairs_semantics(self):
        for c,count in [('C',1),('D',2)]:
            llm=FakeLLM()
            with tempfile.TemporaryDirectory() as d:
                s=run(task(),c,llm,FakeExecutor([observed(lambda x:2*x),observed()]),d)
            self.assertEqual(s['n_attempts'],count)
            self.assertEqual(s['automatic_pass'],c=='D')
            if c=='C':self.assertNotIn('checks',llm.prompts[0][0])
    def test_repair_budget_and_regression_selection(self):
        llm=FakeLLM()
        with tempfile.TemporaryDirectory() as d:
            s=run(task(),'D',llm,FakeExecutor([observed(lambda x:2*x),Observation(False,'syntax')]),d,max_attempts=2,max_calls=4)
        self.assertEqual(s['n_attempts'],2)
        self.assertEqual(s['selected_attempt'],0)
        self.assertTrue(s['final_render'])
        self.assertFalse(s['automatic_pass'])
    def test_budget_counts_planning(self):
        with tempfile.TemporaryDirectory() as d:
            s=run(task(),'D',FakeLLM(),FakeExecutor([]),d,max_calls=1)
        self.assertEqual(s['n_attempts'],0);self.assertEqual(s['n_calls'],1)
    def test_api_failure_recorded(self):
        class Broken(FakeLLM):
            def call(self,*args):raise ConnectionError('fixture')
        with tempfile.TemporaryDirectory() as d:
            s=run(task(),'A',Broken(),FakeExecutor([]),d)
        self.assertTrue(s['infrastructure_error'])
    def test_benchmark_integrity(self):
        path=Path(__file__).parents[1]/'benchmarks/mathvizbench_draft.jsonl'
        rows=[Task.model_validate_json(s) for s in path.read_text().splitlines()]
        self.assertEqual(len(rows),132);self.assertEqual(len({r.id for r in rows}),132)
        self.assertFalse({r.family_id for r in rows if r.split=='dev'} & {r.family_id for r in rows if r.split=='test'})
        for c in {r.category for r in rows}:
            self.assertEqual(sum(r.category==c and r.split=='test' for r in rows),20)

if __name__=='__main__':unittest.main()
