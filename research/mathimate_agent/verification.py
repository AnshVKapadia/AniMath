from __future__ import annotations
import ast
import math
import sympy as sp
from app.scene_compiler import _compile_expression


def expression(value):
    """Convert the existing compiler's approved AST to SymPy without eval/sympify strings."""
    if len(value)>80: raise ValueError('Expression too long')
    _compile_expression(value)
    functions={'sin':sp.sin,'cos':sp.cos,'tan':sp.tan,'exp':sp.exp,'log':sp.log,
               'sqrt':sp.sqrt,'abs':sp.Abs}
    def walk(n):
        if isinstance(n,ast.Constant) and type(n.value) in (int,float):
            if abs(n.value)>10000: raise ValueError('Numeric constant too large')
            return sp.Rational(str(n.value))
        if isinstance(n,ast.Name): return {'x':sp.Symbol('x'),'pi':sp.pi,'e':sp.E}[n.id]
        if isinstance(n,ast.UnaryOp): return -walk(n.operand) if isinstance(n.op,ast.USub) else walk(n.operand)
        if isinstance(n,ast.BinOp):
            a,b=walk(n.left),walk(n.right)
            if isinstance(n.op,ast.Pow) and (not b.is_number or abs(b)>12): raise ValueError('Unsupported exponent')
            return {ast.Add:lambda:a+b,ast.Sub:lambda:a-b,ast.Mult:lambda:a*b,
                    ast.Div:lambda:a/b,ast.Pow:lambda:a**b}[type(n.op)]()
        if isinstance(n,ast.Call): return functions[n.func.id](walk(n.args[0]))
        raise ValueError('Unsupported expression')
    return walk(ast.parse(value,mode='eval').body)


def verify(task, observation):
    snapshots=(observation.trace or {}).get('snapshots',[])
    result=[]
    for req in task.requirements:
        status='unknown'; evidence='No supported runtime evidence'
        if req.kind=='manual':
            evidence='Requires blind video review; never automatically treated as passed'
        elif observation.rendered and snapshots:
            ok=False
            if req.kind=='text':
                # Displayed text presence only, never a mathematical correctness proof.
                ok=any(req.value in text for s in snapshots for text in s.get('texts',[]))
            elif req.kind=='point':
                ok=any(math.hypot(p['xy'][0]-req.x,p['xy'][1]-req.y)<=req.tolerance
                       for s in snapshots for p in s.get('points',[]))
            elif req.kind=='line_slope':
                for s in snapshots:
                    for line in s.get('lines',[]):
                        x1,y1=line['start'][:2]; x2,y2=line['end'][:2]
                        if abs(x2-x1)>1e-6:
                            slope=(y2-y1)/(x2-x1)
                            ok |= (abs(slope-req.slope)<=req.tolerance and
                                   abs(y1+slope*(req.x-x1)-req.y)<=req.tolerance)
            elif req.kind=='graph_function':
                expected=expression(req.expression); x=sp.Symbol('x')
                for s in snapshots:
                    for graph in s.get('graphs',[]):
                        points=graph['points']
                        if len(points)<10 or max(p[0] for p in points)-min(p[0] for p in points)<0.5: continue
                        try:
                            ok |= all(abs(float(expected.subs(x,p[0]))-p[1])<=req.tolerance for p in points)
                        except (ValueError,TypeError,OverflowError): pass
            elif req.kind=='moving_point':
                positions={}
                for s in snapshots:
                    for p in s.get('points',[]):
                        key=(p['id'],p['axes']); xy=p['xy'][:2]
                        if key in positions and math.dist(positions[key],xy)>req.tolerance: ok=True
                        positions[key]=xy
            status='pass' if ok else 'fail'
            evidence='Finite runtime observation; absence can be an unsupported representation'
        result.append({'id':req.id,'kind':req.kind,'essential':req.essential,
                       'status':status,'evidence':evidence})
    automatic=[r for r in result if r['kind']!='manual' and r['essential']]
    essential=[r for r in result if r['essential']]
    return {'requirements':result,
        'automatic_pass':bool(automatic) and observation.rendered and all(r['status']=='pass' for r in automatic),
        'complete_pass':bool(essential) and observation.rendered and all(r['status']=='pass' for r in essential),
        'automatic_coverage':len(automatic)/len(essential) if essential else 0,
        'label':'runtime_contract_proxy_not_full_correctness'}
