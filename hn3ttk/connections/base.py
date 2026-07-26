from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from math import copysign, isfinite
from typing import Any, ClassVar
from uuid import uuid4


@dataclass
class Connection(ABC):
    """
    Base class for hydraulic connection models.

    A Connection represents only the local physical behaviour of an
    hydraulic element. It does not know which nodes it connects; topology is
    defined later by the system layer.

    Constructor arguments
    ---------------------
    id:
        Optional connection identifier. If omitted, a unique id is generated.
    parameters:
        Model-specific configuration dictionary. Each concrete connection class
        documents its accepted keys in its own class docstring.
    metadata:
        Free-form user metadata stored and exported together with the model.

    Common optional ``parameters`` keys
    -----------------------------------
    - ``jacobian_derivative``:
      default Jacobian strategy. Allowed values are ``"normal"``,
      ``"tendency"``, ``"inverse_head_loss"`` and ``"finite_difference"``.
    - ``jacobian_derivative_step``:
      relative finite-difference step for the fallback strategy.
    - ``jacobian_derivative_absolute_step``:
      absolute finite-difference step for the fallback strategy.
    """

    id: str = field(default_factory=lambda: f"conn_{uuid4().hex}")
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    type: ClassVar[str] = "connection"
    jacobian_derivative_modes: ClassVar[tuple[str, ...]] = (
        "default",
        "normal",
        "tendency",
        "inverse_head_loss",
        "finite_difference",
    )

    def __post_init__(self) -> None:
        self.validate()

    @abstractmethod
    def head_loss(self, q: float) -> float:
        """
        Return head variation for a given signed flow rate.

        Parameters
        ----------
        q:
            Signed flow rate in m3/s.
        """
        raise NotImplementedError

    @abstractmethod
    def flow_rate(self, delta_h: float) -> float:
        """
        Return signed flow rate for a given head variation.

        Parameters
        ----------
        delta_h:
            Signed head variation in meters.
        """
        raise NotImplementedError

    @abstractmethod
    def head_loss_derivative(self, q: float) -> float:
        """Return the derivative ``d(delta_h)/dQ`` at the requested flow rate."""
        raise NotImplementedError

    @abstractmethod
    def flow_rate_derivative(self, delta_h: float) -> float:
        """Return the derivative ``dQ/d(delta_h)`` at the requested head."""
        raise NotImplementedError

    def head_loss_tendency(self, q: float) -> float:
        """
        Return the symmetric secant tendency of the head-loss curve.

        tendency = [head_loss(q) - head_loss(-q)] / (2q)

        This is useful as an alternative Jacobian approximation when the normal
        derivative is too singular or numerically unstable near the operating
        point.
        """
        if q == 0:
            return self.head_loss_derivative(0.0)

        return (self.head_loss(q) - self.head_loss(-q)) / (2.0 * q)

    def flow_rate_tendency(self, delta_h: float) -> float:
        """
        Return the symmetric secant tendency of the flow-rate curve.

        tendency = [flow_rate(delta_h) - flow_rate(-delta_h)] / (2 delta_h)
        """
        if delta_h == 0:
            return self.flow_rate_derivative(0.0)

        return (self.flow_rate(delta_h) - self.flow_rate(-delta_h)) / (
            2.0 * delta_h
        )

    def head_loss_plot_data(
        self,
        q_start: float,
        q_end: float,
        n: int,
    ) -> dict[str, list[float]]:
        """
        Return sampled data for plotting ``ΔH(Q)``, its derivative and tendency.

        Parameters
        ----------
        q_start:
            First flow-rate value in the requested sampling interval.
        q_end:
            Last flow-rate value in the requested sampling interval.
        n:
            Number of evaluation points.
        """
        flow_rates = self._build_plot_inputs(
            start=q_start,
            end=q_end,
            n=n,
            label="Flow rate",
        )

        return {
            "flow_rates": flow_rates,
            "head_losses": [self.head_loss(q) for q in flow_rates],
            "derivatives": [self.head_loss_derivative(q) for q in flow_rates],
            "tendencies": [self.head_loss_tendency(q) for q in flow_rates],
        }

    def flow_rate_plot_data(
        self,
        delta_h_start: float,
        delta_h_end: float,
        n: int,
    ) -> dict[str, list[float]]:
        """
        Return sampled data for plotting ``Q(ΔH)``, its derivative and tendency.

        Parameters
        ----------
        delta_h_start:
            First head-variation value in the requested sampling interval.
        delta_h_end:
            Last head-variation value in the requested sampling interval.
        n:
            Number of evaluation points.
        """
        head_losses = self._build_plot_inputs(
            start=delta_h_start,
            end=delta_h_end,
            n=n,
            label="Head variation",
        )

        return {
            "head_losses": head_losses,
            "flow_rates": [self.flow_rate(delta_h) for delta_h in head_losses],
            "derivatives": [
                self.flow_rate_derivative(delta_h) for delta_h in head_losses
            ],
            "tendencies": [
                self.flow_rate_tendency(delta_h) for delta_h in head_losses
            ],
        }

    @staticmethod
    def _validate_jacobian_derivative_mode(mode: str) -> str:
        """Validate and normalize a Jacobian derivative mode string."""
        if not isinstance(mode, str):
            raise ValueError(
                "Jacobian derivative mode must be a string. "
                "Allowed values are: "
                f"{Connection.jacobian_derivative_modes}."
            )

        mode = mode.strip()

        if mode not in Connection.jacobian_derivative_modes:
            raise ValueError(
                f"Invalid jacobian derivative mode '{mode}'. "
                "Allowed values are: "
                f"{Connection.jacobian_derivative_modes}."
            )

        return mode

    def _resolve_jacobian_derivative_mode(self, method: str) -> str:
        """
        Resolve a requested derivative method to a concrete strategy.

        The special value ``"default"`` means: use the strategy stored in the
        connection parameter dictionary.
        """
        method = self._validate_jacobian_derivative_mode(method)

        if method != "default":
            return method

        configured_mode = self._validate_jacobian_derivative_mode(
            self.parameters.get("jacobian_derivative", "normal")
        )

        if configured_mode == "default":
            return "normal"

        return configured_mode

    def get_jacobian_derivative_mode(self) -> str:
        """
        Return the configured default Jacobian derivative mode.

        Returns
        -------
        str
            One of ``"normal"``, ``"tendency"``, ``"inverse_head_loss"`` or
            ``"finite_difference"``.
        """
        return self._validate_jacobian_derivative_mode(
            self.parameters.get("jacobian_derivative", "normal")
        )

    def set_jacobian_derivative_mode(self, mode: str) -> None:
        """
        Store the default Jacobian derivative mode in ``parameters``.

        Parameters
        ----------
        mode:
            One of the supported derivative strategies.
        """
        self.parameters["jacobian_derivative"] = (
            self._validate_jacobian_derivative_mode(mode)
        )

    def _finite_difference_flow_rate_derivative(self, delta_h: float) -> float:
        """Return ``dQ/d(delta_h)`` using a central finite-difference stencil."""
        delta_h = float(delta_h)

        relative_step = float(self.parameters["jacobian_derivative_step"])
        absolute_step = float(
            self.parameters["jacobian_derivative_absolute_step"]
        )

        step = max(
            absolute_step,
            relative_step * max(abs(delta_h), 1.0),
        )

        q_plus = self.flow_rate(delta_h + step)
        q_minus = self.flow_rate(delta_h - step)

        return (q_plus - q_minus) / (2.0 * step)

    def jacobian_derivative(
        self,
        delta_h: float,
        method: str = "default",
    ) -> float:
        """
        Return ``dQ/d(delta_h)`` using the requested Jacobian strategy.

        Parameters
        ----------
        delta_h:
            Signed head variation in meters.
        method:
            Requested derivative strategy. Use ``"default"`` to reuse the
            strategy stored in ``parameters["jacobian_derivative"]``.
        """
        delta_h = float(delta_h)
        resolved_method = self._resolve_jacobian_derivative_mode(method)

        if resolved_method == "normal":
            return self.flow_rate_derivative(delta_h)

        if resolved_method == "tendency":
            return self.flow_rate_tendency(delta_h)

        if resolved_method == "inverse_head_loss":
            q = self.flow_rate(delta_h)
            d_head_d_flow = self.head_loss_derivative(q)

            if d_head_d_flow == 0.0:
                tendency = self.head_loss_tendency(q)

                if tendency != 0.0:
                    return copysign(float("inf"), tendency)

                return float("inf")

            return 1.0 / d_head_d_flow

        return self._finite_difference_flow_rate_derivative(delta_h)

    @staticmethod
    def _build_plot_inputs(
        *,
        start: float,
        end: float,
        n: int,
        label: str,
    ) -> list[float]:
        """Return ``n`` equally spaced finite values between ``start`` and ``end``."""
        if not isinstance(n, int):
            raise TypeError("Sample count 'n' must be an integer.")

        if n < 2:
            raise ValueError("Sample count 'n' must be at least 2.")

        for value_name, value in (("start", start), ("end", end)):
            if not isinstance(value, (int, float)):
                raise TypeError(f"{label} {value_name} must be numeric.")

            numeric_value = float(value)

            if not isfinite(numeric_value):
                raise ValueError(f"{label} {value_name} must be finite.")

        start = float(start)
        end = float(end)
        step = (end - start) / (n - 1)

        return [start + index * step for index in range(n)]

    def validate(self) -> None:
        """
        Validate common connection fields and shared optional parameters.

        Concrete subclasses usually call this method first and then validate
        their own model-specific keys.
        """
        if not isinstance(self.id, str):
            raise TypeError("Connection id must be a string.")

        if not self.id:
            raise ValueError("Connection id cannot be empty.")

        if not isinstance(self.parameters, dict):
            raise TypeError("Connection parameters must be a dictionary.")

        if not isinstance(self.metadata, dict):
            raise TypeError("Connection metadata must be a dictionary.")

        self.parameters.setdefault("jacobian_derivative", "normal")
        self.parameters.setdefault("jacobian_derivative_step", 1.0e-6)
        self.parameters.setdefault(
            "jacobian_derivative_absolute_step",
            1.0e-10,
        )

        self.parameters["jacobian_derivative"] = (
            self._validate_jacobian_derivative_mode(
                self.parameters["jacobian_derivative"]
            )
        )

        for name in (
            "jacobian_derivative_step",
            "jacobian_derivative_absolute_step",
        ):
            value = self.parameters[name]

            if not isinstance(value, (int, float)):
                raise TypeError(f"Parameter '{name}' must be numeric.")

            if not isfinite(float(value)):
                raise ValueError(f"Parameter '{name}' must be finite.")

            value = float(value)

            if value <= 0.0:
                raise ValueError(f"Parameter '{name}' must be positive.")

            self.parameters[name] = value

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the connection to a serializable dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary with ``id``, ``type``, ``parameters`` and ``metadata``.
        """
        return {
            "id": self.id,
            "type": self.type,
            "parameters": self.parameters,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Connection":
        """
        Build a connection object from a serialized dictionary.

        Parameters
        ----------
        data:
            Dictionary containing ``id`` and optionally ``parameters`` and
            ``metadata``.
        """
        return cls(
            id=data["id"],
            parameters=data.get("parameters", {}),
            metadata=data.get("metadata", {}),
        )

    def model_info(self) -> dict[str, Any]:
        """
        Return a small descriptive dictionary for the connection model.

        This helper is useful for documentation tools, demos or UI layers that
        want to inspect the model without hardcoding parameter names.
        """
        return {
            "type": self.type,
            "description": "Base hydraulic connection model.",
            "parameters": [
                "jacobian_derivative",
                "jacobian_derivative_step",
                "jacobian_derivative_absolute_step",
            ],
        }
