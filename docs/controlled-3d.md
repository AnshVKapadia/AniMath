# Controlled 3D: first vertical slice

The controlled family rotates a region between validated nonnegative radius
functions about the x-axis. Expressions use the same restricted arithmetic and
math-function grammar as graph scenes. Bounds must be finite and increasing;
sampled geometric validation rejects negative, crossing, non-finite, or
unreasonably large radii. This is still deliberately bounded capability, not
general-purpose 3D support.

Try: "Explain the washer method in 3D. Rotate the region between y=sqrt(x)
and y=x, from x=0 to x=1, about the x-axis. Show the rotation, isolate a
washer with its radii and thickness, and compute the volume. Show that a disk
has inner radius zero."

`revolution.py` extracts a typed specification and rejects unsupported requests.
`revolution_scene.py` compiles that specification into an actual ThreeDScene:
planar region, camera transition, rotating region, surface sectors, annular
cross-sections, a finite-thickness washer approximation, and the volume integral.
Rendered meshes and the displayed numerical volume are finite-resolution
approximations. Formula correctness is specific to x-axis solids of revolution.
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

Next extensions should add independently tested families: rotation about the
y-axis, shells, then vector geometry. Each needs
geometric invariants, bounded mesh/render budgets, and rendered visual checks.
Production sandbox performance must be checked independently of local rendering.
