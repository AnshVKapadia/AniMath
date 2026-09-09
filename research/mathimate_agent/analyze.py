"""Paired task/family bootstrap; no independence assumption for template variants."""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean


def main():
    p=argparse.ArgumentParser();p.add_argument('results');p.add_argument('--draws',type=int,default=5000)
    p.add_argument('--seed',type=int,default=20260909);args=p.parse_args()
    rows=[json.loads(x) for x in Path(args.results).read_text().splitlines() if x.strip()]
    if not rows: raise ValueError('No results')
    if args.draws<100: raise ValueError('Use at least 100 bootstrap draws')
    schedule=Path(args.results).parent/'schedule.json'
    if schedule.exists():
        expected={tuple(x) for x in json.loads(schedule.read_text())}
        actual={(r['task_id'],r['condition'],r['replicate']) for r in rows}
        if expected!=actual: raise ValueError('Results do not match the complete randomized schedule')
    if any(r['infrastructure_error'] for r in rows):
        raise ValueError('Incomplete run contains infrastructure errors; resolve and document before inferential analysis')
    keys=[(r['task_id'],r['condition'],r['replicate']) for r in rows]
    if len(set(keys))!=len(keys):raise ValueError('Duplicate results')
    conditions=sorted({r['condition'] for r in rows})
    pairs={(r['task_id'],r['replicate']) for r in rows}
    if any({(r['task_id'],r['replicate']) for r in rows if r['condition']==c}!=pairs for c in conditions):
        raise ValueError('Missing paired cells; no silent complete-case deletion')
    print('condition,n,first_render,final_render,automatic_contract_proxy,mean_attempts,mean_seconds,input_tokens,output_tokens')
    for c in conditions:
        a=[r for r in rows if r['condition']==c]
        print(','.join(map(str,[c,len(a),*[round(mean(r[k] for r in a),4) for k in
            ['first_render','final_render','automatic_pass','n_attempts','seconds']],
            sum(r['input_tokens'] for r in a),sum(r['output_tokens'] for r in a)])))
    for baseline in ('C','E','R'):
        if not {'D',baseline}<=set(conditions):continue
        for metric in ('final_render','automatic_pass'):
            lookup={(r['task_id'],r['replicate'],r['condition']):r for r in rows}
            clusters=defaultdict(list)
            for t,rep in sorted(pairs):
                d=lookup[t,rep,'D'];b=lookup[t,rep,baseline]
                clusters[d['family_id']].append(int(d[metric])-int(b[metric]))
            families=sorted(clusters);rng=random.Random(args.seed);boots=[]
            for _ in range(args.draws):
                sample=[v for f in rng.choices(families,k=len(families)) for v in clusters[f]]
                boots.append(mean(sample))
            boots.sort();estimate=mean(v for values in clusters.values() for v in values)
            print(json.dumps({'comparison':f'D-{baseline}','metric':metric,'paired_difference':estimate,
                'ci95_family_bootstrap':[boots[int(.025*len(boots))],boots[min(len(boots)-1,int(.975*len(boots)))]] ,
                'families':len(families),'unit':'proportion','exploratory':baseline!='E'}))

if __name__=='__main__':main()
