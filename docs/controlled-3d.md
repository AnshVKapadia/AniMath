# Controlled 3D: first vertical slice

The first supported family rotates the region between sqrt(x) and x (washers),
or sqrt(x) and zero (disks), about the x-axis on [0,1]. This is deliberately
a bounded capability, not general-purpose 3D support.

Try: "Explain the washer method in 3D. Rotate the region between y=sqrt(x)
and y=x, from x=0 to x=1, about the x-axis. Show the rotation, isolate a
washer with its radii and thickness, and compute the volume. Show that a disk
has inner radius zero."

`revolution.py` extracts a typed specification and rejects unsupported requests.
`revolution_scene.py` compiles that specification into an actual ThreeDScene:
planar region, camera transition, rotating region, surface sectors, annular
cross-sections, a finite-thickness washer approximation, and the volume integral.
The disk variant uses pi/2; the washer variant uses pi/6. Rendered meshes are
finite-resolution approximations. Formula correctness is specific to this family.
All mathematical explanatory overlays use MathTex. Header and footer rails are
camera-fixed, fitted to bounded regions, and checked for frame escape and mutual
overlap before they are displayed.

The rendering pipeline saves revolution_plan.json and scene.py and uses the
existing local/sandbox renderer. A failure is reported, never replaced with a
free-form 2D animation. The extractor still relies on the configured language
model to interpret the prompt; schema validation is not proof of interpretation.

Local verification:

    .venv\Scripts\python.exe -m unittest tests.test_revolution tests.test_controlled_pipeline
    .venv-render\Scripts\python.exe -m manim -ql app/revolution_scene.py GeneratedScene

Next extensions should add independently tested families: arbitrary validated
radius functions/bounds, rotation about y, then vector geometry. Each needs
geometric invariants, bounded mesh/render budgets, and rendered visual checks.
Production sandbox performance must be checked independently of local rendering.
