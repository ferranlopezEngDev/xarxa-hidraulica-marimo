from __future__ import annotations

from math import copysign, isclose, isfinite, log10, pi
from typing import Any, ClassVar

from hn3ttk.connections.base import Connection


class PipeDarcy(Connection):
    """
    Complete Darcy-Weisbach pipe model.

    The model evaluates the signed head variation directly from Darcy-Weisbach:

        ΔH = -f * 8 * L * Q * |Q| / (g * π² * D⁵)

    where:
        L  = pipe length [m]
        D  = internal diameter [m]
        Q  = flow rate [m³/s]
        g  = gravity [m/s²]
        f  = Darcy friction factor [-]

    Sign convention:
        q > 0 gives delta_h < 0 because passive pipes dissipate energy.

    Expected ``parameters`` keys
    ----------------------------
    Required:
    - ``length`` [m]
    - ``diameter`` [m]
    - ``roughness`` [m]

    Optional:
    - ``kinematic_viscosity`` [m2/s], default ``1.0e-6``
    - ``gravity`` [m/s2], default ``9.81``
    - ``laminar_reynolds``, default ``2000.0``
    - ``turbulent_reynolds``, default ``4000.0``
    - ``head_tolerance``
    - ``inverse_relative_tolerance``
    - ``inverse_max_iterations``
    - ``derivative_relative_step``
    - ``derivative_absolute_step``
    """

    type: ClassVar[str] = "pipe_darcy"

    def head_loss(self, q: float) -> float:
        """Return signed Darcy-Weisbach head variation for signed flow rate ``q``."""
        q = float(q)

        if q == 0.0:
            return 0.0

        return -copysign(self._head_loss_magnitude(abs(q)), q)

    def flow_rate(self, delta_h: float) -> float:
        """
        Return signed flow rate q for a signed head variation delta_h.

        For passive pipes:
            delta_h < 0 gives q > 0.

        Returns
        -------
        float
            Signed flow rate in m3/s.
        """
        delta_h = float(delta_h)

        if abs(delta_h) <= self._head_tolerance():
            return 0.0

        sign = -1.0 if delta_h > 0.0 else 1.0
        q_abs = self._solve_positive_flow_rate(abs(delta_h))

        return sign * q_abs

    def head_loss_derivative(self, q: float) -> float:
        """
        Return d(ΔH)/dQ evaluated at q.

        The derivative is numerical because the friction factor changes with
        Reynolds number and contains a transitional regime.
        """
        q = float(q)

        if q == 0.0:
            return -self._laminar_head_loss_slope()

        step = self._derivative_step(q)

        q_minus = q - step
        q_plus = q + step

        h_minus = self.head_loss(q_minus)
        h_plus = self.head_loss(q_plus)

        return (h_plus - h_minus) / (q_plus - q_minus)

    def flow_rate_derivative(self, delta_h: float) -> float:
        """Return ``dQ/d(ΔH)`` evaluated at the requested head variation."""
        delta_h = float(delta_h)

        if abs(delta_h) <= self._head_tolerance():
            return -1.0 / self._laminar_head_loss_slope()

        q = self.flow_rate(delta_h)
        slope = self.head_loss_derivative(q)

        if slope == 0.0:
            return float("-inf")

        return 1.0 / slope

    def validate(self) -> None:
        """Validate required keys, defaults and physical parameter ranges."""
        super().validate()

        required_parameters = [
            "length",
            "diameter",
            "roughness",
        ]

        for name in required_parameters:
            if name not in self.parameters:
                raise ValueError(f"PipeDarcy requires parameter '{name}'.")

        default_parameters = {
            "kinematic_viscosity": 1.0e-6,
            "gravity": 9.81,
            "laminar_reynolds": 2000.0,
            "turbulent_reynolds": 4000.0,
            "head_tolerance": 1.0e-12,
            "inverse_relative_tolerance": 1.0e-10,
            "inverse_max_iterations": 100,
            "derivative_relative_step": 1.0e-6,
            "derivative_absolute_step": 1.0e-10,
        }

        for name, default_value in default_parameters.items():
            self.parameters.setdefault(name, default_value)

        float_parameters = [
            "length",
            "diameter",
            "roughness",
            "kinematic_viscosity",
            "gravity",
            "laminar_reynolds",
            "turbulent_reynolds",
            "head_tolerance",
            "inverse_relative_tolerance",
            "derivative_relative_step",
            "derivative_absolute_step",
        ]

        for name in float_parameters:
            self._validate_finite_float(name)

        if self._length() <= 0.0:
            raise ValueError("Parameter 'length' must be positive.")

        if self._diameter() <= 0.0:
            raise ValueError("Parameter 'diameter' must be positive.")

        if self._roughness() < 0.0:
            raise ValueError("Parameter 'roughness' cannot be negative.")

        if self._kinematic_viscosity() <= 0.0:
            raise ValueError("Parameter 'kinematic_viscosity' must be positive.")

        if self._gravity() <= 0.0:
            raise ValueError("Parameter 'gravity' must be positive.")

        if self._laminar_reynolds() <= 0.0:
            raise ValueError("Parameter 'laminar_reynolds' must be positive.")

        if self._turbulent_reynolds() <= self._laminar_reynolds():
            raise ValueError(
                "Parameter 'turbulent_reynolds' must be greater than "
                "'laminar_reynolds'."
            )

        if self._head_tolerance() <= 0.0:
            raise ValueError("Parameter 'head_tolerance' must be positive.")

        if self._inverse_relative_tolerance() < 0.0:
            raise ValueError(
                "Parameter 'inverse_relative_tolerance' cannot be negative."
            )

        if self._derivative_relative_step() <= 0.0:
            raise ValueError(
                "Parameter 'derivative_relative_step' must be positive."
            )

        if self._derivative_absolute_step() <= 0.0:
            raise ValueError(
                "Parameter 'derivative_absolute_step' must be positive."
            )

        inverse_max_iterations = self.parameters["inverse_max_iterations"]

        if not isinstance(inverse_max_iterations, int):
            raise TypeError("Parameter 'inverse_max_iterations' must be an integer.")

        if inverse_max_iterations <= 0:
            raise ValueError(
                "Parameter 'inverse_max_iterations' must be positive."
            )

    def model_info(self) -> dict[str, Any]:
        """Return a machine-readable summary of the Darcy-Weisbach model."""
        return {
            "type": self.type,
            "equation": "ΔH = -f * 8 * L * Q * |Q| / (g * π² * D⁵)",
            "reference_model": "Darcy-Weisbach",
            "friction_factor": (
                "64/Re in laminar regime, Swamee-Jain in turbulent regime, "
                "linear interpolation of |ΔH|(Q) in transition"
            ),
            "parameters": [
                "length",
                "diameter",
                "roughness",
                "kinematic_viscosity",
                "gravity",
                "laminar_reynolds",
                "turbulent_reynolds",
                "jacobian_derivative",
                "jacobian_derivative_step",
                "jacobian_derivative_absolute_step",
            ],
            "description": (
                "Pipe connection using the complete Darcy-Weisbach equation "
                "with Reynolds-dependent friction factor."
            ),
        }

    def reynolds_number(self, q: float) -> float:
        """Return Reynolds number for the requested signed flow rate."""
        return self.reynolds_number_from_flow_magnitude(abs(float(q)))

    def reynolds_number_from_flow_magnitude(self, q_abs: float) -> float:
        """Return Reynolds number for a positive flow-rate magnitude."""
        q_abs = float(q_abs)

        if q_abs < 0.0:
            raise ValueError("Flow-rate magnitude cannot be negative.")

        if q_abs == 0.0:
            return 0.0

        area = pi * self._diameter() ** 2 / 4.0
        velocity = q_abs / area

        return velocity * self._diameter() / self._kinematic_viscosity()

    def friction_factor(self, q: float) -> float:
        """
        Return Darcy friction factor for signed flow rate q.
        """
        return self.friction_factor_from_reynolds(self.reynolds_number(q))

    def friction_factor_from_reynolds(self, reynolds: float) -> float:
        """
        Return Darcy friction factor for a Reynolds number.

        Laminar:
            f = 64 / Re

        Turbulent:
            Swamee-Jain explicit approximation

        Transitional:
            effective factor derived from a linear interpolation of the
            transition head-loss curve.
        """
        reynolds = float(reynolds)

        if reynolds <= 0.0:
            return 0.0

        q_abs = self._flow_rate_from_reynolds(reynolds)
        head_loss_magnitude = self._head_loss_magnitude(q_abs)

        return (
            head_loss_magnitude
            * self._gravity()
            * pi**2
            * self._diameter() ** 5
            / (8.0 * self._length() * q_abs**2)
        )

    def flow_regime(self, q: float) -> str:
        """
        Return qualitative flow regime for signed flow rate q.
        """
        return self._flow_regime_from_reynolds(self.reynolds_number(q))

    def _head_loss_magnitude(self, q_abs: float) -> float:
        """
        Return positive Darcy-Weisbach head-loss magnitude for q_abs >= 0.
        """
        q_abs = float(q_abs)

        if q_abs == 0.0:
            return 0.0

        regime = self._flow_regime_from_reynolds(
            self.reynolds_number_from_flow_magnitude(q_abs)
        )

        if regime == "laminar":
            return self._laminar_head_loss_slope() * q_abs

        if regime == "transition":
            return self._transition_head_loss_magnitude(q_abs)

        return self._turbulent_head_loss_magnitude(q_abs)

    def _solve_positive_flow_rate(self, target_head_loss: float) -> float:
        """
        Solve head_loss_magnitude(q) = target_head_loss for q >= 0.
        """
        target_head_loss = float(target_head_loss)

        if target_head_loss <= self._head_tolerance():
            return 0.0

        laminar_head_loss_limit = self._laminar_head_loss_limit()

        if target_head_loss <= laminar_head_loss_limit:
            return target_head_loss / self._laminar_head_loss_slope()

        turbulent_head_loss_limit = self._turbulent_head_loss_limit()

        if target_head_loss <= turbulent_head_loss_limit:
            return self._transition_flow_rate(target_head_loss)

        low = self._turbulent_limit_flow_rate()
        high = max(
            self._initial_upper_flow_bound(target_head_loss),
            low,
        )

        for _ in range(self._inverse_max_iterations()):
            if self._head_loss_magnitude(high) >= target_head_loss:
                break

            high *= 2.0
        else:
            raise RuntimeError(
                "Could not bracket flow rate for the requested head loss."
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
        slope = self._laminar_head_loss_slope()
        q_laminar = target_head_loss / slope

        return max(
            q_laminar,
            self._minimum_flow_bound(),
        )

    def _laminar_head_loss_slope(self) -> float:
        """
        Return exact positive laminar slope magnitude at Q = 0.

        In laminar pipe flow:

            |ΔH| = 128 * ν * L * |Q| / (g * π * D⁴)
        """
        return (
            128.0
            * self._kinematic_viscosity()
            * self._length()
            / (self._gravity() * pi * self._diameter() ** 4)
        )

    def _swamee_jain_friction_factor(self, reynolds: float) -> float:
        """
        Return turbulent Darcy friction factor using Swamee-Jain.
        """
        relative_roughness = self._roughness() / self._diameter()

        return 0.25 / log10(
            relative_roughness / 3.7 + 5.74 / reynolds**0.9
        ) ** 2

    def _turbulent_head_loss_magnitude(self, q_abs: float) -> float:
        """
        Return the turbulent head-loss magnitude from Swamee-Jain.
        """
        reynolds = self.reynolds_number_from_flow_magnitude(q_abs)
        friction_factor = self._swamee_jain_friction_factor(reynolds)

        return (
            friction_factor
            * 8.0
            * self._length()
            * q_abs**2
            / (self._gravity() * pi**2 * self._diameter() ** 5)
        )

    def _transition_head_loss_magnitude(self, q_abs: float) -> float:
        """
        Return the transition head-loss magnitude from a linear Q-|ΔH| segment.
        """
        return self._linear_interpolate(
            x=float(q_abs),
            x0=self._laminar_limit_flow_rate(),
            y0=self._laminar_head_loss_limit(),
            x1=self._turbulent_limit_flow_rate(),
            y1=self._turbulent_head_loss_limit(),
        )

    def _transition_flow_rate(self, target_head_loss: float) -> float:
        """
        Return the transition flow rate from the inverse linear Q-|ΔH| segment.
        """
        return self._linear_interpolate(
            x=float(target_head_loss),
            x0=self._laminar_head_loss_limit(),
            y0=self._laminar_limit_flow_rate(),
            x1=self._turbulent_head_loss_limit(),
            y1=self._turbulent_limit_flow_rate(),
        )

    def _flow_regime_from_reynolds(self, reynolds: float) -> str:
        """
        Classify the flow regime from Reynolds number using closed boundaries.
        """
        reynolds = float(reynolds)

        if reynolds == 0.0:
            return "stagnant"

        if reynolds <= self._laminar_reynolds() or isclose(
            reynolds,
            self._laminar_reynolds(),
            rel_tol=1.0e-12,
            abs_tol=0.0,
        ):
            return "laminar"

        if reynolds >= self._turbulent_reynolds() or isclose(
            reynolds,
            self._turbulent_reynolds(),
            rel_tol=1.0e-12,
            abs_tol=0.0,
        ):
            return "turbulent"

        return "transition"

    def _flow_rate_from_reynolds(self, reynolds: float) -> float:
        """
        Return the positive flow-rate magnitude corresponding to Reynolds.
        """
        return (
            float(reynolds)
            * pi
            * self._diameter()
            * self._kinematic_viscosity()
            / 4.0
        )

    def _laminar_limit_flow_rate(self) -> float:
        return self._flow_rate_from_reynolds(self._laminar_reynolds())

    def _turbulent_limit_flow_rate(self) -> float:
        return self._flow_rate_from_reynolds(self._turbulent_reynolds())

    def _laminar_head_loss_limit(self) -> float:
        return self._laminar_head_loss_slope() * self._laminar_limit_flow_rate()

    def _turbulent_head_loss_limit(self) -> float:
        return self._turbulent_head_loss_magnitude(self._turbulent_limit_flow_rate())

    @staticmethod
    def _linear_interpolate(
        x: float,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
    ) -> float:
        """
        Return the linear interpolation between two points.
        """
        if x1 == x0:
            raise ValueError("Interpolation points must have distinct x values.")

        return y0 + (float(x) - x0) * (y1 - y0) / (x1 - x0)

    def _derivative_step(self, q: float) -> float:
        """
        Return numerical derivative step around q.
        """
        return max(
            self._derivative_absolute_step(),
            self._derivative_relative_step()
            * max(abs(float(q)), self._minimum_flow_bound()),
        )

    def _minimum_flow_bound(self) -> float:
        """
        Return a small positive flow bound used for numerical bracketing.
        """
        return 1.0e-12

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

    def _length(self) -> float:
        return float(self.parameters["length"])

    def _diameter(self) -> float:
        return float(self.parameters["diameter"])

    def _roughness(self) -> float:
        return float(self.parameters["roughness"])

    def _kinematic_viscosity(self) -> float:
        return float(self.parameters["kinematic_viscosity"])

    def _gravity(self) -> float:
        return float(self.parameters["gravity"])

    def _laminar_reynolds(self) -> float:
        return float(self.parameters["laminar_reynolds"])

    def _turbulent_reynolds(self) -> float:
        return float(self.parameters["turbulent_reynolds"])

    def _head_tolerance(self) -> float:
        return float(self.parameters["head_tolerance"])

    def _inverse_relative_tolerance(self) -> float:
        return float(self.parameters["inverse_relative_tolerance"])

    def _inverse_max_iterations(self) -> int:
        return int(self.parameters["inverse_max_iterations"])

    def _derivative_relative_step(self) -> float:
        return float(self.parameters["derivative_relative_step"])

    def _derivative_absolute_step(self) -> float:
        return float(self.parameters["derivative_absolute_step"])
