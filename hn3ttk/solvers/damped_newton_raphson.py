from __future__ import annotations

from math import isfinite
from typing import Any

import numpy as np

from hn3ttk.solvers._common import build_solver_result
from hn3ttk.solvers.result import SolverResult
from hn3ttk.system import HydraulicSystem


def solve_damped_newton_raphson(
    system: HydraulicSystem,
    initial_unknown_heads: list[float] | tuple[float, ...] | None = None,
    alpha: float = 1.0,
    derivative_mode: str = "default",
    tolerance: float = 1.0e-9,
    step_tolerance: float = 1.0e-10,
    max_iterations: int = 50,
    initial_damping_factor: float = 1.0,
    damping_reduction_factor: float = 0.5,
    min_damping_factor: float = 1.0e-6,
    max_backtracking_steps: int = 20,
) -> SolverResult:
    """
    Solve the hydraulic system with a damped Newton-Raphson method.

    Parameters
    ----------
    system:
        Hydraulic system to solve.
    initial_unknown_heads:
        Optional initial guess for unknown-head nodes.
    alpha:
        Continuation factor used while evaluating the equations.
    derivative_mode:
        Jacobian derivative strategy forwarded to connection models.
    tolerance:
        Residual convergence tolerance.
    step_tolerance:
        Accepted step-size tolerance for early convergence.
    max_iterations:
        Maximum Newton iterations.
    initial_damping_factor:
        First damping factor tried for each Newton step.
    damping_reduction_factor:
        Multiplicative reduction used during backtracking.
    min_damping_factor:
        Smallest damping factor accepted before failing the step.
    max_backtracking_steps:
        Maximum number of damping trials per Newton iteration.

    Returns
    -------
    SolverResult
        Final solution, residuals, convergence message and iteration history.
    """
    if not isfinite(float(initial_damping_factor)):
        raise ValueError("Parameter 'initial_damping_factor' must be finite.")

    if not isfinite(float(damping_reduction_factor)):
        raise ValueError("Parameter 'damping_reduction_factor' must be finite.")

    if not isfinite(float(min_damping_factor)):
        raise ValueError("Parameter 'min_damping_factor' must be finite.")

    if not isinstance(max_backtracking_steps, int):
        raise TypeError("Parameter 'max_backtracking_steps' must be an integer.")

    initial_damping_factor = float(initial_damping_factor)
    damping_reduction_factor = float(damping_reduction_factor)
    min_damping_factor = float(min_damping_factor)

    if initial_damping_factor <= 0.0 or initial_damping_factor > 1.0:
        raise ValueError(
            "Parameter 'initial_damping_factor' must be in the interval (0, 1]."
        )

    if damping_reduction_factor <= 0.0 or damping_reduction_factor >= 1.0:
        raise ValueError(
            "Parameter 'damping_reduction_factor' must be in the interval (0, 1)."
        )

    if min_damping_factor <= 0.0 or min_damping_factor > initial_damping_factor:
        raise ValueError(
            "Parameter 'min_damping_factor' must be positive and not greater "
            "than 'initial_damping_factor'."
        )

    if max_backtracking_steps < 1:
        raise ValueError("Parameter 'max_backtracking_steps' must be at least 1.")

    if initial_unknown_heads is None:
        initial_unknown_heads = system.initial_unknown_heads()

    x = np.asarray(initial_unknown_heads, dtype=float)
    history: list[dict[str, Any]] = []
    metadata = {
        "solver": "damped_newton_raphson",
        "alpha": float(alpha),
        "derivative_mode": derivative_mode,
        "tolerance": float(tolerance),
        "step_tolerance": float(step_tolerance),
        "max_iterations": int(max_iterations),
        "initial_damping_factor": initial_damping_factor,
        "damping_reduction_factor": damping_reduction_factor,
        "min_damping_factor": min_damping_factor,
        "max_backtracking_steps": int(max_backtracking_steps),
    }

    for iteration in range(max_iterations):
        residual = np.asarray(
            system.nodal_flow_residuals(x.tolist(), alpha=alpha),
            dtype=float,
        )

        max_abs_residual = (
            0.0
            if residual.size == 0
            else float(np.max(np.abs(residual)))
        )

        history_entry: dict[str, Any] = {
            "iteration": iteration,
            "alpha": float(alpha),
            "unknown_heads": x.tolist(),
            "residuals": residual.tolist(),
            "max_abs_residual": max_abs_residual,
        }
        history.append(history_entry)

        if not np.all(np.isfinite(residual)):
            return build_solver_result(
                success=False,
                message="Residual contains non-finite values.",
                iterations=iteration,
                unknown_heads=x.tolist(),
                residuals=residual.tolist(),
                max_abs_residual=max_abs_residual,
                system=system,
                alpha=alpha,
                history=history,
                metadata=metadata,
            )

        if max_abs_residual <= tolerance:
            return build_solver_result(
                success=True,
                message="Converged by residual tolerance.",
                iterations=iteration,
                unknown_heads=x.tolist(),
                residuals=residual.tolist(),
                max_abs_residual=max_abs_residual,
                system=system,
                alpha=alpha,
                history=history,
                metadata=metadata,
            )

        jacobian = system.dense_jacobian(
            x.tolist(),
            alpha=alpha,
            derivative_mode=derivative_mode,
        )

        if not np.all(np.isfinite(jacobian)):
            return build_solver_result(
                success=False,
                message="Jacobian contains non-finite values.",
                iterations=iteration,
                unknown_heads=x.tolist(),
                residuals=residual.tolist(),
                max_abs_residual=max_abs_residual,
                system=system,
                alpha=alpha,
                history=history,
                metadata=metadata,
            )

        try:
            step = np.linalg.solve(jacobian, -residual)
        except np.linalg.LinAlgError as error:
            return build_solver_result(
                success=False,
                message=f"Jacobian solve failed: {error}",
                iterations=iteration,
                unknown_heads=x.tolist(),
                residuals=residual.tolist(),
                max_abs_residual=max_abs_residual,
                system=system,
                alpha=alpha,
                history=history,
                metadata=metadata,
            )

        if not np.all(np.isfinite(step)):
            history_entry["step"] = step.tolist()
            history_entry["max_abs_step"] = (
                0.0
                if step.size == 0
                else float(np.max(np.abs(step)))
            )

            return build_solver_result(
                success=False,
                message="Newton step contains non-finite values.",
                iterations=iteration,
                unknown_heads=x.tolist(),
                residuals=residual.tolist(),
                max_abs_residual=max_abs_residual,
                system=system,
                alpha=alpha,
                history=history,
                metadata=metadata,
            )

        max_abs_step = (
            0.0
            if step.size == 0
            else float(np.max(np.abs(step)))
        )

        history_entry["step"] = step.tolist()
        history_entry["max_abs_step"] = max_abs_step

        damping_factor = initial_damping_factor
        accepted = False
        accepted_x = x
        accepted_residual = residual
        accepted_max_abs_residual = max_abs_residual
        backtracking_history: list[dict[str, Any]] = []

        for backtracking_step in range(max_backtracking_steps):
            trial_x = x + damping_factor * step
            trial_residual = np.asarray(
                system.nodal_flow_residuals(trial_x.tolist(), alpha=alpha),
                dtype=float,
            )
            trial_max_abs_residual = (
                0.0
                if trial_residual.size == 0
                else float(np.max(np.abs(trial_residual)))
            )

            backtracking_history.append(
                {
                    "backtracking_step": backtracking_step,
                    "damping_factor": float(damping_factor),
                    "trial_unknown_heads": trial_x.tolist(),
                    "trial_residuals": trial_residual.tolist(),
                    "trial_max_abs_residual": trial_max_abs_residual,
                }
            )

            if (
                np.all(np.isfinite(trial_residual))
                and trial_max_abs_residual < max_abs_residual
            ):
                accepted = True
                accepted_x = trial_x
                accepted_residual = trial_residual
                accepted_max_abs_residual = trial_max_abs_residual
                break

            damping_factor *= damping_reduction_factor

            if damping_factor < min_damping_factor:
                break

        history_entry["backtracking"] = backtracking_history

        if not accepted:
            return build_solver_result(
                success=False,
                message="Backtracking failed to reduce residual.",
                iterations=iteration,
                unknown_heads=x.tolist(),
                residuals=residual.tolist(),
                max_abs_residual=max_abs_residual,
                system=system,
                alpha=alpha,
                history=history,
                metadata=metadata,
            )

        accepted_step = damping_factor * step
        max_abs_accepted_step = (
            0.0
            if accepted_step.size == 0
            else float(np.max(np.abs(accepted_step)))
        )

        history_entry["damping_factor"] = float(damping_factor)
        history_entry["accepted_step"] = accepted_step.tolist()
        history_entry["max_abs_accepted_step"] = max_abs_accepted_step
        history_entry["accepted_max_abs_residual"] = accepted_max_abs_residual
        history_entry["backtracking_steps"] = len(backtracking_history) - 1

        x = accepted_x

        if max_abs_accepted_step <= step_tolerance:
            if not np.all(np.isfinite(accepted_residual)):
                return build_solver_result(
                    success=False,
                    message="Residual contains non-finite values.",
                    iterations=iteration + 1,
                    unknown_heads=x.tolist(),
                    residuals=accepted_residual.tolist(),
                    max_abs_residual=accepted_max_abs_residual,
                    system=system,
                    alpha=alpha,
                    history=history,
                    metadata=metadata,
                )

            return build_solver_result(
                success=True,
                message="Converged by step tolerance.",
                iterations=iteration + 1,
                unknown_heads=x.tolist(),
                residuals=accepted_residual.tolist(),
                max_abs_residual=accepted_max_abs_residual,
                system=system,
                alpha=alpha,
                history=history,
                metadata=metadata,
            )

    final_residual = np.asarray(
        system.nodal_flow_residuals(x.tolist(), alpha=alpha),
        dtype=float,
    )
    final_max_abs_residual = (
        0.0
        if final_residual.size == 0
        else float(np.max(np.abs(final_residual)))
    )

    return build_solver_result(
        success=False,
        message="Maximum number of iterations reached.",
        iterations=max_iterations,
        unknown_heads=x.tolist(),
        residuals=final_residual.tolist(),
        max_abs_residual=final_max_abs_residual,
        system=system,
        alpha=alpha,
        history=history,
        metadata=metadata,
    )
