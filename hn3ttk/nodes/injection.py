from __future__ import annotations

from typing import Any, ClassVar

from hn3ttk.nodes.base import Node


class InjectionNode(Node):
    """
    Unknown-head node with prescribed injection.

    Injection is stored as a positive magnitude and returned as positive
    external flow, because it adds water into the network.

    Expected ``parameters`` keys
    ----------------------------
    - ``elevation``:
      geometric elevation in meters. Default: ``0.0``.
    - ``initial_head``:
      initial head guess in meters. Default: ``elevation``.
    - ``injection``:
      positive injection magnitude in m3/s. Required.
    - ``scale_injection_with_alpha``:
      when ``True``, the effective external flow becomes ``alpha * injection``.
    """

    type: ClassVar[str] = "injection_node"

    def is_fixed_head(self) -> bool:
        """Injection nodes have unknown hydraulic head."""
        return False

    def fixed_head(self, alpha: float = 1.0) -> float:
        """
        Raise because injection nodes do not prescribe hydraulic head.
        """
        self._validate_continuation_factor(alpha)
        raise ValueError("InjectionNode does not have a fixed hydraulic head.")

    def initial_head(self) -> float:
        """Return the initial unknown-head guess in meters."""
        return float(self.parameters["initial_head"])

    def external_flow(self, alpha: float = 1.0) -> float:
        """
        Return injection as positive external flow.

        Positive external flow means water is added into the network.
        """
        alpha = self._validate_continuation_factor(alpha)

        injection = float(self.parameters["injection"])

        if self._scale_injection_with_alpha():
            return alpha * injection

        return injection

    def validate(self) -> None:
        """
        Validate injection-node parameters and fill optional defaults.

        The ``injection`` key is required and must be non-negative.
        """
        super().validate()

        self.parameters.setdefault("elevation", 0.0)
        self._validate_finite_float("elevation")

        self.parameters.setdefault("initial_head", self.elevation())
        self._validate_finite_float("initial_head")

        if "injection" not in self.parameters:
            raise ValueError("InjectionNode requires parameter 'injection'.")

        self._validate_finite_float("injection")

        if self.parameters["injection"] < 0.0:
            raise ValueError("InjectionNode parameter 'injection' cannot be negative.")

        self.parameters.setdefault("scale_injection_with_alpha", True)
        self._validate_bool("scale_injection_with_alpha")

    def model_info(self) -> dict[str, Any]:
        """Return a machine-readable summary of the injection node model."""
        return {
            "type": self.type,
            "description": "Unknown-head node with prescribed injection.",
            "parameters": [
                "elevation",
                "initial_head",
                "injection",
                "scale_injection_with_alpha",
            ],
        }

    def _scale_injection_with_alpha(self) -> bool:
        return bool(self.parameters["scale_injection_with_alpha"])
