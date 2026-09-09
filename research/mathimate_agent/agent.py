from __future__ import annotations
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from time import perf_counter
from research.mathimate_agent.llm import SYSTEM, PLAN
from research.mathimate_agent.verification import verify

# E isolates verification from planning; R controls repeated sampling / test-time compute.
CONDITIONS = {
 'A':dict(plan=False,feedback=False,verify=False,resample=False),
 'B':dict(plan=True,feedback=False,verify=False,resample=False),
 'C':dict(plan=False,feedback=True,verify=False,resample=False),
 'D':dict(plan=True,feedback=True,verify=True,resample=False),
 'E':dict(plan=True,feedback=True,verify=False,resample=False),
 'R':dict(plan=False,feedback=False,verify=False,resample=True),
}

@dataclass
class State:
    task_id: str
    condition: str
    plan: str | None = None
    code: str | None = None
    attempts: list[dict] = field(default_factory=list)
    stop_reason: str = ''
    selected_attempt: int | None = None


def run(task, condition, llm, executor, directory, max_attempts=3, max_calls=5, replan=False):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    spec=CONDITIONS[condition]
    if max_attempts<1 or max_calls<1: raise ValueError('Budgets must be positive')
    state=State(task.id,condition)
    public=json.dumps(task.public_input())
    budget=1 if condition in ('A','B') else max_attempts
    started=perf_counter(); calls_start=llm.calls
    def save(event):
        with (directory/'events.jsonl').open('a') as f: f.write(json.dumps(event)+'\n')
        (directory/'state.json').write_text(json.dumps(asdict(state),indent=2))
    def available(): return llm.calls-calls_start<max_calls
    try:
        if spec['plan'] and available():
            state.plan=llm.call(public,PLAN,'plan')
            save({'action':'plan','plan':state.plan})
        for i in range(budget):
            if not available(): state.stop_reason='call_budget'; break
            prompt=public
            if state.plan: prompt+='\nPlan:\n'+state.plan
            if i and not spec['resample']:
                previous=state.attempts[-1]
                prompt+='\nPrevious code:\n'+state.code+'\nExecution feedback:\n'+json.dumps(previous['feedback'])
                prompt+='\nReturn a complete replacement program. Correct the reported faults while preserving fulfilled requirements.'
            state.code=llm.call(prompt,SYSTEM,'generate' if i==0 or spec['resample'] else 'repair')
            obs=executor.render(state.code,directory/f'attempt-{i:02}')
            assessment=verify(task,obs)
            feedback={'rendered':obs.rendered,'category':obs.category,'details':obs.details}
            if spec['verify']:
                feedback['checks']=[{'id':r['id'],'status':r['status']} for r in assessment['requirements'] if r['kind']!='manual']
            record={'index':i,'observation':asdict(obs),'assessment':assessment,'feedback':feedback}
            state.attempts.append(record)
            if obs.rendered:
                # C/E/R select the first render; D may replace a render with a contract pass.
                if state.selected_attempt is None or (spec['verify'] and assessment['automatic_pass']):
                    state.selected_attempt=i
            save({'action':'observe','attempt':i,**record})
            if obs.infrastructure_error: state.stop_reason='infrastructure_error'; break
            if obs.rendered and (not spec['verify'] or assessment['automatic_pass']):
                state.stop_reason='automatic_contract_pass' if spec['verify'] else 'render_pass'; break
            # One replanning call inside the same total call budget. No new agents.
            semantic_failure=obs.rendered and not assessment['automatic_pass']
            if replan and spec['plan'] and spec['verify'] and semantic_failure and i+1<budget and llm.calls-calls_start+1<max_calls:
                state.plan=llm.call(public+'\nPrevious plan:\n'+str(state.plan)+'\nObserved failed checks:\n'+json.dumps(feedback),PLAN,'replan')
                save({'action':'replan','plan':state.plan})
        if not state.stop_reason: state.stop_reason='attempt_budget'
    except Exception as exc:
        state.stop_reason='harness_or_api_error'
        save({'action':'error','error_type':type(exc).__name__})
        # Resume never silently replaces this run; the error remains in the denominator ledger.
    if state.selected_attempt is None and state.attempts: state.selected_attempt=len(state.attempts)-1
    selected=state.attempts[state.selected_attempt] if state.selected_attempt is not None else None
    summary={'task_id':task.id,'family_id':task.family_id,'category':task.category,
        'difficulty':task.difficulty,'condition':condition,'stop_reason':state.stop_reason,
        'n_attempts':len(state.attempts),'n_calls':llm.calls-calls_start,
        'first_render':bool(state.attempts and state.attempts[0]['observation']['rendered']),
        'final_render':bool(selected and selected['observation']['rendered']),
        'automatic_pass':bool(selected and selected['assessment']['automatic_pass']),
        'complete_pass':bool(selected and selected['assessment']['complete_pass']),
        'selected_attempt':state.selected_attempt,'seconds':perf_counter()-started,
        'input_tokens':llm.input_tokens,'output_tokens':llm.output_tokens,
        'cached_tokens':getattr(llm,'cached_tokens',0),
        'infrastructure_error':state.stop_reason in ('infrastructure_error','harness_or_api_error')}
    (directory/'summary.json').write_text(json.dumps(summary,indent=2))
    save({'action':'terminate',**summary})
    return summary
