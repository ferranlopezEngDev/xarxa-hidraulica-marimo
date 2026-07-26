from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SolverResult:
    """
    Container with the outcome of a hydraulic solve.

    Attributes
    ----------
    success:
        Whether the solve met the convergence criteria.
    message:
        Human-readable convergence or failure message.
    iterations:
        Number of iterations or function evaluations reported by the solver.
    unknown_heads:
        Final unknown-head values in the solver ordering.
    residuals:
        Final nodal residual vector.
    max_abs_residual:
        Maximum absolute value of the final residual vector.
    state:
        Optional evaluated hydraulic state dictionary.
    history:
        Optional iteration history collected by the solver.
    metadata:
        Extra solver-specific metadata.
    """

    success: bool
    message: str
    iterations: int
    unknown_heads: list[float]
    residuals: list[float]
    max_abs_residual: float
    state: dict[str, Any] | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Return a serializable dictionary representation.

        The method converts NumPy scalars, arrays and nested containers to
        plain Python values where possible.
        """

        def to_builtin(value: Any) -> Any:
            if value is None:
                return None

            if isinstance(value, (bool, int, float, str)):
                return value

            if isinstance(value, dict):
                return {
                    str(key): to_builtin(item)
                    for key, item in value.items()
                }

            if isinstance(value, (list, tuple)):
                return [to_builtin(item) for item in value]

            item_method = getattr(value, "item", None)

            if callable(item_method):
                try:
                    return to_builtin(item_method())
                except Exception:
                    pass

            return value

        return {
            "success": bool(self.success),
            "message": str(self.message),
            "iterations": int(self.iterations),
            "unknown_heads": [
                float(value)
                for value in self.unknown_heads
            ],
            "residuals": [
                float(value)
                for value in self.residuals
            ],
            "max_abs_residual": float(self.max_abs_residual),
            "state": to_builtin(self.state),
            "history": to_builtin(self.history),
            "metadata": to_builtin(self.metadata),
        }
