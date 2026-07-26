from __future__ import annotations

from math import copysign, isfinite
from typing import Any, ClassVar

from hn3ttk.connections.base import Connection


class PipeFixedPowerLaw(Connection):
    """
    Fixed power-law pipe model.

    The model evaluates the signed head variation as:

        ΔH = -k * sign(Q) * |Q|^n

    where:
        k = fixed power-law coefficient
        n = fixed power-law exponent
        Q = flow rate [m³/s]

    Sign convention:
        q > 0 gives delta_h < 0 because passive pipes dissipate energy.
        q < 0 gives delta_h > 0.

    Expected ``parameters`` keys
    ----------------------------
    - ``k``:
      positive power-law coefficient. Required.
    - ``n``:
      positive power-law exponent. Required.
    - ``head_tolerance``:
      small threshold used when inverting near zero head loss.
    """

    type: ClassVar[str] = "pipe_fixed_power_law"

    # ------------------------------------------------------------------
    # Mandatory public Connection API
    # ------------------------------------------------------------------

    def head_loss(self, q: float) -> float:
        """
        Return signed head variation ΔH for signed flow rate q.

        Convention:
            q > 0 -> ΔH < 0
            q < 0 -> ΔH > 0

        Returns
        -------
        float
            Signed head variation in meters.
        """
        q = float(q)

        if q == 0.0:
            return 0.0

        return -copysign(self._k() * abs(q) ** self._n(), q)

    def flow_rate(self, delta_h: float) -> float:
        """
        Return signed flow rate q for a signed head variation delta_h.

        Convention:
            delta_h < 0 -> q > 0
            delta_h > 0 -> q < 0

        Returns
        -------
        float
            Signed flow rate in m3/s.
        """
        delta_h = float(delta_h)

        if abs(delta_h) <= self._head_tolerance():
            return 0.0

        q_abs = (abs(delta_h) / self._k()) ** (1.0 / self._n())

        return -copysign(q_abs, delta_h)

    def head_loss_derivative(self, q: float) -> float:
        """Return ``d(ΔH)/dQ`` evaluated at the requested flow rate."""
        q = float(q)
        k = self._k()
        n = self._n()

        if q == 0.0:
            if n == 1.0:
                return -k

            if n > 1.0:
                return 0.0

            return float("-inf")

        return -k * n * abs(q) ** (n - 1.0)

    def flow_rate_derivative(self, delta_h: float) -> float:
        """Return ``dQ/d(ΔH)`` evaluated at the requested head variation."""
        delta_h = float(delta_h)
        k = self._k()
        n = self._n()

        if abs(delta_h) <= self._head_tolerance():
            if n == 1.0:
                return -1.0 / k

            if n > 1.0:
                return float("-inf")

            return 0.0

        return (
            -(1.0 / n)
            * (1.0 / k) ** (1.0 / n)
            * abs(delta_h) ** ((1.0 / n) - 1.0)
        )

    def validate(self) -> None:
        """Validate required keys, defaults and positivity constraints."""
        super().validate()

        required_parameters = [
            "k",
            "n",
        ]

        for name in required_parameters:
            if name not in self.parameters:
                raise ValueError(
                    f"PipeFixedPowerLaw requires parameter '{name}'."
                )

        default_parameters = {
            "head_tolerance": 1.0e-12,
        }

        for name, default_value in default_parameters.items():
            self.parameters.setdefault(name, default_value)

        float_parameters = [
            "k",
            "n",
            "head_tolerance",
        ]

        for name in float_parameters:
            self._validate_finite_float(name)

        if self._k() <= 0.0:
            raise ValueError("Parameter 'k' must be positive.")

        if self._n() <= 0.0:
            raise ValueError("Parameter 'n' must be positive.")

        if self._head_tolerance() <= 0.0:
            raise ValueError("Parameter 'head_tolerance' must be positive.")

    def model_info(self) -> dict[str, Any]:
        """Return a machine-readable summary of the fixed power-law model."""
        return {
            "type": self.type,
            "equation": "ΔH = -k * sign(Q) * |Q|^n",
            "parameters": [
                "k",
                "n",
                "head_tolerance",
                "jacobian_derivative",
                "jacobian_derivative_step",
                "jacobian_derivative_absolute_step",
            ],
            "description": (
                "Fixed power-law pipe connection with constant k and n. "
                "Positive flow produces negative head variation."
            ),
        }

    # ------------------------------------------------------------------
    # Parameter validation
    # ------------------------------------------------------------------

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
    # Canonical parameter accessors
    # ------------------------------------------------------------------

    def _k(self) -> float:
        return float(self.parameters["k"])

    def _n(self) -> float:
        return float(self.parameters["n"])

    def _head_tolerance(self) -> float:
        return float(self.parameters["head_tolerance"])
