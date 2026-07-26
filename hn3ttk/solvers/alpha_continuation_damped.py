from __future__ import annotations

from hn3ttk.solvers._alpha_continuation_common import run_alpha_continuation
from hn3ttk.solvers.damped_newton_raphson import solve_damped_newton_raphson
from hn3ttk.solvers.result import SolverResult
from hn3ttk.system import HydraulicSystem


def solve_alpha_continuation_damped_newton(
    system: HydraulicSystem,
    initial_unknown_heads: list[float] | tuple[float, ...] | None = None,
    alpha_start: float = 0.0,
    alpha_end: float = 1.0,
    alpha_steps: int = 10,
    derivative_mode: str = "default",
    tolerance: float = 1.0e-9,
    step_tolerance: float = 1.0e-10,
    max_iterations_per_step: int = 50,
    initial_damping_factor: float = 1.0,
    damping_reduction_factor: float = 0.5,
    min_damping_factor: float = 1.0e-6,
    max_backtracking_steps: int = 20,
) -> SolverResult:
    """
    Solve a sequence of hydraulic problems using damped Newton continuation.

    The system is solved repeatedly for increasing ``alpha`` values from
    ``alpha_start`` to ``alpha_end`` using the damped Newton solver at each
    continuation step.
    """
    return run_alpha_continuation(
        system=system,
        step_solver=solve_damped_newton_raphson,
        solver_name="alpha_continuation_damped_newton",
        initial_unknown_heads=initial_unknown_heads,
        alpha_start=alpha_start,
        alpha_end=alpha_end,
        alpha_steps=alpha_steps,
        derivative_mode=derivative_mode,
        tolerance=tolerance,
        step_tolerance=step_tolerance,
        max_iterations_per_step=max_iterations_per_step,
        step_solver_kwargs={
            "initial_damping_factor": initial_damping_factor,
            "damping_reduction_factor": damping_reduction_factor,
            "min_damping_factor": min_damping_factor,
            "max_backtracking_steps": max_backtracking_steps,
        },
        continuation_metadata={
            "inner_solver": "damped_newton_raphson",
            "initial_damping_factor": float(initial_damping_factor),
            "damping_reduction_factor": float(damping_reduction_factor),
            "min_damping_factor": float(min_damping_factor),
            "max_backtracking_steps": int(max_backtracking_steps),
        },
    )
