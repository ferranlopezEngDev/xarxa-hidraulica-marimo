from __future__ import annotations

from typing import Any, ClassVar

from hn3ttk.nodes.base import Node


class DemandNode(Node):
    """
    Unknown-head node with prescribed demand.

    Demand is stored as a positive magnitude and returned as negative external
    flow, because it extracts water from the network.

    Expected ``parameters`` keys
    ----------------------------
    - ``elevation``:
      geometric elevation in meters. Default: ``0.0``.
    - ``initial_head``:
      initial head guess in meters. Default: ``elevation``.
    - ``demand``:
      positive demand magnitude in m3/s. Required.
    - ``scale_demand_with_alpha``:
      when ``True``, the effective external flow becomes ``-alpha * demand``.
    """

    type: ClassVar[str] = "demand_node"

    def is_fixed_head(self) -> bool:
        """Demand nodes have unknown hydraulic head."""
        return False

    def fixed_head(self, alpha: float = 1.0) -> float:
        """
        Raise because demand nodes do not prescribe hydraulic head.

        This method exists to satisfy the common :class:`Node` API.
        """
        self._validate_continuation_factor(alpha)
        raise ValueError("DemandNode does not have a fixed hydraulic head.")

    def initial_head(self) -> float:
        """Return the initial unknown-head guess in meters."""
        return float(self.parameters["initial_head"])

    def external_flow(self, alpha: float = 1.0) -> float:
        """
        Return demand as negative external flow.

        The stored demand magnitude is positive, but the returned external flow
        is negative because demand removes water from the network.
        """
        alpha = self._validate_continuation_factor(alpha)

        demand = float(self.parameters["demand"])

        if self._scale_demand_with_alpha():
            return -alpha * demand

        return -demand

    def validate(self) -> None:
        """
        Validate demand-node parameters and fill optional defaults.

        The ``demand`` key is required and must be non-negative.
        """
        super().validate()

        self.parameters.setdefault("elevation", 0.0)
        self._validate_finite_float("elevation")

        self.parameters.setdefault("initial_head", self.elevation())
        self._validate_finite_float("initial_head")

        if "demand" not in self.parameters:
            raise ValueError("DemandNode requires parameter 'demand'.")

        self._validate_finite_float("demand")

        if self.parameters["demand"] < 0.0:
            raise ValueError("DemandNode parameter 'demand' cannot be negative.")

        self.parameters.setdefault("scale_demand_with_alpha", True)
        self._validate_bool("scale_demand_with_alpha")

    def model_info(self) -> dict[str, Any]:
        """Return a machine-readable summary of the demand node model."""
        return {
            "type": self.type,
            "description": "Unknown-head node with prescribed demand.",
            "parameters": [
                "elevation",
                "initial_head",
                "demand",
                "scale_demand_with_alpha",
            ],
        }

    def _scale_demand_with_alpha(self) -> bool:
        return bool(self.parameters["scale_demand_with_alpha"])
