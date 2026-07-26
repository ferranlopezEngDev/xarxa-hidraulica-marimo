from __future__ import annotations

from math import isfinite
from typing import Any

import numpy as np
from scipy.optimize import root

from hn3ttk.solvers._common import build_solver_result
from hn3ttk.solvers.result import SolverResult
from hn3ttk.system import HydraulicSystem

SCIPY_ROOT_METHODS = (
    "hybr",
    "lm",
    "broyden1",
    "broyden2",
    "anderson",
    "linearmixing",
    "diagbroyden",
    "excitingmixing",
    "krylov",
    "df-sane",
)


def solve_scipy_root(
    system: HydraulicSystem,
    initial_unknown_heads: list[float] | tuple[float, ...] | None = None,
    alpha: float = 1.0,
    method: str = "hybr",
    use_jacobian: bool = True,
    derivative_mode: str = "default",
    tolerance: float = 1.0e-9,
    residual_tolerance: float = 1.0e-8,
    max_function_evaluations: int | None = None,
    options: dict[str, Any] | None = None,
) -> SolverResult:
    """
    Solve the hydraulic system using ``scipy.optimize.root``.

    Parameters
    ----------
    system:
        Hydraulic system to solve.
    initial_unknown_heads:
        Optional initial guess for unknown-head nodes. If omitted, the system
        initial guesses are used.
    alpha:
        Continuation factor applied while evaluating the system equations.
    method:
        SciPy root method, for example ``"hybr"``, ``"lm"`` or ``"krylov"``.
    use_jacobian:
        If ``True``, use the analytical dense Jacobian when the selected SciPy
        method supports it.
    derivative_mode:
        Jacobian derivative strategy forwarded to connection models.
    tolerance:
        Main SciPy solver tolerance.
    residual_tolerance:
        Extra acceptance criterion applied by HN3Ttk after SciPy returns.
    max_function_evaluations:
        Optional iteration/evaluation budget forwarded to SciPy.
    options:
        Optional raw SciPy options dictionary.

    Returns
    -------
    SolverResult
        Final solution, residuals, convergence message and metadata.
    """
    if method not in SCIPY_ROOT_METHODS:
        raise ValueError(
            f"Invalid SciPy root method '{method}'. "
            f"Allowed values are: {SCIPY_ROOT_METHODS}."
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
                "scipy_success": True,
                "scipy_message": "No unknown heads.",
                "nfev": 0,
                "njev": None,
            }
        ]
        metadata = {
            "solver": "scipy_root",
            "scipy_method": method,
            "alpha": float(alpha),
            "use_jacobian": bool(use_jacobian),
            "jacobian_used": False,
            "derivative_mode": derivative_mode,
            "tolerance": float(tolerance),
            "residual_tolerance": float(residual_tolerance),
            "max_function_evaluations": max_function_evaluations,
            "scipy_success": True,
            "scipy_status": 0,
            "scipy_message": "No unknown heads.",
            "nfev": 0,
            "njev": None,
        }
        return build_solver_result(
            success=True,
            message="SciPy root converged.",
            iterations=0,
            unknown_heads=x0.tolist(),
            residuals=final_residual.tolist(),
            max_abs_residual=0.0,
            system=system,
            alpha=alpha,
            history=history,
            metadata=metadata,
        )

    jacobian_should_be_used = bool(use_jacobian) and method in ("hybr", "lm")

    scipy_options = {} if options is None else dict(options)

    if max_function_evaluations is not None:
        if method in ("hybr", "lm", "df-sane"):
            scipy_options.setdefault("maxfev", int(max_function_evaluations))
        else:
            scipy_options.setdefault("maxiter", int(max_function_evaluations))

    scipy_result = root(
        fun=fun,
        x0=x0,
        method=method,
        jac=jac if jacobian_should_be_used else None,
        tol=tolerance,
        options=scipy_options,
    )

    final_x = np.asarray(scipy_result.x, dtype=float)
    final_residual = fun(final_x)
    max_abs_residual = (
        0.0
        if final_residual.size == 0
        else float(np.max(np.abs(final_residual)))
    )

    success = bool(scipy_result.success) and max_abs_residual <= residual_tolerance

    if success:
        message = "SciPy root converged."
    else:
        message = (
            "SciPy root failed or residual tolerance not reached: "
            f"{scipy_result.message}"
        )

    iterations = int(
        getattr(
            scipy_result,
            "nit",
            getattr(scipy_result, "nfev", 0),
        )
    )

    njev = getattr(scipy_result, "njev", None)

    history = [
        {
            "alpha": float(alpha),
            "method": method,
            "unknown_heads": final_x.tolist(),
            "residuals": final_residual.tolist(),
            "max_abs_residual": max_abs_residual,
            "scipy_success": bool(scipy_result.success),
            "scipy_message": str(scipy_result.message),
            "nfev": int(getattr(scipy_result, "nfev", 0)),
            "njev": None if njev is None else int(njev),
        }
    ]

    metadata = {
        "solver": "scipy_root",
        "scipy_method": method,
        "alpha": float(alpha),
        "use_jacobian": bool(use_jacobian),
        "jacobian_used": bool(jacobian_should_be_used),
        "derivative_mode": derivative_mode,
        "tolerance": float(tolerance),
        "residual_tolerance": float(residual_tolerance),
        "max_function_evaluations": max_function_evaluations,
        "scipy_success": bool(scipy_result.success),
        "scipy_status": int(getattr(scipy_result, "status", 0)),
        "scipy_message": str(scipy_result.message),
        "nfev": int(getattr(scipy_result, "nfev", 0)),
        "njev": None if njev is None else int(njev),
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


def solve_alpha_continuation_scipy_root(
    system: HydraulicSystem,
    initial_unknown_heads: list[float] | tuple[float, ...] | None = None,
    alpha_start: float = 0.0,
    alpha_end: float = 1.0,
    alpha_steps: int = 10,
    method: str = "hybr",
    use_jacobian: bool = True,
    derivative_mode: str = "default",
    tolerance: float = 1.0e-9,
    residual_tolerance: float = 1.0e-8,
    max_function_evaluations: int | None = None,
    options: dict[str, Any] | None = None,
) -> SolverResult:
    """
    Solve a sequence of hydraulic problems using SciPy root continuation.

    The problem is solved repeatedly for increasing ``alpha`` values from
    ``alpha_start`` to ``alpha_end``. The solution of one step is reused as the
    initial guess for the next step.
    """
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

        result = solve_scipy_root(
            system=system,
            initial_unknown_heads=current_x,
            alpha=alpha,
            method=method,
            use_jacobian=use_jacobian,
            derivative_mode=derivative_mode,
            tolerance=tolerance,
            residual_tolerance=residual_tolerance,
            max_function_evaluations=max_function_evaluations,
            options=options,
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
                    "solver": "alpha_continuation_scipy_root",
                    "inner_solver": "scipy_root",
                    "scipy_method": method,
                    "alpha_start": float(alpha_start),
                    "alpha_end": float(alpha_end),
                    "alpha_steps": int(alpha_steps),
                    "alpha_values": [float(value) for value in alpha_values],
                    "use_jacobian": bool(use_jacobian),
                    "derivative_mode": derivative_mode,
                    "failed_alpha": alpha,
                },
            )

        current_x = list(result.unknown_heads)
        final_result = result

    if final_result is None:
        raise RuntimeError("SciPy root continuation did not execute any step.")

    return SolverResult(
        success=True,
        message="SciPy root continuation converged.",
        iterations=total_iterations,
        unknown_heads=final_result.unknown_heads,
        residuals=final_result.residuals,
        max_abs_residual=final_result.max_abs_residual,
        state=final_result.state,
        history=global_history,
        metadata={
            "solver": "alpha_continuation_scipy_root",
            "inner_solver": "scipy_root",
            "scipy_method": method,
            "alpha_start": float(alpha_start),
            "alpha_end": float(alpha_end),
            "alpha_steps": int(alpha_steps),
            "alpha_values": [float(value) for value in alpha_values],
            "use_jacobian": bool(use_jacobian),
            "derivative_mode": derivative_mode,
        },
    )
