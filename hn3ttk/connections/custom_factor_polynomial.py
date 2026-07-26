from __future__ import annotations

from math import copysign, isfinite
from typing import Any, ClassVar

from hn3ttk.connections.base import Connection


class CustomFactorPolynomialConnection(Connection):
    """
    Custom factor polynomial hydraulic connection.

    The model evaluates a custom signed power expansion:

        ΔH = -Σ ai * sign(Q) * |Q|^ni

    where:
        ai > 0
        ni > 0

    This gives passive dissipative behaviour:

        q > 0  ->  delta_h < 0
        q < 0  ->  delta_h > 0

    This model is useful for custom empirical laws such as:

        ΔH = -(a1*Q + a2*Q|Q| + a3*sign(Q)*|Q|^n)

    Expected ``parameters`` keys
    ----------------------------
    - ``coefficients``:
      positive polynomial coefficients. Required.
    - ``exponents``:
      positive exponents associated with each coefficient. Required.
    - ``head_tolerance``:
      near-zero threshold for inversion. Default: ``1.0e-12``.
    - ``inverse_relative_tolerance``:
      tolerance for the inverse solve. Default: ``1.0e-10``.
    - ``inverse_max_iterations``:
      maximum inverse iterations. Default: ``100``.
    - ``minimum_flow_rate``:
      minimum positive flow magnitude used internally near zero.
    """

    type: ClassVar[str] = "custom_factor_polynomial"

    def __post_init__(self) -> None:
        super().__post_init__()
        self._rebuild_model()

    # ------------------------------------------------------------------
    # Mandatory public Connection API
    # ------------------------------------------------------------------

    def head_loss(self, q: float) -> float:
        """
        Return signed head variation ΔH for signed flow rate q.
        """
        q = float(q)

        if q == 0.0:
            return 0.0

        magnitude = self._head_loss_magnitude(abs(q))
        return -copysign(magnitude, q)

    def flow_rate(self, delta_h: float) -> float:
        """
        Return signed flow rate q for signed head variation delta_h.

        For passive elements:
            delta_h < 0 -> q > 0
            delta_h > 0 -> q < 0
        """
        delta_h = float(delta_h)

        if abs(delta_h) <= self._head_tolerance():
            return 0.0

        q_abs = self._solve_positive_flow_rate(abs(delta_h))

        return -copysign(q_abs, delta_h)

    def head_loss_derivative(self, q: float) -> float:
        """
        Return d(ΔH)/dQ evaluated at q.
        """
        q = float(q)

        if q == 0.0:
            return self._head_loss_derivative_at_zero()

        q_abs = abs(q)

        derivative_magnitude = 0.0

        for coefficient, exponent in zip(self._coefficients, self._exponents):
            derivative_magnitude += (
                coefficient * exponent * q_abs ** (exponent - 1.0)
            )

        return -derivative_magnitude

    def flow_rate_derivative(self, delta_h: float) -> float:
        """
        Return dQ/d(ΔH) evaluated at delta_h.
        """
        delta_h = float(delta_h)

        if abs(delta_h) <= self._head_tolerance():
            slope = self.head_loss_derivative(0.0)
        else:
            q = self.flow_rate(delta_h)
            slope = self.head_loss_derivative(q)

        if slope == 0.0:
            return float("-inf")

        return 1.0 / slope

    def validate(self) -> None:
        """Validate polynomial-term arrays, defaults and positivity rules."""
        super().validate()

        required_parameters = [
            "coefficients",
            "exponents",
        ]

        for name in required_parameters:
            if name not in self.parameters:
                raise ValueError(
                    f"CustomFactorPolynomialConnection requires parameter '{name}'."
                )

        default_parameters = {
            "head_tolerance": 1.0e-12,
            "inverse_relative_tolerance": 1.0e-10,
            "inverse_max_iterations": 100,
            "minimum_flow_rate": 1.0e-12,
        }

        for name, default_value in default_parameters.items():
            self.parameters.setdefault(name, default_value)

        coefficients = self._validate_numeric_sequence("coefficients")
        exponents = self._validate_numeric_sequence("exponents")

        if len(coefficients) != len(exponents):
            raise ValueError(
                "'coefficients' and 'exponents' must have the same length."
            )

        if len(coefficients) < 1:
            raise ValueError("At least one coefficient/exponent term is required.")

        for coefficient in coefficients:
            if coefficient <= 0.0:
                raise ValueError("All coefficients must be positive.")

        for exponent in exponents:
            if exponent <= 0.0:
                raise ValueError("All exponents must be positive.")

        self.parameters["coefficients"] = coefficients
        self.parameters["exponents"] = exponents

        self._validate_finite_float("head_tolerance")
        self._validate_finite_float("inverse_relative_tolerance")
        self._validate_finite_float("minimum_flow_rate")

        if self._head_tolerance() <= 0.0:
            raise ValueError("Parameter 'head_tolerance' must be positive.")

        if self._inverse_relative_tolerance() < 0.0:
            raise ValueError(
                "Parameter 'inverse_relative_tolerance' cannot be negative."
            )

        if self._minimum_flow_rate() <= 0.0:
            raise ValueError("Parameter 'minimum_flow_rate' must be positive.")

        inverse_max_iterations = self.parameters["inverse_max_iterations"]

        if not isinstance(inverse_max_iterations, int):
            raise TypeError("Parameter 'inverse_max_iterations' must be an integer.")

        if inverse_max_iterations <= 0:
            raise ValueError("Parameter 'inverse_max_iterations' must be positive.")

    def model_info(self) -> dict[str, Any]:
        """Return a machine-readable summary of the custom polynomial model."""
        return {
            "type": self.type,
            "equation": "ΔH = -Σ ai * sign(Q) * |Q|^ni",
            "parameters": [
                "coefficients",
                "exponents",
                "head_tolerance",
                "inverse_relative_tolerance",
                "inverse_max_iterations",
                "minimum_flow_rate",
                "jacobian_derivative",
                "jacobian_derivative_step",
                "jacobian_derivative_absolute_step",
            ],
            "description": (
                "Custom passive hydraulic connection based on a sum of signed "
                "power-law factors."
            ),
        }

    # ------------------------------------------------------------------
    # Public custom-term API
    # ------------------------------------------------------------------

    def get_terms(self) -> tuple[list[float], list[float]]:
        """
        Return copies of the current polynomial terms.

        Returns
        -------
        tuple[list[float], list[float]]
            coefficients, exponents
        """
        return (
            list(self.parameters["coefficients"]),
            list(self.parameters["exponents"]),
        )

    def set_terms(
        self,
        coefficients: list[float],
        exponents: list[float],
    ) -> None:
        """Replace all polynomial terms and rebuild the model."""
        self.parameters["coefficients"] = list(coefficients)
        self.parameters["exponents"] = list(exponents)

        self.validate()
        self._rebuild_model()

    def add_term(self, coefficient: float, exponent: float) -> None:
        """Add one polynomial factor and rebuild the model."""
        coefficients, exponents = self.get_terms()

        coefficients.append(float(coefficient))
        exponents.append(float(exponent))

        self.set_terms(coefficients, exponents)

    def remove_term(self, index: int) -> None:
        """
        Remove one polynomial factor by index and rebuild the model.
        """
        coefficients, exponents = self.get_terms()

        if not isinstance(index, int):
            raise TypeError("Term index must be an integer.")

        if index < 0 or index >= len(coefficients):
            raise IndexError("Term index out of range.")

        if len(coefficients) <= 1:
            raise ValueError("Cannot remove term: at least one term is required.")

        coefficients.pop(index)
        exponents.pop(index)

        self.set_terms(coefficients, exponents)

    def get_coefficients(self) -> list[float]:
        """
        Return a copy of the coefficients.
        """
        return list(self.parameters["coefficients"])

    def get_exponents(self) -> list[float]:
        """
        Return a copy of the exponents.
        """
        return list(self.parameters["exponents"])

    def sample(
        self,
        q_min: float,
        q_max: float,
        n: int,
    ) -> dict[str, list[float]]:
        """
        Sample the custom polynomial curve.
        """
        q_min = float(q_min)
        q_max = float(q_max)

        if not isinstance(n, int):
            raise TypeError("Sample count 'n' must be an integer.")

        if n < 2:
            raise ValueError("Sample count 'n' must be at least 2.")

        if q_max <= q_min:
            raise ValueError("'q_max' must be greater than 'q_min'.")

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
        Cache coefficients and exponents.

        This method must be called every time the terms change.
        """
        self._coefficients = list(self.parameters["coefficients"])
        self._exponents = list(self.parameters["exponents"])

    # ------------------------------------------------------------------
    # Internal hydraulic helpers
    # ------------------------------------------------------------------

    def _head_loss_magnitude(self, q_abs: float) -> float:
        """
        Return positive head-loss magnitude for q_abs >= 0.
        """
        q_abs = float(q_abs)

        if q_abs == 0.0:
            return 0.0

        value = 0.0

        for coefficient, exponent in zip(self._coefficients, self._exponents):
            value += coefficient * q_abs**exponent

        return value

    def _solve_positive_flow_rate(self, target_head_loss: float) -> float:
        """
        Solve head_loss_magnitude(q) = target_head_loss for q >= 0.
        """
        target_head_loss = float(target_head_loss)

        if target_head_loss <= self._head_tolerance():
            return 0.0

        low = 0.0
        high = self._initial_upper_flow_bound(target_head_loss)

        for _ in range(self._inverse_max_iterations()):
            if self._head_loss_magnitude(high) >= target_head_loss:
                break

            high *= 2.0
        else:
            raise RuntimeError(
                "Could not bracket flow rate for the requested head variation."
            )

        absolute_tolerance = self._head_tolerance()
        relative_tolerance = self._inverse_relative_tolerance()

        for _ in range(self._inverse_max_iterations()):
            mid = 0.5 * (low + high)
            h_mid = self._head_loss_magnitude(mid)

            error = h_mid - target_head_loss

            if abs(error) <= max(
                absolute_tolerance,
                relative_tolerance * target_head_loss,
            ):
                return mid

            if h_mid < target_head_loss:
                low = mid
            else:
                high = mid

        return 0.5 * (low + high)

    def _initial_upper_flow_bound(self, target_head_loss: float) -> float:
        """
        Build an initial positive upper flow-rate bound.
        """
        smallest_coefficient = min(self._coefficients)
        smallest_exponent = min(self._exponents)

        q_estimate = (target_head_loss / smallest_coefficient) ** (
            1.0 / smallest_exponent
        )

        return max(
            q_estimate,
            self._minimum_flow_rate(),
        )

    def _head_loss_derivative_at_zero(self) -> float:
        """
        Return d(ΔH)/dQ at Q = 0 when mathematically defined.

        For one term:
            d/dQ [-a * sign(Q) * |Q|^n]

        At Q = 0:
            n = 1  -> contribution = -a
            n > 1  -> contribution = 0
            n < 1  -> singular negative infinite derivative
        """
        derivative = 0.0

        for coefficient, exponent in zip(self._coefficients, self._exponents):
            if exponent < 1.0:
                return float("-inf")

            if exponent == 1.0:
                derivative -= coefficient

        return derivative

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

    # ------------------------------------------------------------------
    # Parameter accessors
    # ------------------------------------------------------------------

    def _head_tolerance(self) -> float:
        return float(self.parameters["head_tolerance"])

    def _inverse_relative_tolerance(self) -> float:
        return float(self.parameters["inverse_relative_tolerance"])

    def _inverse_max_iterations(self) -> int:
        return int(self.parameters["inverse_max_iterations"])

    def _minimum_flow_rate(self) -> float:
        return float(self.parameters["minimum_flow_rate"])
