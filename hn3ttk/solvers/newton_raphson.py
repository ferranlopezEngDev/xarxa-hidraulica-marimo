from __future__ import annotations

from typing import Any

import numpy as np

from hn3ttk.solvers._common import build_solver_result
from hn3ttk.solvers.result import SolverResult
from hn3ttk.system import HydraulicSystem


def solve_newton_raphson(
    system: HydraulicSystem,
    initial_unknown_heads: list[float] | tuple[float, ...] | None = None,
    alpha: float = 1.0,
    derivative_mode: str = "default",
    tolerance: float = 1.0e-9,
    step_tolerance: float = 1.0e-10,
    max_iterations: int = 50,
) -> SolverResult:
    """
    Solve the hydraulic system with a simple Newton-Raphson method.

    Parameters
    ----------
    system:
        Hydraulic system to solve.
    initial_unknown_heads:
        Optional initial guess for unknown-head nodes. If omitted, the system
        initial guesses are used.
    alpha:
        Continuation factor used while evaluating the equations.
    derivative_mode:
        Jacobian derivative strategy forwarded to connection models.
    tolerance:
        Residual convergence tolerance.
    step_tolerance:
        Step-size convergence tolerance.
    max_iterations:
        Maximum number of Newton iterations.

    Returns
    -------
    SolverResult
        Final solution, residuals, convergence message and iteration history.

    Notes
    -----
    This is a plain Newton method: no damping, no line search and no step
    clipping.
    """
    if initial_unknown_heads is None:
        initial_unknown_heads = system.initial_unknown_heads()

    x = np.asarray(initial_unknown_heads, dtype=float)
    history: list[dict[str, Any]] = []
    metadata = {
        "solver": "newton_raphson",
        "alpha": float(alpha),
        "derivative_mode": derivative_mode,
        "tolerance": float(tolerance),
        "step_tolerance": float(step_tolerance),
        "max_iterations": int(max_iterations),
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

        x = x + step

        if max_abs_step <= step_tolerance:
            final_residual = np.asarray(
                system.nodal_flow_residuals(x.tolist(), alpha=alpha),
                dtype=float,
            )
            final_max_abs_residual = (
                0.0
                if final_residual.size == 0
                else float(np.max(np.abs(final_residual)))
            )

            if not np.all(np.isfinite(final_residual)):
                return build_solver_result(
                    success=False,
                    message="Residual contains non-finite values.",
                    iterations=iteration + 1,
                    unknown_heads=x.tolist(),
                    residuals=final_residual.tolist(),
                    max_abs_residual=final_max_abs_residual,
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
                residuals=final_residual.tolist(),
                max_abs_residual=final_max_abs_residual,
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
