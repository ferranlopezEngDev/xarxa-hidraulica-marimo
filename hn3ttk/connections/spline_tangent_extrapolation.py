from __future__ import annotations

from typing import Any, ClassVar

from hn3ttk.connections.spline_interpolation import SplineInterpolationConnection


class SplineTangentExtrapolationConnection(SplineInterpolationConnection):
    """
    Spline-based tabulated hydraulic connection with tangent extrapolation.

    Inside the tabulated range, the model behaves exactly like
    ``SplineInterpolationConnection``.

    Outside the tabulated range, the model does not use the raw spline
    extrapolation. Instead, it extends the curve with the tangent line taken at
    the nearest tabulated endpoint.

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
      whether tangent extrapolation outside the tabulated range is allowed.
      Default: ``True``.
    """

    type: ClassVar[str] = "spline_tangent_extrapolation"

    def head_loss(self, q: float) -> float:
        """Return head variation ΔH for flow rate q."""
        q = float(q)

        return self._evaluate_with_tangent(
            value=q,
            x_values=self._flow_rates,
            interpolator=self._forward_interpolator,
            derivative=self._forward_derivative,
            label="Flow rate",
        )

    def flow_rate(self, delta_h: float) -> float:
        """Return flow rate q for head variation delta_h."""
        delta_h = float(delta_h)

        return self._evaluate_with_tangent(
            value=delta_h,
            x_values=self._inverse_head_losses,
            interpolator=self._inverse_interpolator,
            derivative=self._inverse_derivative,
            label="Head variation",
        )

    def head_loss_derivative(self, q: float) -> float:
        """Return d(ΔH)/dQ evaluated at q."""
        q = float(q)

        return self._evaluate_derivative_with_tangent(
            value=q,
            x_values=self._flow_rates,
            derivative=self._forward_derivative,
            label="Flow rate",
        )

    def flow_rate_derivative(self, delta_h: float) -> float:
        """Return dQ/d(ΔH) evaluated at delta_h."""
        delta_h = float(delta_h)

        return self._evaluate_derivative_with_tangent(
            value=delta_h,
            x_values=self._inverse_head_losses,
            derivative=self._inverse_derivative,
            label="Head variation",
        )

    def model_info(self) -> dict[str, Any]:
        """Return a machine-readable summary of the tangent-extrapolated spline model."""
        return {
            "type": self.type,
            "equation": (
                "Spline interpolation of Q -> ΔH inside the tabulated range, "
                "tangent-line extrapolation outside"
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
                "inside the tabulated domain and tangent-line extrapolation at "
                "the nearest endpoint outside it."
            ),
        }

    def _evaluate_with_tangent(
        self,
        *,
        value: float,
        x_values: list[float],
        interpolator,
        derivative,
        label: str,
    ) -> float:
        if x_values[0] <= value <= x_values[-1]:
            return float(interpolator(value))

        self._check_range(value, x_values, label)

        anchor = x_values[0] if value < x_values[0] else x_values[-1]
        anchor_value = float(interpolator(anchor))
        anchor_slope = float(derivative(anchor))

        return anchor_value + anchor_slope * (value - anchor)

    def _evaluate_derivative_with_tangent(
        self,
        *,
        value: float,
        x_values: list[float],
        derivative,
        label: str,
    ) -> float:
        if x_values[0] <= value <= x_values[-1]:
            return float(derivative(value))

        self._check_range(value, x_values, label)

        anchor = x_values[0] if value < x_values[0] else x_values[-1]

        return float(derivative(anchor))
