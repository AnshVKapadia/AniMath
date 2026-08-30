from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from app.rendering import run_generation_pipeline


BENCHMARK_PROMPTS = {
    "derivative": (
        "Show why the derivative of x^2 is 2x using a secant line that becomes "
        "a tangent."
    ),
    "riemann": (
        "Visualize Riemann rectangles for the area under f(x)=x^2 from x=0 to "
        "x=2, then show the definite integral."
    ),
    "equation": (
        "Explain algebraically why the geometric series 1 + r + r^2 + ... equals "
        "1/(1-r) for absolute value of r less than 1. Use equation transformations "
        "rather than a graph."
    ),
}


def main() -> int:
    failures = 0
    run_id = uuid4().hex[:8]
    for name, prompt in BENCHMARK_PROMPTS.items():
        job_id = f"benchmark-{run_id}-{name}"
        started = perf_counter()
        try:
            result = run_generation_pipeline(job_id, prompt)
        except Exception as exc:
            failures += 1
            print(f"{name}: FAIL after {perf_counter() - started:.2f}s ({exc})")
            continue

        route = "fallback" if result.repaired else "controlled"
        print(
            f"{name}: PASS via {route} in {perf_counter() - started:.2f}s "
            f"({result.video_path})"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
