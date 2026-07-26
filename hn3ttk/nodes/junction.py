from __future__ import annotations

from typing import Any, ClassVar

from hn3ttk.nodes.configurable import ConfigurableNode


class JunctionNode(ConfigurableNode):
    """
    Junction node with unknown hydraulic head.

    It may optionally include an external flow term.

    Expected ``parameters`` keys
    ----------------------------
    - ``elevation``:
      geometric elevation in meters. Default: ``0.0``.
    - ``initial_head``:
      initial unknown-head guess in meters. Default: ``elevation``.
    - ``external_flow``:
      optional signed external flow in m3/s. Default: ``0.0``.
    - ``scale_external_flow_with_alpha``:
      when ``True``, the external flow is scaled by ``alpha`` during
      continuation solves.
    """

    type: ClassVar[str] = "junction_node"

    def validate(self) -> None:
        """
        Validate junction-node configuration.

        This method forces ``fixed_head=False`` because a junction is always an
        unknown-head node in this model.
        """
        if "fixed_head" in self.parameters and self.parameters["fixed_head"] is not False:
            raise ValueError("JunctionNode cannot have fixed_head=True.")

        self.parameters["fixed_head"] = False
        self.parameters.setdefault("external_flow", 0.0)

        super().validate()

    def model_info(self) -> dict[str, Any]:
        """Return a machine-readable summary of the junction model."""
        return {
            "type": self.type,
            "description": "Unknown-head junction node.",
            "parameters": [
                "elevation",
                "initial_head",
                "external_flow",
                "scale_external_flow_with_alpha",
            ],
        }
