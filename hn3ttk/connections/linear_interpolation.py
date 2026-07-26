from __future__ import annotations

from bisect import bisect_left
from math import isfinite
from typing import Any, ClassVar

from hn3ttk.connections.base import Connection


class LinearInterpolationConnection(Connection):
    """
    Linear tabulated hydraulic connection.

    The model stores a tabulated relation between flow rate and head variation:

        Q -> ΔH

    and evaluates intermediate values using piecewise-linear interpolation.

    Expected convention for passive elements:
        q > 0  ->  delta_h < 0
        q < 0  ->  delta_h > 0

    However, this class only requires the tabulated relation to be invertible.
    It does not enforce passive behaviour.

    Expected ``parameters`` keys
    ----------------------------
    - ``flow_rates``:
      list of sampled flow-rate values. Required.
    - ``head_losses``:
      list of sampled head-variation values with the same length as
      ``flow_rates``. Required.
    - ``extrapolate``:
      whether values outside the sampled range are allowed. Default: ``True``.
    """

    type: ClassVar[str] = "linear_interpolation"

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
        return self._interpolate(
            x=float(q),
            x_values=self._flow_rates,
            y_values=self._head_losses,
        )

    def flow_rate(self, delta_h: float) -> float:
        """
        Return interpolated flow rate q for head variation delta_h.
        """
        return self._interpolate(
            x=float(delta_h),
            x_values=self._inverse_head_losses,
            y_values=self._inverse_flow_rates,
        )

    def head_loss_derivative(self, q: float) -> float:
        """
        Return local piecewise-linear derivative d(ΔH)/dQ.
        """
        return self._segment_slope(
            x=float(q),
            x_values=self._flow_rates,
            y_values=self._head_losses,
        )

    def flow_rate_derivative(self, delta_h: float) -> float:
        """
        Return local piecewise-linear derivative dQ/d(ΔH).
        """
        return self._segment_slope(
            x=float(delta_h),
            x_values=self._inverse_head_losses,
            y_values=self._inverse_flow_rates,
        )

    def validate(self) -> None:
        """Validate tabulation lengths, numeric content and extrapolation flag."""
        super().validate()

        required_parameters = [
            "flow_rates",
            "head_losses",
        ]

        for name in required_parameters:
            if name not in self.parameters:
                raise ValueError(
                    f"LinearInterpolationConnection requires parameter '{name}'."
                )

        self.parameters.setdefault("extrapolate", True)

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

        self.parameters["flow_rates"] = flow_rates
        self.parameters["head_losses"] = head_losses

    def model_info(self) -> dict[str, Any]:
        """Return a machine-readable summary of the interpolation model."""
        return {
            "type": self.type,
            "equation": "Piecewise-linear interpolation of Q -> ΔH",
            "parameters": [
                "flow_rates",
                "head_losses",
                "extrapolate",
                "jacobian_derivative",
                "jacobian_derivative_step",
                "jacobian_derivative_absolute_step",
            ],
            "description": (
                "Tabulated hydraulic connection using linear interpolation "
                "between flow-rate and head-variation samples."
            ),
        }

    # ------------------------------------------------------------------
    # Public tabulation API
    # ------------------------------------------------------------------

    def get_tabulation(self) -> tuple[list[float], list[float]]:
        """
        Return copies of the current tabulated data.

        The returned lists are copies, so external modifications do not affect
        the internal model.
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
        """Replace the whole tabulation and rebuild the interpolation model."""
        self.parameters["flow_rates"] = list(flow_rates)
        self.parameters["head_losses"] = list(head_losses)

        self.validate()
        self._rebuild_model()

    def add_point(self, flow_rate: float, head_loss: float) -> None:
        """Add one tabulated sample and rebuild the interpolation model."""
        flow_rates, head_losses = self.get_tabulation()

        flow_rates.append(float(flow_rate))
        head_losses.append(float(head_loss))

        self.set_tabulation(flow_rates, head_losses)

    def remove_point(self, index: int) -> None:
        """Remove one tabulated sample by index and rebuild the model."""
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

    def sample(self, n: int) -> dict[str, list[float]]:
        """Sample the interpolated curve at ``n`` equally spaced flow-rate values."""
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
        Sort, validate and cache the interpolation data.

        This method must be called every time the tabulation changes.
        """
        flow_rates = list(self.parameters["flow_rates"])
        head_losses = list(self.parameters["head_losses"])

        sorted_pairs = sorted(zip(flow_rates, head_losses), key=lambda pair: pair[0])

        self._flow_rates = [pair[0] for pair in sorted_pairs]
        self._head_losses = [pair[1] for pair in sorted_pairs]

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

    # ------------------------------------------------------------------
    # Interpolation helpers
    # ------------------------------------------------------------------

    def _interpolate(
        self,
        x: float,
        x_values: list[float],
        y_values: list[float],
    ) -> float:
        """
        Return linear interpolation or extrapolation.
        """
        if not self.parameters["extrapolate"]:
            if x < x_values[0] or x > x_values[-1]:
                raise ValueError("Interpolation input is outside the tabulated range.")

        index = bisect_left(x_values, x)

        if index == 0:
            if x == x_values[0]:
                return y_values[0]

            left_index = 0
            right_index = 1

        elif index == len(x_values):
            if x == x_values[-1]:
                return y_values[-1]

            left_index = len(x_values) - 2
            right_index = len(x_values) - 1

        elif x_values[index] == x:
            return y_values[index]

        else:
            left_index = index - 1
            right_index = index

        return self._linear_segment_value(
            x=x,
            x0=x_values[left_index],
            x1=x_values[right_index],
            y0=y_values[left_index],
            y1=y_values[right_index],
        )

    def _segment_slope(
        self,
        x: float,
        x_values: list[float],
        y_values: list[float],
    ) -> float:
        """
        Return the slope of the active linear segment.
        """
        if not self.parameters["extrapolate"]:
            if x < x_values[0] or x > x_values[-1]:
                raise ValueError("Derivative input is outside the tabulated range.")

        index = bisect_left(x_values, x)

        if index == 0:
            left_index = 0
            right_index = 1

        elif index >= len(x_values):
            left_index = len(x_values) - 2
            right_index = len(x_values) - 1

        else:
            left_index = index - 1
            right_index = index

        return (
            (y_values[right_index] - y_values[left_index])
            / (x_values[right_index] - x_values[left_index])
        )

    @staticmethod
    def _linear_segment_value(
        x: float,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
    ) -> float:
        """
        Evaluate a linear segment.
        """
        weight = (x - x0) / (x1 - x0)
        return y0 + weight * (y1 - y0)

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
