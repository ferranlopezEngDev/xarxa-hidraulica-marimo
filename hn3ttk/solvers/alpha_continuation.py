from __future__ import annotations

from hn3ttk.solvers._alpha_continuation_common import run_alpha_continuation
from hn3ttk.solvers.newton_raphson import solve_newton_raphson
from hn3ttk.solvers.result import SolverResult
from hn3ttk.system import HydraulicSystem


def solve_alpha_continuation_newton(
    system: HydraulicSystem,
    initial_unknown_heads: list[float] | tuple[float, ...] | None = None,
    alpha_start: float = 0.0,
    alpha_end: float = 1.0,
    alpha_steps: int = 10,
    derivative_mode: str = "default",
    tolerance: float = 1.0e-9,
    step_tolerance: float = 1.0e-10,
    max_iterations_per_step: int = 50,
) -> SolverResult:
    """
    Solve a sequence of hydraulic problems using alpha continuation.

    The system is solved repeatedly for increasing ``alpha`` values from
    ``alpha_start`` to ``alpha_end`` using the plain Newton solver at each
    continuation step.
    """
    return run_alpha_continuation(
        system=system,
        step_solver=solve_newton_raphson,
        solver_name="alpha_continuation_newton",
        initial_unknown_heads=initial_unknown_heads,
        alpha_start=alpha_start,
        alpha_end=alpha_end,
        alpha_steps=alpha_steps,
        derivative_mode=derivative_mode,
        tolerance=tolerance,
        step_tolerance=step_tolerance,
        max_iterations_per_step=max_iterations_per_step,
        continuation_metadata={
            "inner_solver": "newton_raphson",
        },
    )
