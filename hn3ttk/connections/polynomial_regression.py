from __future__ import annotations

from math import isfinite
from typing import Any, ClassVar

import numpy as np

from hn3ttk.connections.base import Connection


class PolynomialRegressionConnection(Connection):
    """
    Polynomial regression hydraulic connection.

    The model fits a polynomial relation from tabulated data:

        Q -> ΔH

    After creation, the polynomial coefficients are computed in _rebuild_model().
    If the tabulation is modified, the polynomial is recalculated.

    Expected convention for passive elements:
        q > 0  ->  delta_h < 0
        q < 0  ->  delta_h > 0

    This class does not enforce passive behaviour. It only fits the provided
    data.

    Expected ``parameters`` keys
    ----------------------------
    - ``flow_rates``:
      sampled flow-rate values. Required.
    - ``head_losses``:
      sampled head-variation values. Required.
    - ``degree``:
      polynomial degree. Default: ``1``.
    - ``extrapolate``:
      whether values outside the sampled range are allowed. Default: ``True``.
    - ``inverse_scan_points``:
      scan density used to bracket inverse solutions.
    - ``inverse_max_iterations``:
      maximum inverse iterations.
    - ``head_tolerance`` and ``flow_tolerance``:
      small tolerances used by the inverse solve.
    """

    type: ClassVar[str] = "polynomial_regression"

    def __post_init__(self) -> None:
        super().__post_init__()
        self._rebuild_model()

    # ------------------------------------------------------------------
    # Mandatory public Connection API
    # ------------------------------------------------------------------

    def head_loss(self, q: float) -> float:
        """
        Return polynomial head variation ΔH for flow rate q.
        """
        q = float(q)
        self._check_flow_range(q)
        return float(np.polyval(self._coefficients, q))

    def flow_rate(self, delta_h: float) -> float:
        """
        Return flow rate q for a given head variation delta_h.

        The inverse polynomial relation is solved numerically.
        """
        delta_h = float(delta_h)

        q_left, q_right = self._find_inverse_bracket(delta_h)

        if q_left == q_right:
            return q_left

        return self._bisect_inverse(
            delta_h=delta_h,
            q_left=q_left,
            q_right=q_right,
        )

    def head_loss_derivative(self, q: float) -> float:
        """
        Return d(ΔH)/dQ evaluated at q.
        """
        q = float(q)
        self._check_flow_range(q)
        return float(np.polyval(self._derivative_coefficients, q))

    def flow_rate_derivative(self, delta_h: float) -> float:
        """
        Return dQ/d(ΔH) evaluated at delta_h.
        """
        q = self.flow_rate(delta_h)
        slope = self.head_loss_derivative(q)

        if slope == 0.0:
            return float("inf")

        return 1.0 / slope

    def validate(self) -> None:
        """Validate tabulation data, regression degree and inverse settings."""
        super().validate()

        required_parameters = [
            "flow_rates",
            "head_losses",
        ]

        for name in required_parameters:
            if name not in self.parameters:
                raise ValueError(
                    f"PolynomialRegressionConnection requires parameter '{name}'."
                )

        default_parameters = {
            "degree": 1,
            "extrapolate": True,
            "inverse_scan_points": 200,
            "inverse_max_iterations": 100,
            "head_tolerance": 1.0e-12,
            "flow_tolerance": 1.0e-12,
        }

        for name, default_value in default_parameters.items():
            self.parameters.setdefault(name, default_value)

        if not isinstance(self.parameters["degree"], int):
            raise TypeError("Parameter 'degree' must be an integer.")

        if self.parameters["degree"] < 1:
            raise ValueError("Parameter 'degree' must be at least 1.")

        if not isinstance(self.parameters["extrapolate"], bool):
            raise TypeError("Parameter 'extrapolate' must be a boolean.")

        if not isinstance(self.parameters["inverse_scan_points"], int):
            raise TypeError("Parameter 'inverse_scan_points' must be an integer.")

        if self.parameters["inverse_scan_points"] < 2:
            raise ValueError("Parameter 'inverse_scan_points' must be at least 2.")

        if not isinstance(self.parameters["inverse_max_iterations"], int):
            raise TypeError("Parameter 'inverse_max_iterations' must be an integer.")

        if self.parameters["inverse_max_iterations"] < 1:
            raise ValueError("Parameter 'inverse_max_iterations' must be positive.")

        flow_rates = self._validate_numeric_sequence("flow_rates")
        head_losses = self._validate_numeric_sequence("head_losses")

        if len(flow_rates) != len(head_losses):
            raise ValueError(
                "'flow_rates' and 'head_losses' must have the same length."
            )

        if len(flow_rates) < 2:
            raise ValueError("At least two tabulated points are required.")

        if self.parameters["degree"] >= len(flow_rates):
            raise ValueError(
                "Polynomial degree must be lower than the number of data points."
            )

        if len(set(flow_rates)) != len(flow_rates):
            raise ValueError("'flow_rates' values must be distinct.")

        if len(set(head_losses)) < 2:
            raise ValueError("'head_losses' must contain at least two distinct values.")

        self.parameters["flow_rates"] = flow_rates
        self.parameters["head_losses"] = head_losses

        self._validate_finite_float("head_tolerance")
        self._validate_finite_float("flow_tolerance")

        if self._head_tolerance() <= 0.0:
            raise ValueError("Parameter 'head_tolerance' must be positive.")

        if self._flow_tolerance() <= 0.0:
            raise ValueError("Parameter 'flow_tolerance' must be positive.")

    def model_info(self) -> dict[str, Any]:
        """Return a machine-readable summary of the regression model."""
        return {
            "type": self.type,
            "equation": "Polynomial regression of Q -> ΔH",
            "parameters": [
                "flow_rates",
                "head_losses",
                "degree",
                "extrapolate",
                "inverse_scan_points",
                "inverse_max_iterations",
                "head_tolerance",
                "flow_tolerance",
                "jacobian_derivative",
                "jacobian_derivative_step",
                "jacobian_derivative_absolute_step",
            ],
            "description": (
                "Hydraulic connection fitted using polynomial regression from "
                "flow-rate and head-variation samples."
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
        """Replace the whole tabulation and rebuild the polynomial model."""
        self.parameters["flow_rates"] = list(flow_rates)
        self.parameters["head_losses"] = list(head_losses)

        self.validate()
        self._rebuild_model()

    def add_point(self, flow_rate: float, head_loss: float) -> None:
        """
        Add one tabulated point and rebuild the polynomial model.
        """
        flow_rates, head_losses = self.get_tabulation()

        flow_rates.append(float(flow_rate))
        head_losses.append(float(head_loss))

        self.set_tabulation(flow_rates, head_losses)

    def remove_point(self, index: int) -> None:
        """
        Remove one tabulated point by index and rebuild the polynomial model.
        """
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

    def get_coefficients(self) -> list[float]:
        """
        Return polynomial coefficients in NumPy order.

        Coefficients are ordered from highest degree to constant term.
        """
        return [float(value) for value in self._coefficients]

    def sample(self, n: int) -> dict[str, list[float]]:
        """
        Sample the fitted polynomial using n equally spaced flow-rate values.
        """
        if not isinstance(n, int):
            raise TypeError("Sample count 'n' must be an integer.")

        if n < 2:
            raise ValueError("Sample count 'n' must be at least 2.")

        q_min = self._flow_min
        q_max = self._flow_max

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
        Sort tabulated data and compute polynomial coefficients.

        This method must be called every time the tabulation or degree changes.
        """
        flow_rates = list(self.parameters["flow_rates"])
        head_losses = list(self.parameters["head_losses"])

        sorted_pairs = sorted(zip(flow_rates, head_losses), key=lambda pair: pair[0])

        self._flow_rates = [pair[0] for pair in sorted_pairs]
        self._head_losses = [pair[1] for pair in sorted_pairs]

        self.parameters["flow_rates"] = list(self._flow_rates)
        self.parameters["head_losses"] = list(self._head_losses)

        self._flow_min = self._flow_rates[0]
        self._flow_max = self._flow_rates[-1]

        degree = self._degree()

        self._coefficients = np.polyfit(
            self._flow_rates,
            self._head_losses,
            degree,
        )

        self._derivative_coefficients = np.polyder(self._coefficients)

    # ------------------------------------------------------------------
    # Inverse relation helpers
    # ------------------------------------------------------------------

    def _find_inverse_bracket(self, delta_h: float) -> tuple[float, float]:
        """
        Find a bracket [q_left, q_right] such that:

            head_loss(q) - delta_h = 0

        has a root inside the interval.
        """
        q_left = self._flow_min
        q_right = self._flow_max

        bracket = self._scan_bracket(delta_h, q_left, q_right)

        if bracket is not None:
            return bracket

        if not self._extrapolate():
            raise ValueError(
                "Could not invert polynomial inside the tabulated flow-rate range."
            )

        span = max(q_right - q_left, self._flow_tolerance())

        for _ in range(self._inverse_max_iterations()):
            q_left -= span
            q_right += span
            span *= 2.0

            bracket = self._scan_bracket(delta_h, q_left, q_right)

            if bracket is not None:
                return bracket

        raise RuntimeError("Could not bracket the inverse polynomial relation.")

    def _scan_bracket(
        self,
        delta_h: float,
        q_left: float,
        q_right: float,
    ) -> tuple[float, float] | None:
        """
        Scan a flow-rate interval looking for a sign-changing bracket.
        """
        scan_points = self._inverse_scan_points()

        previous_q = q_left
        previous_value = self._inverse_residual(previous_q, delta_h)

        if abs(previous_value) <= self._head_tolerance():
            return previous_q, previous_q

        for index in range(1, scan_points):
            q = q_left + (q_right - q_left) * index / (scan_points - 1)
            value = self._inverse_residual(q, delta_h)

            if abs(value) <= self._head_tolerance():
                return q, q

            if previous_value * value < 0.0:
                return previous_q, q

            previous_q = q
            previous_value = value

        return None

    def _bisect_inverse(
        self,
        delta_h: float,
        q_left: float,
        q_right: float,
    ) -> float:
        """
        Solve the inverse relation by bisection once a bracket is known.
        """
        left_value = self._inverse_residual(q_left, delta_h)
        right_value = self._inverse_residual(q_right, delta_h)

        if abs(left_value) <= self._head_tolerance():
            return q_left

        if abs(right_value) <= self._head_tolerance():
            return q_right

        if left_value * right_value > 0.0:
            raise RuntimeError("Invalid inverse bracket.")

        for _ in range(self._inverse_max_iterations()):
            q_mid = 0.5 * (q_left + q_right)
            mid_value = self._inverse_residual(q_mid, delta_h)

            if abs(mid_value) <= self._head_tolerance():
                return q_mid

            if abs(q_right - q_left) <= self._flow_tolerance():
                return q_mid

            if left_value * mid_value < 0.0:
                q_right = q_mid
                right_value = mid_value
            else:
                q_left = q_mid
                left_value = mid_value

        return 0.5 * (q_left + q_right)

    def _inverse_residual(self, q: float, delta_h: float) -> float:
        """
        Return residual for inverse calculation.
        """
        return float(np.polyval(self._coefficients, q)) - delta_h

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

    def _validate_finite_float(self, name: str) -> None:
        """
        Validate that a parameter exists and is a finite numeric value.
        """
        if name not in self.parameters:
            raise ValueError(f"Missing parameter '{name}'.")

        value = self.parameters[name]

        if not isinstance(value, (int, float)):
            raise TypeError(f"Parameter '{name}' must be numeric.")

        if not isfinite(float(value)):
            raise ValueError(f"Parameter '{name}' must be finite.")

        self.parameters[name] = float(value)

    def _check_flow_range(self, q: float) -> None:
        """
        Check if q is inside the tabulated range when extrapolation is disabled.
        """
        if self._extrapolate():
            return

        if q < self._flow_min or q > self._flow_max:
            raise ValueError("Flow rate is outside the fitted tabulation range.")

    # ------------------------------------------------------------------
    # Parameter accessors
    # ------------------------------------------------------------------

    def _degree(self) -> int:
        return int(self.parameters["degree"])

    def _extrapolate(self) -> bool:
        return bool(self.parameters["extrapolate"])

    def _inverse_scan_points(self) -> int:
        return int(self.parameters["inverse_scan_points"])

    def _inverse_max_iterations(self) -> int:
        return int(self.parameters["inverse_max_iterations"])

    def _head_tolerance(self) -> float:
        return float(self.parameters["head_tolerance"])

    def _flow_tolerance(self) -> float:
        return float(self.parameters["flow_tolerance"])
