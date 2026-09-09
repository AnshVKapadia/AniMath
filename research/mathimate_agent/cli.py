from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
import random
import subprocess
import uuid
from importlib.metadata import version
from pathlib import Path
from datetime import datetime, timezone
from research.mathimate_agent.schema import Task
from research.mathimate_agent.agent import run, CONDITIONS
from research.mathimate_agent.execution import DockerExecutor
from research.mathimate_agent.llm import ResearchLLM


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--benchmark',default='research/benchmarks/mathvizbench_draft.jsonl')
    p.add_argument('--split',choices=['dev','test'],default='dev')
    p.add_argument('--conditions',nargs='+',choices=CONDITIONS,default=['A','B','C','D','E','R'])
    p.add_argument('--out',default=None)
    p.add_argument('--limit',type=int,default=None)
    p.add_argument('--replicates',type=int,default=1)
    p.add_argument('--attempts',type=int,default=3)
    p.add_argument('--calls',type=int,default=5)
    p.add_argument('--max-output-tokens',type=int,default=6000)
    p.add_argument('--replan',action='store_true',help='Optional D sensitivity ablation; disabled in the primary comparison')
    p.add_argument('--seed',type=int,default=20260909,help='Task order only; API generation is not seeded')
    p.add_argument('--validate-only',action='store_true')
    p.add_argument('--allow-draft',action='store_true',help='Run unaudited data for pilots only')
    args=p.parse_args()
    raw=Path(args.benchmark).read_bytes()
    tasks=[Task.model_validate_json(x) for x in raw.decode().splitlines() if x.strip()]
    if len({t.id for t in tasks})!=len(tasks): raise ValueError('Duplicate task ids')
    dev={t.family_id for t in tasks if t.split=='dev'}
    test={t.family_id for t in tasks if t.split=='test'}
    if dev & test: raise ValueError('Family leakage across dev/test')
    chosen=[t for t in tasks if t.split==args.split]
    if args.limit is not None:
        if args.limit<1: raise ValueError('Limit must be positive')
        chosen=chosen[:args.limit]
    if not chosen: raise ValueError('No selected tasks')
    if min(args.replicates,args.attempts,args.calls,args.max_output_tokens)<1: raise ValueError('Invalid budget')
    if args.validate_only:
        print(json.dumps({'valid':len(tasks),'selected':len(chosen),'sha256':hashlib.sha256(raw).hexdigest(),
                          'families':len({t.family_id for t in tasks}),'audited':sum(t.status=='audited' for t in tasks)}));return
    if any(t.status!='audited' for t in chosen) and not args.allow_draft:
        raise ValueError('Benchmark is DRAFT. Audit it before publication runs; --allow-draft is for pilots')
    executor=DockerExecutor(); executor.preflight()
    # Verify credentials before creating a run. Reuse configuration, never copy credentials to Docker.
    out=Path(args.out or f'research/runs/{uuid.uuid4().hex}')
    if out.exists(): raise ValueError('Output directory exists; use a new run directory')
    out.mkdir(parents=True)
    ResearchLLM(out/'preflight.jsonl',args.max_output_tokens)
    packages={n:version(n) for n in ['openai','pydantic','sympy','python-dotenv']}
    image=json.loads(subprocess.check_output(['docker','image','inspect',executor.image],text=True))[0]
    source_root=Path(__file__).resolve().parents[2]
    source_hashes={str(f.relative_to(source_root)):hashlib.sha256(f.read_bytes()).hexdigest()
                   for folder in ['research/mathimate_agent','app'] for f in sorted((source_root/folder).glob('*.py'))}
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'args':vars(args),
              'benchmark_sha256':hashlib.sha256(raw).hexdigest(),'source_sha256':source_hashes,
              'python':platform.python_version(),'packages':packages,'image_id':image['Id'],
              'image_digests':image.get('RepoDigests',[]),'model_generation_seed':None,
              'selected_task_ids':[t.id for t in chosen],'schema':'0.1'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    schedule=[(t,c,r) for t in chosen for r in range(args.replicates) for c in args.conditions]
    random.Random(args.seed).shuffle(schedule)
    (out/'schedule.json').write_text(json.dumps([(t.id,c,r) for t,c,r in schedule]))
    for t,c,r in schedule:
        directory=out/f'{t.id}--{c}--r{r}';directory.mkdir()
        llm=ResearchLLM(directory/'llm.jsonl',args.max_output_tokens)
        summary=run(t,c,llm,executor,directory,args.attempts,args.calls,args.replan)
        summary['replicate']=r
        with (out/'results.jsonl').open('a') as f:f.write(json.dumps(summary)+'\n')
        print(json.dumps(summary),flush=True)
        if summary['infrastructure_error']:
            raise RuntimeError('Stopped experiment after infrastructure/API error; preserve ledger and fix before a new run')

if __name__=='__main__':main()
