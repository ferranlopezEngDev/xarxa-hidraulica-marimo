from __future__ import annotations

from typing import Any

import numpy as np

from hn3ttk.solvers.result import SolverResult
from hn3ttk.system import HydraulicSystem


def safe_evaluate_state(
    system: HydraulicSystem,
    unknown_heads: list[float],
    alpha: float,
) -> dict[str, Any] | None:
    """Return system state if it can be evaluated safely."""
    try:
        return system.evaluate_state(unknown_heads, alpha=alpha)
    except Exception:
        return None


def build_solver_result(
    *,
    success: bool,
    message: str,
    iterations: int,
    unknown_heads: list[float],
    residuals: list[float],
    max_abs_residual: float,
    system: HydraulicSystem,
    alpha: float,
    history: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> SolverResult:
    """Build a solver result with safe state evaluation."""
    return SolverResult(
        success=success,
        message=message,
        iterations=iterations,
        unknown_heads=list(unknown_heads),
        residuals=list(residuals),
        max_abs_residual=float(max_abs_residual),
        state=safe_evaluate_state(system, list(unknown_heads), alpha),
        history=history,
        metadata={} if metadata is None else dict(metadata),
    )


def predict_unknown_heads(
    system: HydraulicSystem,
    unknown_heads: list[float],
    alpha: float,
) -> list[float]:
    """
    Build a simple continuation predictor from the residual at the new alpha.

    This keeps continuation logic separate from damping logic while still
    nudging the initial guess away from singular zero-flow anchors.
    """
    x = np.asarray(unknown_heads, dtype=float)
    residual = np.asarray(
        system.nodal_flow_residuals(x.tolist(), alpha=alpha),
        dtype=float,
    )

    if residual.shape != x.shape:
        return x.tolist()

    if not np.all(np.isfinite(residual)):
        return x.tolist()

    predicted_x = x + residual

    if not np.all(np.isfinite(predicted_x)):
        return x.tolist()

    return predicted_x.tolist()
