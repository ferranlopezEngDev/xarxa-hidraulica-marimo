from __future__ import annotations

from math import copysign, isclose, isfinite, log, log10, pi
from typing import Any, ClassVar

from hn3ttk.connections.base import Connection


class PipeLocalPowerLaw(Connection):
    """
    Local power-law pipe model derived from Darcy-Weisbach.

    The reference Darcy-Weisbach model is locally approximated as:

        ΔH = -k(Q) * sign(Q) * |Q|^n(Q)

    where k(Q) and n(Q) are recomputed around the current flow rate.

    Sign convention:
        q > 0 gives delta_h < 0 because passive pipes dissipate energy.

    Expected ``parameters`` keys
    ----------------------------
    Required:
    - ``length`` [m]
    - ``diameter`` [m]
    - ``roughness`` [m]

    Optional:
    - ``kinematic_viscosity``
    - ``gravity``
    - ``laminar_reynolds``
    - ``turbulent_reynolds``
    - ``relative_band``
    - ``minimum_flow_rate``
    - ``head_tolerance``
    - ``inverse_relative_tolerance``
    - ``inverse_max_iterations``
    - ``derivative_relative_step``
    - ``derivative_absolute_step``
    """

    type: ClassVar[str] = "pipe_local_power_law"

    def head_loss(self, q: float) -> float:
        """
        Return signed head variation ΔH for signed flow rate q.
        """
        q = float(q)

        if q == 0.0:
            return 0.0

        return -copysign(self._head_loss_magnitude(abs(q)), q)

    def flow_rate(self, delta_h: float) -> float:
        """
        Return signed flow rate q for a signed head variation delta_h.

        For passive pipes:
            delta_h < 0 gives q > 0.
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

        The derivative is computed numerically because k(Q) and n(Q) are local
        approximations that change with the operating point.
        """
        q = float(q)

        if q == 0.0:
            k_laminar, _ = self._laminar_power_law_parameters()
            return -k_laminar

        step = self._derivative_step(q)

        q_minus = q - step
        q_plus = q + step

        h_minus = self.head_loss(q_minus)
        h_plus = self.head_loss(q_plus)

        return (h_plus - h_minus) / (q_plus - q_minus)

    def flow_rate_derivative(self, delta_h: float) -> float:
        """
        Return dQ/d(ΔH) evaluated at delta_h.
        """
        delta_h = float(delta_h)

        if abs(delta_h) <= self._head_tolerance():
            k_laminar, _ = self._laminar_power_law_parameters()
            return -1.0 / k_laminar

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
                raise ValueError(
                    f"PipeLocalPowerLaw requires parameter '{name}'."
                )

        default_parameters = {
            "kinematic_viscosity": 1.0e-6,
            "gravity": 9.81,
            "laminar_reynolds": 2000.0,
            "turbulent_reynolds": 4000.0,
            "relative_band": 0.05,
            "minimum_flow_rate": 1.0e-8,
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
            "relative_band",
            "minimum_flow_rate",
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

        if not (0.0 < self._relative_band() < 1.0):
            raise ValueError("Parameter 'relative_band' must be between 0 and 1.")

        if self._minimum_flow_rate() <= 0.0:
            raise ValueError("Parameter 'minimum_flow_rate' must be positive.")

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
        """Return a machine-readable summary of the local power-law model."""
        return {
            "type": self.type,
            "equation": "ΔH = -k(Q) * sign(Q) * |Q|^n(Q)",
            "reference_model": "Darcy-Weisbach",
            "local_model": "Power-law approximation with local k and n",
            "parameters": [
                "length",
                "diameter",
                "roughness",
                "kinematic_viscosity",
                "gravity",
                "laminar_reynolds",
                "turbulent_reynolds",
                "relative_band",
                "minimum_flow_rate",
                "jacobian_derivative",
                "jacobian_derivative_step",
                "jacobian_derivative_absolute_step",
            ],
            "description": (
                "Pipe connection using Darcy-Weisbach friction factors and a "
                "local power-law approximation outside transition, with a "
                "linear interpolation of |ΔH|(Q) in transition."
            ),
        }

    def local_power_law_parameters(self, q: float) -> tuple[float, float]:
        """
        Return local power-law parameters (k, n) at the requested flow rate.

        Laminar regime:
            exact laminar power law.

        Transitional regime:
            k(Q) and n(Q) are derived from the local value and slope of a
            linear interpolation of the transition head-loss curve.

        Turbulent regime:
            k and n are obtained from a local power-law fit of the
            Swamee-Jain friction factor.
        """
        q_abs = abs(float(q))

        if q_abs <= self._minimum_flow_rate():
            return self._laminar_power_law_parameters()

        reynolds = self.reynolds_number_from_flow_magnitude(q_abs)

        regime = self._flow_regime_from_reynolds(reynolds)

        if regime == "laminar":
            return self._laminar_power_law_parameters()

        if regime == "transition":
            return self._transition_equivalent_power_law_parameters(q_abs)

        if regime == "turbulent":
            return self._turbulent_local_power_law_parameters(q_abs)

        return self._laminar_power_law_parameters()

    def reynolds_number(self, q: float) -> float:
        """
        Return Reynolds number for signed flow rate q.
        """
        return self.reynolds_number_from_flow_magnitude(abs(float(q)))

    def reynolds_number_from_flow_magnitude(self, q_abs: float) -> float:
        """
        Return Reynolds number for a positive flow-rate magnitude.
        """
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
            effective factor derived from the local power-law head-loss model.

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

    def _head_loss_magnitude(self, q_abs: float) -> float:
        """
        Return positive head-loss magnitude for positive flow-rate magnitude.
        """
        q_abs = float(q_abs)

        if q_abs <= self._minimum_flow_rate():
            k, n = self._laminar_power_law_parameters()
            return k * q_abs**n

        regime = self._flow_regime_from_reynolds(
            self.reynolds_number_from_flow_magnitude(q_abs)
        )

        if regime == "laminar":
            k, n = self._laminar_power_law_parameters()
            return k * q_abs**n

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
            return target_head_loss / self._laminar_power_law_parameters()[0]

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
        k_laminar, _ = self._laminar_power_law_parameters()
        q_laminar = target_head_loss / k_laminar

        return max(
            q_laminar,
            self._minimum_flow_rate(),
        )

    def _laminar_power_law_parameters(self) -> tuple[float, float]:
        """
        Return exact laminar power-law parameters.

        In laminar pipe flow:

            |ΔH| = 128 * ν * L * |Q| / (g * π * D⁴)

        Therefore:

            k = 128 * ν * L / (g * π * D⁴)
            n = 1
        """
        k = (
            128.0
            * self._kinematic_viscosity()
            * self._length()
            / (self._gravity() * pi * self._diameter() ** 4)
        )

        return k, 1.0

    def _transition_equivalent_power_law_parameters(
        self,
        q_abs: float,
    ) -> tuple[float, float]:
        """
        Return local equivalent k and n from the transition line value/slope.
        """
        q_abs = float(q_abs)
        head_loss_magnitude = self._transition_head_loss_magnitude(q_abs)
        slope = self._transition_head_loss_slope()
        n = q_abs * slope / head_loss_magnitude
        k = head_loss_magnitude / q_abs**n

        if k <= 0.0:
            raise ValueError("Computed local coefficient k must be positive.")

        if n <= 0.0:
            raise ValueError("Computed local exponent n must be positive.")

        return k, n

    def _turbulent_local_power_law_parameters(
        self,
        q_abs: float,
    ) -> tuple[float, float]:
        """
        Fit a local power law using only the turbulent Swamee-Jain friction law.
        """
        q1, q2 = self._local_power_law_band(q_abs)
        re1 = self.reynolds_number_from_flow_magnitude(q1)
        re2 = self.reynolds_number_from_flow_magnitude(q2)
        f1 = self._swamee_jain_friction_factor(re1)
        f2 = self._swamee_jain_friction_factor(re2)

        return self._power_law_parameters_from_samples(q1, q2, f1, f2)

    def _turbulent_limit_power_law_parameters(self) -> tuple[float, float]:
        """
        Return the local power-law parameters at the turbulent Reynolds limit.
        """
        return self._turbulent_local_power_law_parameters(
            self._flow_rate_from_reynolds(self._turbulent_reynolds())
        )

    def _turbulent_head_loss_magnitude(self, q_abs: float) -> float:
        """
        Return the turbulent head-loss magnitude from the local power-law fit.
        """
        k, n = self._turbulent_local_power_law_parameters(q_abs)
        return k * q_abs**n

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

    def _transition_head_loss_slope(self) -> float:
        """
        Return the constant slope of the transition line in the Q-|ΔH| plane.
        """
        return (
            self._turbulent_head_loss_limit() - self._laminar_head_loss_limit()
        ) / (
            self._turbulent_limit_flow_rate() - self._laminar_limit_flow_rate()
        )

    def _local_power_law_band(self, q_abs: float) -> tuple[float, float]:
        """
        Return the local sampling band used to fit the power-law coefficients.
        """
        q1 = max(
            self._minimum_flow_rate(),
            float(q_abs) * (1.0 - self._relative_band()),
        )
        q2 = max(
            float(q_abs) * (1.0 + self._relative_band()),
            q1 * (1.0 + self._relative_band()),
        )

        return q1, q2

    def _power_law_parameters_from_samples(
        self,
        q1: float,
        q2: float,
        f1: float,
        f2: float,
    ) -> tuple[float, float]:
        """
        Build k and n from two positive flow-rate samples and their factors.
        """
        if f1 <= 0.0 or f2 <= 0.0:
            return self._laminar_power_law_parameters()

        exponent_b = log(f1 / f2) / log(q2 / q1)
        coefficient_a = f1 * q1**exponent_b

        k = (
            8.0
            * coefficient_a
            * self._length()
            / (self._gravity() * pi**2 * self._diameter() ** 5)
        )
        n = 2.0 - exponent_b

        if k <= 0.0:
            raise ValueError("Computed local coefficient k must be positive.")

        if n <= 0.0:
            raise ValueError("Computed local exponent n must be positive.")

        return k, n

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
        return self._laminar_head_loss_magnitude(self._laminar_limit_flow_rate())

    def _turbulent_head_loss_limit(self) -> float:
        return self._turbulent_head_loss_magnitude(self._turbulent_limit_flow_rate())

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

    def _laminar_head_loss_magnitude(self, q_abs: float) -> float:
        """
        Return the exact laminar head-loss magnitude.
        """
        k, n = self._laminar_power_law_parameters()
        return k * float(q_abs) ** n

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

    def _swamee_jain_friction_factor(self, reynolds: float) -> float:
        """
        Return turbulent Darcy friction factor using Swamee-Jain.
        """
        relative_roughness = self._roughness() / self._diameter()

        return 0.25 / log10(
            relative_roughness / 3.7 + 5.74 / reynolds**0.9
        ) ** 2

    def _derivative_step(self, q: float) -> float:
        """
        Return numerical derivative step around q.
        """
        return max(
            self._derivative_absolute_step(),
            self._derivative_relative_step()
            * max(abs(float(q)), self._minimum_flow_rate()),
        )

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

    def _relative_band(self) -> float:
        return float(self.parameters["relative_band"])

    def _minimum_flow_rate(self) -> float:
        return float(self.parameters["minimum_flow_rate"])

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
