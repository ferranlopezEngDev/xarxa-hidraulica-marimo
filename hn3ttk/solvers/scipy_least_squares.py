from __future__ import annotations

from math import isfinite
from typing import Any

import numpy as np
from scipy.optimize import least_squares

from hn3ttk.solvers._common import build_solver_result
from hn3ttk.solvers.result import SolverResult
from hn3ttk.system import HydraulicSystem

SCIPY_LEAST_SQUARES_METHODS = (
    "trf",
    "dogbox",
    "lm",
)


def _is_unbounded_bounds(bounds: tuple[Any, Any]) -> bool:
    """Return True if the bounds are equivalent to (-inf, inf)."""
    lower, upper = bounds
    lower_array = np.asarray(lower, dtype=float)
    upper_array = np.asarray(upper, dtype=float)
    return bool(
        np.all(np.isneginf(lower_array))
        and np.all(np.isposinf(upper_array))
    )


def solve_scipy_least_squares(
    system: HydraulicSystem,
    initial_unknown_heads: list[float] | tuple[float, ...] | None = None,
    alpha: float = 1.0,
    method: str = "trf",
    use_jacobian: bool = True,
    derivative_mode: str = "default",
    tolerance: float = 1.0e-9,
    residual_tolerance: float = 1.0e-8,
    bounds: tuple[Any, Any] = (-np.inf, np.inf),
    loss: str = "linear",
    f_scale: float = 1.0,
    max_function_evaluations: int | None = None,
    kwargs: dict[str, Any] | None = None,
) -> SolverResult:
    """
    Solve the hydraulic system using ``scipy.optimize.least_squares``.

    Parameters
    ----------
    system:
        Hydraulic system to solve.
    initial_unknown_heads:
        Optional initial guess for unknown-head nodes.
    alpha:
        Continuation factor used while evaluating the equations.
    method:
        SciPy least-squares method, usually ``"trf"``, ``"dogbox"`` or ``"lm"``.
    use_jacobian:
        If ``True``, use the analytical dense Jacobian when possible.
    derivative_mode:
        Jacobian derivative strategy forwarded to connection models.
    tolerance:
        Main SciPy tolerance used for ``ftol``, ``xtol`` and ``gtol``.
    residual_tolerance:
        Extra acceptance criterion applied by HN3Ttk after SciPy returns.
    bounds:
        Lower and upper bounds for the unknown-head vector.
    loss:
        Robust loss name forwarded to SciPy.
    f_scale:
        Scaling parameter for the selected loss.
    max_function_evaluations:
        Optional evaluation budget forwarded to SciPy.
    kwargs:
        Optional extra keyword arguments passed to SciPy.
    """
    if method not in SCIPY_LEAST_SQUARES_METHODS:
        raise ValueError(
            f"Invalid SciPy least_squares method '{method}'. "
            f"Allowed values are: {SCIPY_LEAST_SQUARES_METHODS}."
        )

    if method == "lm":
        if not _is_unbounded_bounds(bounds):
            raise ValueError(
                "SciPy least_squares method 'lm' does not support bounds."
            )

        if loss != "linear":
            raise ValueError(
                "SciPy least_squares method 'lm' requires loss='linear'."
            )

    if initial_unknown_heads is None:
        initial_unknown_heads = system.initial_unknown_heads()

    x0 = np.asarray(initial_unknown_heads, dtype=float)

    def fun(x: np.ndarray) -> np.ndarray:
        return np.asarray(
            system.nodal_flow_residuals(x.tolist(), alpha=alpha),
            dtype=float,
        )

    def jac(x: np.ndarray) -> np.ndarray:
        jacobian = system.dense_jacobian(
            x.tolist(),
            alpha=alpha,
            derivative_mode=derivative_mode,
        )

        if np.all(np.isfinite(jacobian)):
            return jacobian

        return system.finite_difference_jacobian(
            x.tolist(),
            alpha=alpha,
        )

    if x0.size == 0:
        final_residual = fun(x0)
        history = [
            {
                "alpha": float(alpha),
                "method": method,
                "unknown_heads": x0.tolist(),
                "residuals": final_residual.tolist(),
                "max_abs_residual": 0.0,
                "cost": 0.0,
                "optimality": 0.0,
                "scipy_success": True,
                "scipy_message": "No unknown heads.",
                "nfev": 0,
                "njev": None,
            }
        ]
        metadata = {
            "solver": "scipy_least_squares",
            "scipy_method": method,
            "alpha": float(alpha),
            "use_jacobian": bool(use_jacobian),
            "jacobian_used": bool(use_jacobian),
            "derivative_mode": derivative_mode,
            "tolerance": float(tolerance),
            "residual_tolerance": float(residual_tolerance),
            "loss": loss,
            "f_scale": float(f_scale),
            "max_function_evaluations": max_function_evaluations,
            "scipy_success": True,
            "scipy_status": 0,
            "scipy_message": "No unknown heads.",
            "nfev": 0,
            "njev": None,
            "cost": 0.0,
            "optimality": 0.0,
        }
        return build_solver_result(
            success=True,
            message="SciPy least_squares converged.",
            iterations=0,
            unknown_heads=x0.tolist(),
            residuals=final_residual.tolist(),
            max_abs_residual=0.0,
            system=system,
            alpha=alpha,
            history=history,
            metadata=metadata,
        )

    jac_argument: str | Any

    if use_jacobian:
        jac_argument = jac
    else:
        jac_argument = "2-point"

    scipy_kwargs = {} if kwargs is None else dict(kwargs)

    scipy_result = least_squares(
        fun=fun,
        x0=x0,
        jac=jac_argument,
        bounds=bounds,
        method=method,
        ftol=tolerance,
        xtol=tolerance,
        gtol=tolerance,
        loss=loss,
        f_scale=f_scale,
        max_nfev=max_function_evaluations,
        **scipy_kwargs,
    )

    final_x = np.asarray(scipy_result.x, dtype=float)
    final_residual = fun(final_x)
    max_abs_residual = (
        0.0
        if final_residual.size == 0
        else float(np.max(np.abs(final_residual)))
    )

    if (
        bool(scipy_result.success)
        and max_abs_residual > min(residual_tolerance, tolerance)
        and tolerance > 0.0
    ):
        refined_result = least_squares(
            fun=fun,
            x0=final_x,
            jac=jac_argument,
            bounds=bounds,
            method=method,
            ftol=tolerance,
            xtol=tolerance,
            gtol=tolerance * 0.1,
            loss=loss,
            f_scale=f_scale,
            max_nfev=max_function_evaluations,
            **scipy_kwargs,
        )

        refined_x = np.asarray(refined_result.x, dtype=float)
        refined_residual = fun(refined_x)
        refined_max_abs_residual = (
            0.0
            if refined_residual.size == 0
            else float(np.max(np.abs(refined_residual)))
        )

        if refined_max_abs_residual <= max_abs_residual:
            scipy_result = refined_result
            final_x = refined_x
            final_residual = refined_residual
            max_abs_residual = refined_max_abs_residual

    success = bool(scipy_result.success) and max_abs_residual <= residual_tolerance

    if success:
        message = "SciPy least_squares converged."
    else:
        message = (
            "SciPy least_squares failed or residual tolerance not reached: "
            f"{scipy_result.message}"
        )

    iterations = int(getattr(scipy_result, "nfev", 0))
    njev = getattr(scipy_result, "njev", None)

    history = [
        {
            "alpha": float(alpha),
            "method": method,
            "unknown_heads": final_x.tolist(),
            "residuals": final_residual.tolist(),
            "max_abs_residual": max_abs_residual,
            "cost": float(getattr(scipy_result, "cost", 0.0)),
            "optimality": float(getattr(scipy_result, "optimality", 0.0)),
            "scipy_success": bool(scipy_result.success),
            "scipy_message": str(scipy_result.message),
            "nfev": int(getattr(scipy_result, "nfev", 0)),
            "njev": None if njev is None else int(njev),
        }
    ]

    metadata = {
        "solver": "scipy_least_squares",
        "scipy_method": method,
        "alpha": float(alpha),
        "use_jacobian": bool(use_jacobian),
        "jacobian_used": bool(use_jacobian),
        "derivative_mode": derivative_mode,
        "tolerance": float(tolerance),
        "residual_tolerance": float(residual_tolerance),
        "loss": loss,
        "f_scale": float(f_scale),
        "max_function_evaluations": max_function_evaluations,
        "scipy_success": bool(scipy_result.success),
        "scipy_status": int(getattr(scipy_result, "status", 0)),
        "scipy_message": str(scipy_result.message),
        "nfev": int(getattr(scipy_result, "nfev", 0)),
        "njev": None if njev is None else int(njev),
        "cost": float(getattr(scipy_result, "cost", 0.0)),
        "optimality": float(getattr(scipy_result, "optimality", 0.0)),
    }

    return build_solver_result(
        success=success,
        message=message,
        iterations=iterations,
        unknown_heads=final_x.tolist(),
        residuals=final_residual.tolist(),
        max_abs_residual=max_abs_residual,
        system=system,
        alpha=alpha,
        history=history,
        metadata=metadata,
    )


def solve_alpha_continuation_scipy_least_squares(
    system: HydraulicSystem,
    initial_unknown_heads: list[float] | tuple[float, ...] | None = None,
    alpha_start: float = 0.0,
    alpha_end: float = 1.0,
    alpha_steps: int = 10,
    method: str = "trf",
    use_jacobian: bool = True,
    derivative_mode: str = "default",
    tolerance: float = 1.0e-9,
    residual_tolerance: float = 1.0e-8,
    bounds: tuple[Any, Any] = (-np.inf, np.inf),
    loss: str = "linear",
    f_scale: float = 1.0,
    max_function_evaluations: int | None = None,
    kwargs: dict[str, Any] | None = None,
) -> SolverResult:
    """Solve a sequence of hydraulic problems using SciPy least_squares."""
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

    for continuation_step, alpha in enumerate(alpha_values):
        alpha = float(alpha)

        result = solve_scipy_least_squares(
            system=system,
            initial_unknown_heads=current_x,
            alpha=alpha,
            method=method,
            use_jacobian=use_jacobian,
            derivative_mode=derivative_mode,
            tolerance=tolerance,
            residual_tolerance=residual_tolerance,
            bounds=bounds,
            loss=loss,
            f_scale=f_scale,
            max_function_evaluations=max_function_evaluations,
            kwargs=kwargs,
        )

        total_iterations += result.iterations
        global_history.append(
            {
                "continuation_step": continuation_step,
                "alpha": alpha,
                "success": result.success,
                "message": result.message,
                "iterations": result.iterations,
                "unknown_heads": result.unknown_heads,
                "residuals": result.residuals,
                "max_abs_residual": result.max_abs_residual,
                "inner_history": result.history,
            }
        )

        if not result.success:
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
                metadata={
                    "solver": "alpha_continuation_scipy_least_squares",
                    "inner_solver": "scipy_least_squares",
                    "scipy_method": method,
                    "alpha_start": float(alpha_start),
                    "alpha_end": float(alpha_end),
                    "alpha_steps": int(alpha_steps),
                    "alpha_values": [float(value) for value in alpha_values],
                    "use_jacobian": bool(use_jacobian),
                    "derivative_mode": derivative_mode,
                    "loss": loss,
                    "f_scale": float(f_scale),
                    "failed_alpha": alpha,
                },
            )

        current_x = list(result.unknown_heads)
        final_result = result

    if final_result is None:
        raise RuntimeError(
            "SciPy least_squares continuation did not execute any step."
        )

    return SolverResult(
        success=True,
        message="SciPy least_squares continuation converged.",
        iterations=total_iterations,
        unknown_heads=final_result.unknown_heads,
        residuals=final_result.residuals,
        max_abs_residual=final_result.max_abs_residual,
        state=final_result.state,
        history=global_history,
        metadata={
            "solver": "alpha_continuation_scipy_least_squares",
            "inner_solver": "scipy_least_squares",
            "scipy_method": method,
            "alpha_start": float(alpha_start),
            "alpha_end": float(alpha_end),
            "alpha_steps": int(alpha_steps),
            "alpha_values": [float(value) for value in alpha_values],
            "use_jacobian": bool(use_jacobian),
            "derivative_mode": derivative_mode,
            "loss": loss,
            "f_scale": float(f_scale),
        },
    )
