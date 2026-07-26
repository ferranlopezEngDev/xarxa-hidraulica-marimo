from __future__ import annotations

from math import isfinite
from typing import Any, Callable

import numpy as np

from hn3ttk.solvers._common import predict_unknown_heads
from hn3ttk.solvers.result import SolverResult
from hn3ttk.system import HydraulicSystem


def run_alpha_continuation(
    *,
    system: HydraulicSystem,
    step_solver: Callable[..., SolverResult],
    solver_name: str,
    initial_unknown_heads: list[float] | tuple[float, ...] | None = None,
    alpha_start: float = 0.0,
    alpha_end: float = 1.0,
    alpha_steps: int = 10,
    derivative_mode: str = "default",
    tolerance: float = 1.0e-9,
    step_tolerance: float = 1.0e-10,
    max_iterations_per_step: int = 50,
    step_solver_kwargs: dict[str, Any] | None = None,
    continuation_metadata: dict[str, Any] | None = None,
) -> SolverResult:
    """Run a generic alpha continuation loop around a Newton-like solver."""
    if not isinstance(alpha_steps, int):
        raise TypeError("Parameter 'alpha_steps' must be an integer.")

    if alpha_steps < 1:
        raise ValueError("Parameter 'alpha_steps' must be at least 1.")

    if not isfinite(float(alpha_start)):
        raise ValueError("Parameter 'alpha_start' must be finite.")

    if not isfinite(float(alpha_end)):
        raise ValueError("Parameter 'alpha_end' must be finite.")

    alpha_values = np.linspace(alpha_start, alpha_end, alpha_steps + 1)

    if initial_unknown_heads is None:
        initial_unknown_heads = system.initial_unknown_heads()

    current_x = np.asarray(initial_unknown_heads, dtype=float).tolist()
    total_iterations = 0
    global_history: list[dict[str, Any]] = []
    final_result: SolverResult | None = None
    step_solver_kwargs = {} if step_solver_kwargs is None else dict(step_solver_kwargs)
    continuation_metadata = (
        {}
        if continuation_metadata is None
        else dict(continuation_metadata)
    )

    for continuation_step, alpha in enumerate(alpha_values):
        alpha = float(alpha)
        attempt_log: list[dict[str, Any]] = []
        attempted_configurations: set[tuple[str, tuple[float, ...]]] = set()

        candidate_heads = list(current_x)
        candidate_derivative_mode = derivative_mode

        if continuation_step == 0 and alpha == 0.0 and derivative_mode == "default":
            candidate_derivative_mode = "tendency"
        elif continuation_step > 0:
            candidate_heads = predict_unknown_heads(
                system,
                list(current_x),
                alpha,
            )

        result: SolverResult | None = None

        for guess, mode in (
            (candidate_heads, candidate_derivative_mode),
            (list(current_x), derivative_mode),
            (
                candidate_heads,
                "tendency" if derivative_mode == "default" else derivative_mode,
            ),
        ):
            key = (mode, tuple(float(value) for value in guess))

            if key in attempted_configurations:
                continue

            attempted_configurations.add(key)

            attempt_result = step_solver(
                system=system,
                initial_unknown_heads=guess,
                alpha=alpha,
                derivative_mode=mode,
                tolerance=tolerance,
                step_tolerance=step_tolerance,
                max_iterations=max_iterations_per_step,
                **step_solver_kwargs,
            )

            total_iterations += attempt_result.iterations
            attempt_log.append(
                {
                    "initial_unknown_heads": [float(value) for value in guess],
                    "derivative_mode": mode,
                    "success": attempt_result.success,
                    "message": attempt_result.message,
                    "iterations": attempt_result.iterations,
                    "max_abs_residual": attempt_result.max_abs_residual,
                }
            )

            result = attempt_result

            if attempt_result.success:
                break

        if result is None:
            raise RuntimeError(
                "Alpha continuation did not execute any Newton attempt."
            )

        global_history.append(
            {
                "continuation_step": continuation_step,
                "alpha": alpha,
                "newton_history": result.history,
                "success": result.success,
                "message": result.message,
                "iterations": result.iterations,
                "max_abs_residual": result.max_abs_residual,
                "attempts": attempt_log,
            }
        )

        if not result.success:
            failure_metadata = {
                "solver": solver_name,
                "failed_alpha": alpha,
                "alpha_start": float(alpha_start),
                "alpha_end": float(alpha_end),
                "alpha_steps": int(alpha_steps),
                "max_iterations_per_step": int(max_iterations_per_step),
                "alpha_values": [float(value) for value in alpha_values],
                "derivative_mode": derivative_mode,
            }
            failure_metadata.update(continuation_metadata)

            return SolverResult(
                success=False,
                message=(
                    f"Alpha continuation failed at alpha={alpha}: "
                    f"{result.message}"
                ),
                iterations=total_iterations,
                unknown_heads=result.unknown_heads,
                residuals=result.residuals,
                max_abs_residual=result.max_abs_residual,
                state=result.state,
                history=global_history,
                metadata=failure_metadata,
            )

        current_x = list(result.unknown_heads)
        final_result = result

    if final_result is None:
        raise RuntimeError("Alpha continuation did not execute any step.")

    success_metadata = {
        "solver": solver_name,
        "alpha_start": float(alpha_start),
        "alpha_end": float(alpha_end),
        "alpha_steps": int(alpha_steps),
        "max_iterations_per_step": int(max_iterations_per_step),
        "alpha_values": [float(value) for value in alpha_values],
        "derivative_mode": derivative_mode,
    }
    success_metadata.update(continuation_metadata)

    return SolverResult(
        success=True,
        message="Alpha continuation completed successfully.",
        iterations=total_iterations,
        unknown_heads=final_result.unknown_heads,
        residuals=final_result.residuals,
        max_abs_residual=final_result.max_abs_residual,
        state=final_result.state,
        history=global_history,
        metadata=success_metadata,
    )
