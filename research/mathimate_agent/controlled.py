"""Optional comparator that directly reuses the existing plan schema and compiler.

Kept separate from A-D because compiler-generated code is a different output space.
This does not reproduce the production pipeline's free-form fallback policy.
"""
import argparse
import json
from pathlib import Path
from app.scene_compiler import compile_scene
from research.mathimate_agent.llm import ResearchLLM
from research.mathimate_agent.schema import Task
from research.mathimate_agent.execution import DockerExecutor
from research.mathimate_agent.verification import verify

class LoggedPlanner(ResearchLLM):
    def _run(self,user_prompt,system_prompt):
        return self.call(user_prompt,system_prompt,'existing_structured_planner')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--task-id',required=True)
    p.add_argument('--benchmark',default='research/benchmarks/mathvizbench_draft.jsonl')
    p.add_argument('--out',required=True);args=p.parse_args()
    tasks=[Task.model_validate_json(x) for x in Path(args.benchmark).read_text().splitlines()]
    task=next(t for t in tasks if t.id==args.task_id)
    executor=DockerExecutor();executor.preflight()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    llm=LoggedPlanner(out/'llm.jsonl')
    plan=llm.generate_scene_plan(task.prompt,plan_validator=compile_scene)
    (out/'plan.json').write_text(plan.model_dump_json(indent=2))
    compiled=compile_scene(plan)
    obs=executor.render(compiled.code,out/'render')
    result={'comparator':'existing_planner_and_compiler_no_freeform_fallback',
            'task_id':task.id,'calls':llm.calls,'rendered':obs.rendered,'assessment':verify(task,obs)}
    (out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

if __name__=='__main__':main()
