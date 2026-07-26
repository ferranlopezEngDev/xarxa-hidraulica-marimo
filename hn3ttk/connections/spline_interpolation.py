from __future__ import annotations

from math import isfinite
from typing import Any, ClassVar

from scipy.interpolate import CubicSpline, PchipInterpolator

from hn3ttk.connections.base import Connection


class SplineInterpolationConnection(Connection):
    """
    Spline-based tabulated hydraulic connection.

    The model stores a tabulated relation between flow rate and head variation:

        Q -> ΔH

    and builds an internal interpolation model during __post_init__.

    Supported interpolation methods:
        - "pchip": monotonicity-preserving cubic interpolation
        - "cubic_spline": classical cubic spline interpolation

    Recommended method for hydraulic curves:
        "pchip"

    Expected convention for passive elements:
        q > 0  ->  delta_h < 0
        q < 0  ->  delta_h > 0

    This class does not enforce passive behaviour. It only requires the curve
    to be invertible, so head_losses must be strictly monotonic.

    Expected ``parameters`` keys
    ----------------------------
    - ``flow_rates``:
      sampled flow-rate values. Required.
    - ``head_losses``:
      sampled head-variation values. Required.
    - ``method``:
      interpolation family, either ``"pchip"`` or ``"cubic_spline"``.
    - ``extrapolate``:
      whether values outside the sampled range are allowed. Default: ``True``.
    """

    type: ClassVar[str] = "spline_interpolation"

    def __post_init__(self) -> None:
        super().__post_init__()
        self._rebuild_model()

    # ------------------------------------------------------------------
    # Mandatory public Connection API
    # ------------------------------------------------------------------

    def head_loss(self, q: float) -> float:
        """
        Return interpolated head variation ΔH for flow rate q.
        """
        q = float(q)
        self._check_range(q, self._flow_rates, "Flow rate")

        return float(self._forward_interpolator(q))

    def flow_rate(self, delta_h: float) -> float:
        """
        Return interpolated flow rate q for head variation delta_h.
        """
        delta_h = float(delta_h)
        self._check_range(delta_h, self._inverse_head_losses, "Head variation")

        return float(self._inverse_interpolator(delta_h))

    def head_loss_derivative(self, q: float) -> float:
        """
        Return d(ΔH)/dQ evaluated at q.
        """
        q = float(q)
        self._check_range(q, self._flow_rates, "Flow rate")

        return float(self._forward_derivative(q))

    def flow_rate_derivative(self, delta_h: float) -> float:
        """
        Return dQ/d(ΔH) evaluated at delta_h.
        """
        delta_h = float(delta_h)
        self._check_range(delta_h, self._inverse_head_losses, "Head variation")

        return float(self._inverse_derivative(delta_h))

    def validate(self) -> None:
        """Validate tabulation data, interpolation method and constraints."""
        super().validate()

        required_parameters = [
            "flow_rates",
            "head_losses",
        ]

        for name in required_parameters:
            if name not in self.parameters:
                raise ValueError(
                    f"SplineInterpolationConnection requires parameter '{name}'."
                )

        default_parameters = {
            "method": "pchip",
            "extrapolate": True,
        }

        for name, default_value in default_parameters.items():
            self.parameters.setdefault(name, default_value)

        if self.parameters["method"] not in ("pchip", "cubic_spline"):
            raise ValueError(
                "Parameter 'method' must be either 'pchip' or 'cubic_spline'."
            )

        if not isinstance(self.parameters["extrapolate"], bool):
            raise TypeError("Parameter 'extrapolate' must be a boolean.")

        flow_rates = self._validate_numeric_sequence("flow_rates")
        head_losses = self._validate_numeric_sequence("head_losses")

        if len(flow_rates) != len(head_losses):
            raise ValueError(
                "'flow_rates' and 'head_losses' must have the same length."
            )

        if len(flow_rates) < 2:
            raise ValueError("At least two tabulated points are required.")

        if self.parameters["method"] == "cubic_spline" and len(flow_rates) < 3:
            raise ValueError(
                "At least three points are recommended/required for cubic_spline."
            )

        self.parameters["flow_rates"] = flow_rates
        self.parameters["head_losses"] = head_losses

    def model_info(self) -> dict[str, Any]:
        """Return a machine-readable summary of the spline model."""
        return {
            "type": self.type,
            "equation": "Spline interpolation of Q -> ΔH",
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
                "between flow-rate and head-variation samples."
            ),
        }

    # ------------------------------------------------------------------
    # Public tabulation API
    # ------------------------------------------------------------------

    def get_tabulation(self) -> tuple[list[float], list[float]]:
        """
        Return copies of the current tabulated data.
        """
        return (
            list(self.parameters["flow_rates"]),
            list(self.parameters["head_losses"]),
        )

    def set_tabulation(
        self,
        flow_rates: list[float],
        head_losses: list[float],
    ) -> None:
        """Replace the whole tabulation and rebuild the spline model."""
        self.parameters["flow_rates"] = list(flow_rates)
        self.parameters["head_losses"] = list(head_losses)

        self.validate()
        self._rebuild_model()

    def add_point(self, flow_rate: float, head_loss: float) -> None:
        """Add one tabulated sample and rebuild the spline model."""
        flow_rates, head_losses = self.get_tabulation()

        flow_rates.append(float(flow_rate))
        head_losses.append(float(head_loss))

        self.set_tabulation(flow_rates, head_losses)

    def remove_point(self, index: int) -> None:
        """Remove one tabulated sample by index and rebuild the spline model."""
        flow_rates, head_losses = self.get_tabulation()

        if not isinstance(index, int):
            raise TypeError("Point index must be an integer.")

        if index < 0 or index >= len(flow_rates):
            raise IndexError("Point index out of range.")

        if len(flow_rates) <= 2:
            raise ValueError("Cannot remove point: at least two points are required.")

        flow_rates.pop(index)
        head_losses.pop(index)

        self.set_tabulation(flow_rates, head_losses)

    def get_method(self) -> str:
        """Return the current interpolation method name."""
        return str(self.parameters["method"])

    def set_method(self, method: str) -> None:
        """
        Change interpolation method and rebuild the spline model.
        """
        self.parameters["method"] = method

        self.validate()
        self._rebuild_model()

    def sample(self, n: int) -> dict[str, list[float]]:
        """
        Sample the interpolated curve using n equally spaced flow-rate values.
        """
        if not isinstance(n, int):
            raise TypeError("Sample count 'n' must be an integer.")

        if n < 2:
            raise ValueError("Sample count 'n' must be at least 2.")

        q_min = self._flow_rates[0]
        q_max = self._flow_rates[-1]

        step = (q_max - q_min) / (n - 1)

        flow_rates = [q_min + i * step for i in range(n)]
        head_losses = [self.head_loss(q) for q in flow_rates]

        return {
            "flow_rates": flow_rates,
            "head_losses": head_losses,
        }

    # ------------------------------------------------------------------
    # Internal model building
    # ------------------------------------------------------------------

    def _rebuild_model(self) -> None:
        """
        Sort, validate and build interpolation objects.

        This method must be called every time the tabulation or method changes.
        """
        flow_rates = list(self.parameters["flow_rates"])
        head_losses = list(self.parameters["head_losses"])

        sorted_pairs = sorted(zip(flow_rates, head_losses), key=lambda pair: pair[0])

        self._flow_rates = [pair[0] for pair in sorted_pairs]
        self._head_losses = [pair[1] for pair in sorted_pairs]

        self.parameters["flow_rates"] = list(self._flow_rates)
        self.parameters["head_losses"] = list(self._head_losses)

        self._validate_strictly_increasing(self._flow_rates, "flow_rates")
        self._validate_strictly_monotonic(self._head_losses, "head_losses")

        inverse_pairs = sorted(
            zip(self._head_losses, self._flow_rates),
            key=lambda pair: pair[0],
        )

        self._inverse_head_losses = [pair[0] for pair in inverse_pairs]
        self._inverse_flow_rates = [pair[1] for pair in inverse_pairs]

        self._validate_strictly_increasing(
            self._inverse_head_losses,
            "head_losses",
        )

        self._forward_interpolator = self._build_interpolator(
            self._flow_rates,
            self._head_losses,
        )

        self._inverse_interpolator = self._build_interpolator(
            self._inverse_head_losses,
            self._inverse_flow_rates,
        )

        self._forward_derivative = self._forward_interpolator.derivative()
        self._inverse_derivative = self._inverse_interpolator.derivative()

    def _build_interpolator(
        self,
        x_values: list[float],
        y_values: list[float],
    ):
        """
        Build the selected scipy interpolator.
        """
        method = self._method()
        extrapolate = self._extrapolate()

        if method == "pchip":
            return PchipInterpolator(
                x_values,
                y_values,
                extrapolate=extrapolate,
            )

        if method == "cubic_spline":
            return CubicSpline(
                x_values,
                y_values,
                extrapolate=extrapolate,
            )

        raise RuntimeError(f"Unsupported interpolation method '{method}'.")

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_numeric_sequence(self, name: str) -> list[float]:
        """
        Validate a numeric sequence parameter and return it as a list of floats.
        """
        value = self.parameters[name]

        if not isinstance(value, (list, tuple)):
            raise TypeError(f"Parameter '{name}' must be a list or tuple.")

        normalized_values: list[float] = []

        for item in value:
            if not isinstance(item, (int, float)):
                raise TypeError(f"All values in '{name}' must be numeric.")

            numeric_item = float(item)

            if not isfinite(numeric_item):
                raise ValueError(f"All values in '{name}' must be finite.")

            normalized_values.append(numeric_item)

        return normalized_values

    @staticmethod
    def _validate_strictly_increasing(values: list[float], name: str) -> None:
        """
        Validate that values are strictly increasing.
        """
        for index in range(1, len(values)):
            if values[index] <= values[index - 1]:
                raise ValueError(f"'{name}' values must be strictly increasing.")

    @staticmethod
    def _validate_strictly_monotonic(values: list[float], name: str) -> None:
        """
        Validate that values are strictly increasing or strictly decreasing.
        """
        increasing = all(
            values[index] > values[index - 1]
            for index in range(1, len(values))
        )

        decreasing = all(
            values[index] < values[index - 1]
            for index in range(1, len(values))
        )

        if not increasing and not decreasing:
            raise ValueError(
                f"'{name}' values must be strictly monotonic for inversion."
            )

    def _check_range(
        self,
        value: float,
        values: list[float],
        label: str,
    ) -> None:
        """
        Check interpolation range when extrapolation is disabled.
        """
        if self._extrapolate():
            return

        if value < values[0] or value > values[-1]:
            raise ValueError(f"{label} is outside the tabulated range.")

    # ------------------------------------------------------------------
    # Parameter accessors
    # ------------------------------------------------------------------

    def _method(self) -> str:
        return str(self.parameters["method"])

    def _extrapolate(self) -> bool:
        return bool(self.parameters["extrapolate"])
