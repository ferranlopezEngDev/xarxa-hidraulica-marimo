from __future__ import annotations

from typing import Any, ClassVar

from hn3ttk.connections.spline_interpolation import SplineInterpolationConnection


class SplineSecantExtrapolationConnection(SplineInterpolationConnection):
    """
    Spline-based tabulated hydraulic connection with secant extrapolation.

    Inside the tabulated range, the model behaves exactly like
    ``SplineInterpolationConnection``.

    Outside the tabulated range, the model does not use the raw spline
    extrapolation. Instead, it extends the curve with the straight line defined
    by the first two tabulated points on the left and the last two tabulated
    points on the right.

    Supported interpolation methods:
        - "pchip"
        - "cubic_spline"

    Expected ``parameters`` keys
    ----------------------------
    - ``flow_rates``:
      sampled flow-rate values. Required.
    - ``head_losses``:
      sampled head-variation values. Required.
    - ``method``:
      interpolation family, either ``"pchip"`` or ``"cubic_spline"``.
    - ``extrapolate``:
      whether secant extrapolation outside the tabulated range is allowed.
      Default: ``True``.
    """

    type: ClassVar[str] = "spline_secant_extrapolation"

    def head_loss(self, q: float) -> float:
        """Return head variation ΔH for flow rate q."""
        q = float(q)

        return self._evaluate_with_secant(
            value=q,
            x_values=self._flow_rates,
            y_values=self._head_losses,
            interpolator=self._forward_interpolator,
            label="Flow rate",
        )

    def flow_rate(self, delta_h: float) -> float:
        """Return flow rate q for head variation delta_h."""
        delta_h = float(delta_h)

        return self._evaluate_with_secant(
            value=delta_h,
            x_values=self._inverse_head_losses,
            y_values=self._inverse_flow_rates,
            interpolator=self._inverse_interpolator,
            label="Head variation",
        )

    def head_loss_derivative(self, q: float) -> float:
        """Return d(ΔH)/dQ evaluated at q."""
        q = float(q)

        return self._evaluate_derivative_with_secant(
            value=q,
            x_values=self._flow_rates,
            y_values=self._head_losses,
            derivative=self._forward_derivative,
            label="Flow rate",
        )

    def flow_rate_derivative(self, delta_h: float) -> float:
        """Return dQ/d(ΔH) evaluated at delta_h."""
        delta_h = float(delta_h)

        return self._evaluate_derivative_with_secant(
            value=delta_h,
            x_values=self._inverse_head_losses,
            y_values=self._inverse_flow_rates,
            derivative=self._inverse_derivative,
            label="Head variation",
        )

    def model_info(self) -> dict[str, Any]:
        """Return a machine-readable summary of the secant-extrapolated spline model."""
        return {
            "type": self.type,
            "equation": (
                "Spline interpolation of Q -> ΔH inside the tabulated range, "
                "secant-line extrapolation outside"
            ),
            "parameters": [
                "flow_rates",
                "head_losses",
                "method",
                "extrapolate",
                "jacobian_derivative",
                "jacobian_derivative_step",
                "jacobian_derivative_absolute_step",
            ],
            "supported_methods": [
                "pchip",
                "cubic_spline",
            ],
            "description": (
                "Tabulated hydraulic connection using spline interpolation "
                "inside the tabulated domain and the boundary secant line "
                "outside it."
            ),
        }

    def _evaluate_with_secant(
        self,
        *,
        value: float,
        x_values: list[float],
        y_values: list[float],
        interpolator,
        label: str,
    ) -> float:
        if x_values[0] <= value <= x_values[-1]:
            return float(interpolator(value))

        self._check_range(value, x_values, label)

        x0, y0, x1, y1 = self._boundary_segment(
            value=value,
            x_values=x_values,
            y_values=y_values,
        )
        slope = self._segment_slope(x0, y0, x1, y1)

        return y0 + slope * (value - x0)

    def _evaluate_derivative_with_secant(
        self,
        *,
        value: float,
        x_values: list[float],
        y_values: list[float],
        derivative,
        label: str,
    ) -> float:
        if x_values[0] <= value <= x_values[-1]:
            return float(derivative(value))

        self._check_range(value, x_values, label)

        x0, y0, x1, y1 = self._boundary_segment(
            value=value,
            x_values=x_values,
            y_values=y_values,
        )

        return self._segment_slope(x0, y0, x1, y1)

    @staticmethod
    def _segment_slope(x0: float, y0: float, x1: float, y1: float) -> float:
        return (y1 - y0) / (x1 - x0)

    @staticmethod
    def _boundary_segment(
        *,
        value: float,
        x_values: list[float],
        y_values: list[float],
    ) -> tuple[float, float, float, float]:
        if value < x_values[0]:
            return x_values[0], y_values[0], x_values[1], y_values[1]

        return x_values[-2], y_values[-2], x_values[-1], y_values[-1]
