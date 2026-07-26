from __future__ import annotations

from typing import Any, ClassVar

from hn3ttk.nodes.base import Node


class ConfigurableNode(Node):
    """
    Fully configurable hydraulic node.

    This is the most generic node model in the package. It can behave either
    as a fixed-head boundary or as an unknown-head node depending on
    ``parameters["fixed_head"]``.

    Expected ``parameters`` keys
    ----------------------------
    - ``elevation``:
      geometric elevation ``z`` in meters. Default: ``0.0``.
    - ``fixed_head``:
      ``True`` for a prescribed-head node, ``False`` for an unknown-head node.
      Default: ``False``.
    - ``head``:
      prescribed hydraulic head ``H`` in meters for fixed-head mode.
      Default: ``elevation``.
    - ``initial_head``:
      initial head guess in meters for unknown-head mode.
      Default: ``elevation``.
    - ``external_flow``:
      signed external nodal flow in m3/s. Positive means injection and
      negative means demand. Default: ``0.0``.
    - ``scale_head_with_alpha``:
      when ``True``, ``fixed_head(alpha) = elevation + alpha * (head - elevation)``.
    - ``scale_external_flow_with_alpha``:
      when ``True``, ``external_flow(alpha) = alpha * external_flow``.
    """

    type: ClassVar[str] = "configurable_node"

    def is_fixed_head(self) -> bool:
        """Return ``True`` when ``parameters['fixed_head']`` is enabled."""
        return bool(self.parameters["fixed_head"])

    def fixed_head(self, alpha: float = 1.0) -> float:
        """
        Return the prescribed hydraulic head in fixed-head mode.

        Raises
        ------
        ValueError
            If the node is currently configured as unknown-head.
        """
        if not self.is_fixed_head():
            raise ValueError("Node does not have a fixed hydraulic head.")

        alpha = self._validate_continuation_factor(alpha)

        head = self._head()

        if self._scale_head_with_alpha():
            return self.elevation() + alpha * (head - self.elevation())

        return head

    def initial_head(self) -> float:
        """
        Return the initial hydraulic-head guess.

        For fixed-head mode, this returns the imposed head so fixed-head nodes
        can still participate in utilities that expect a head value.
        """
        if self.is_fixed_head():
            return self.fixed_head(alpha=1.0)

        return self._initial_head()

    def external_flow(self, alpha: float = 1.0) -> float:
        """
        Return the signed external nodal flow.

        Positive values inject water into the network. Negative values extract
        water from the network.
        """
        alpha = self._validate_continuation_factor(alpha)

        value = self._external_flow()

        if self._scale_external_flow_with_alpha():
            return alpha * value

        return value

    def validate(self) -> None:
        """
        Validate and normalize the configurable node parameter dictionary.

        Missing optional keys are filled with defaults.
        """
        super().validate()

        self.parameters.setdefault("elevation", 0.0)
        self._validate_finite_float("elevation")

        self.parameters.setdefault("fixed_head", False)
        self._validate_bool("fixed_head")

        self.parameters.setdefault("head", self.elevation())
        self._validate_finite_float("head")

        self.parameters.setdefault("initial_head", self.elevation())
        self._validate_finite_float("initial_head")

        self.parameters.setdefault("external_flow", 0.0)
        self._validate_finite_float("external_flow")

        self.parameters.setdefault("scale_head_with_alpha", False)
        self._validate_bool("scale_head_with_alpha")

        self.parameters.setdefault("scale_external_flow_with_alpha", True)
        self._validate_bool("scale_external_flow_with_alpha")

    def model_info(self) -> dict[str, Any]:
        """Return a machine-readable summary of this node model."""
        return {
            "type": self.type,
            "description": "Fully configurable hydraulic node.",
            "parameters": [
                "elevation",
                "fixed_head",
                "head",
                "initial_head",
                "external_flow",
                "scale_head_with_alpha",
                "scale_external_flow_with_alpha",
            ],
        }

    def _head(self) -> float:
        return float(self.parameters["head"])

    def _initial_head(self) -> float:
        return float(self.parameters["initial_head"])

    def _external_flow(self) -> float:
        return float(self.parameters["external_flow"])

    def _scale_head_with_alpha(self) -> bool:
        return bool(self.parameters["scale_head_with_alpha"])

    def _scale_external_flow_with_alpha(self) -> bool:
        return bool(self.parameters["scale_external_flow_with_alpha"])
