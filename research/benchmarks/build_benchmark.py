"""Deterministic draft: 24 held-out families x 5 variants + 12 disjoint dev tasks.

Author-created with AI assistance. This is a seed suite, not a validated benchmark.
No model output, evaluation result, or hidden test feedback is used to build it.
"""
import json
from pathlib import Path
from research.mathimate_agent.schema import Task

ROOT=Path(__file__).parent
rows=[]

def req(kind,description,**kwargs):return dict(kind=kind,description=description,**kwargs)
def graph(expr):return req('graph_function',f'Plot y={expr} on labeled coordinate axes.',expression=expr)
def label(text):return req('text',f'Display the exact ASCII label "{text}" using Text.',value=text)
def point(x,y):return req('point',f'Show a dot at ({x},{y}) on the coordinate axes.',x=x,y=y)
def manual(text):return req('manual',text)
def add(cat,family,k,prompt,checks,difficulty='medium',split='test'):
    checks=[dict(id=f'r{i+1}',**c) for i,c in enumerate(checks)]
    task=Task(id=f'{family}-{k}',family_id=family,category=cat,difficulty=difficulty,split=split,
        prompt=prompt+' Use coordinate axes for geometric positions. '+ ' '.join(c['description'] for c in checks),
        requirements=checks,provenance='Original deterministic templates, authored with AI assistance on 2026-09-09; no external prompt copying; unaudited')
    rows.append(task)

for k in range(1,6):
    a=k+1
    add('algebra','linear_root',k,f'Animate solving {a}x-{2*a}=0 and connect the solution to the x-intercept.',
        [graph(f'{a}*x-{2*a}'),point(2,0),label('x = 2'),manual('Show at least two valid equation transformations.')],'easy')
    add('algebra','quadratic_factor',k,f'Animate factoring x^2-{2*a}x+{a*a}=0.',
        [graph(f'(x-{a})**2'),point(a,0),label(f'root = {a}'),manual('Show the repeated factor and distinguish one distinct root from multiplicity two.')])
    add('algebra','complete_square',k,f'Complete the square for x^2+{2*a}x+{a*a+1} and connect it to the vertex.',
        [graph(f'(x+{a})**2+1'),point(-a,1),label('minimum = 1'),manual('Animate the algebraic completion of the square without omitting the compensation term.')])
    add('algebra','system_intersection',k,f'Animate solving y={a}x+1 and y=-x+{a+2} as a system.',
        [graph(f'{a}*x+1'),graph(f'-x+{a+2}'),point(1,a+1),label(f'intersection = (1, {a+1})'),manual('Show valid elimination or substitution steps and both lines together.')],'hard')
    add('functions','vertical_translation',k,f'Animate shifting y=x^2 upward by {a}.',
        [graph('x**2'),graph(f'x**2+{a}'),point(0,a),manual('Show an actual continuous upward translation and preserve the parabola shape.')],'easy')
    add('functions','horizontal_translation',k,f'Animate shifting y=x^2 rightward by {a}.',
        [graph('x**2'),graph(f'(x-{a})**2'),point(a,0),manual('Show continuous horizontal motion in the correct direction.')])
    add('functions','inverse_line',k,f'Visualize the inverse of f(x)={a}x+1 through reflection about y=x.',
        [graph(f'{a}*x+1'),graph(f'(x-1)/{a}'),graph('x'),manual('Reflect corresponding points and correctly label the inverse function.')])
    add('functions','piecewise_continuity',k,f'Visualize the piecewise function equal to x+{a} for x<0 and x^2+{a} for x>=0 near zero.',
        [point(0,a),label(f'limit = {a}'),manual('Use the correct formula on each half-axis, correct open/closed endpoints, and demonstrate matching one-sided limits.')],'hard')
    add('calculus','tangent_polynomial',k,f'Animate the derivative of f(x)=x^2 at x={k}, including a secant approaching the tangent.',
        [graph('x**2'),point(k,k*k),req('moving_point','Move the second secant point visibly toward the fixed point.'),
         req('line_slope',f'Show the tangent through ({k},{k*k}) with slope {2*k}.',x=k,y=k*k,slope=2*k),
         label(f'slope = {2*k}'),manual('Keep the first point fixed; reduce the second-point separation; distinguish secant and final tangent.')],'easy')
    add('calculus','integral_linear',k,f'Animate the definite integral of f(x)={a}x on [0,2] using shaded area.',
        [graph(f'{a}*x'),label(f'area = {2*a}'),manual('Shade only the region bounded by the curve, x-axis, x=0 and x=2; explain area accumulation.')])
    add('calculus','riemann_quadratic',k,f'Animate left Riemann sums for x^2 on [0,{k}], refining from 4 to 8 to 16 rectangles.',
        [graph('x**2'),label(f'exact area = {k**3}/3'),manual('Use left endpoints at each partition, show all three refinements, and distinguish sum approximation from exact integral.')])
    add('calculus','taylor_exponential',k,f'Compare exp(x) near zero with its degree-{k+1} Taylor polynomial using sequential term additions.',
        [graph('exp(x)'),manual(f'Display the correct degree-{k+1} polynomial with factorial denominators and show convergence near zero, without claiming global accuracy.')],'hard')
    add('geometry','right_triangle',k,f'Animate a right triangle with legs {3*k} and {4*k} and its hypotenuse square.',
        [label(f'hypotenuse = {5*k}'),manual('Draw perpendicular legs with correct proportions and show the Pythagorean area relation.')],'easy')
    add('geometry','circle_area',k,f'Visualize why a circle of radius {k} has area pi*r^2 by rearranging equal sectors.',
        [label(f'area = {k*k} pi'),manual('Rearrange actual sectors with matched area, identify approximate base pi*r and height r, and acknowledge the limiting approximation.')])
    add('geometry','rotation_point',k,f'Rotate ({k},0) by 90 degrees counterclockwise about the origin.',
        [point(k,0),point(0,k),req('moving_point','Animate the point along its rotation arc.'),manual('Preserve the radius throughout the quarter-circle motion and mark the angle.')])
    add('geometry','similar_triangles',k,f'Animate scaling a 3-4-5 triangle by factor {a} and compare length and area scaling.',
        [label(f'length factor = {a}'),label(f'area factor = {a*a}'),manual('Show corresponding equal angles and area scaling by the square, with geometrically similar triangles.')],'hard')
    add('linear_algebra','vector_addition',k,f'Animate adding u=({k},1) and v=(1,{k}) using head-to-tail arrows.',
        [label(f'sum = ({k+1}, {k+1})'),manual('Translate the second vector without rotation, and draw the resultant from the origin.')],'easy')
    add('linear_algebra','diagonal_map',k,f'Animate the matrix diag({a},2) acting on a grid and vector (1,1).',
        [point(1,1),point(a,2),label(f'determinant = {2*a}'),manual('Scale grid coordinates correctly along each axis and show area scaling by the determinant.')])
    add('linear_algebra','projection',k,f'Project vector ({a},{k}) orthogonally onto the x-axis.',
        [point(a,k),point(a,0),label(f'projection = ({a}, 0)'),manual('Show a perpendicular residual and decompose the vector into projection plus residual.')])
    add('linear_algebra','shear_invariant',k,f'Animate the shear matrix [[1,{k}],[0,1]] acting on a unit square.',
        [label('determinant = 1'),manual('Show the correct sheared parallelogram, fixed x-axis, and preservation of area.')],'hard')
    add('probability_statistics','bernoulli',k,f'Animate the probability mass function for a Bernoulli variable with p={k}/6.',
        [label(f'P(X=1) = {k}/6'),label(f'P(X=0) = {6-k}/6'),manual('Show two bars at 0 and 1 with proportional heights summing to one.')],'easy')
    add('probability_statistics','sample_mean',k,f'Animate computing the mean of [{k},{k+2},{k+4}] using a balance point on a number line.',
        [label(f'mean = {k+2}'),manual('Place all three data points and the balance point correctly; show signed deviations summing to zero.')])
    add('probability_statistics','uniform_density',k,f'Animate a uniform density on [0,{a}] and shade the probability over [0,1].',
        [label(f'density = 1/{a}'),label(f'probability = 1/{a}'),manual('Use density zero outside support and constant inside, and distinguish density height from total probability.')])
    add('probability_statistics','bayes_grid',k,f'Animate Bayes rule using 100 equally sized cells: {10*k} are group A, {5*k} of A and {10-k} outside A are positive.',
        [label(f'P(A|positive) = {5*k}/{4*k+10}'),manual('Highlight the correct intersection and conditioning set; normalize by all positive cells, not all A cells.')],'hard')

# Concept-disjoint development prompts; never split variants of one family across dev/test.
devs=[
('algebra','dev_difference_squares','Factor x^2-9 using a difference of squares.',[label('(x-3)(x+3)'),manual('Show a valid factorization sequence.')]),
('algebra','dev_absolute_inequality','Visualize |x|<2 on a number line.',[label('-2 < x < 2'),manual('Use open endpoints and the correct interval.')]),
('functions','dev_even_symmetry','Demonstrate even symmetry of cos(x).',[graph('cos(x)'),manual('Match x and -x at equal heights.')]),
('functions','dev_reciprocal','Plot 1/x and distinguish its two branches.',[manual('Exclude x=0 and show both asymptotes without connecting the branches.')]),
('calculus','dev_stationary','Show the stationary point of x^2+1.',[graph('x**2+1'),point(0,1),label('slope = 0')]),
('calculus','dev_antiderivative','Connect 3x^2 with its antiderivative x^3+C.',[graph('3*x**2'),manual('Differentiate the antiderivative and explain the constant.')]),
('geometry','dev_midpoint','Animate the midpoint between (0,0) and (4,2).',[point(2,1),manual('Show endpoints and equal half-segments.')]),
('geometry','dev_reflection','Reflect (2,1) across the y-axis.',[point(2,1),point(-2,1),manual('Show symmetry across the y-axis.')]),
('linear_algebra','dev_dot_product','Visualize (1,2) dot (3,1).',[label('dot product = 5'),manual('Explain multiplication and sum correctly.')]),
('linear_algebra','dev_zero_map','Show a zero matrix mapping all vectors to the origin.',[point(0,0),manual('Collapse at least two independent vectors.')]),
('probability_statistics','dev_median','Find the median of [1,3,8,9,12].',[label('median = 8'),manual('Show sorted order and middle element.')]),
('probability_statistics','dev_complement','Visualize the complement of an event of probability 1/4.',[label('complement = 3/4'),manual('Show disjoint exhaustive event and complement regions.')]),
]
for cat,family,prompt,checks in devs:add(cat,family,1,prompt,checks,'medium','dev')
(ROOT/'mathvizbench_draft.jsonl').write_text(''.join(t.model_dump_json()+'\n' for t in rows))
(ROOT/'task.schema.json').write_text(json.dumps(Task.model_json_schema(),indent=2))
print(json.dumps({'tasks':len(rows),'test':sum(t.split=='test' for t in rows),'dev':sum(t.split=='dev' for t in rows)}))
