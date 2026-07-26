from __future__ import annotations

from typing import Any

from hn3ttk.nodes.base import Node
from hn3ttk.nodes.configurable import ConfigurableNode
from hn3ttk.nodes.demand import DemandNode
from hn3ttk.nodes.fixed_head import FixedHeadNode
from hn3ttk.nodes.injection import InjectionNode
from hn3ttk.nodes.junction import JunctionNode
from hn3ttk.nodes.reservoir import ReservoirNode


NODE_REGISTRY: dict[str, type[Node]] = {
    ConfigurableNode.type: ConfigurableNode,
    JunctionNode.type: JunctionNode,
    FixedHeadNode.type: FixedHeadNode,
    DemandNode.type: DemandNode,
    InjectionNode.type: InjectionNode,
    ReservoirNode.type: ReservoirNode,
}


def node_from_dict(data: dict[str, Any]) -> Node:
    """
    Build a Node object from a dictionary.

    Expected format:

        {
            "id": "node_1",
            "type": "reservoir_node",
            "parameters": {...},
            "metadata": {...}
        }

    The "id" and "metadata" fields are optional.
    The "type" and "parameters" fields are required.
    """
    if not isinstance(data, dict):
        raise TypeError("Node data must be a dictionary.")

    if "type" not in data:
        raise ValueError("Node data must contain a 'type' field.")

    if "parameters" not in data:
        raise ValueError("Node data must contain a 'parameters' field.")

    node_type = data["type"]

    if not isinstance(node_type, str):
        raise TypeError("Node 'type' must be a string.")

    if node_type not in NODE_REGISTRY:
        available_types = ", ".join(sorted(NODE_REGISTRY.keys()))
        raise ValueError(
            f"Unknown node type '{node_type}'. "
            f"Available types: {available_types}"
        )

    parameters = data["parameters"]

    if not isinstance(parameters, dict):
        raise TypeError("Node 'parameters' must be a dictionary.")

    metadata = data.get("metadata", {})

    if not isinstance(metadata, dict):
        raise TypeError("Node 'metadata' must be a dictionary.")

    node_class = NODE_REGISTRY[node_type]

    constructor_arguments: dict[str, Any] = {
        "parameters": dict(parameters),
        "metadata": dict(metadata),
    }

    if "id" in data:
        if not isinstance(data["id"], str):
            raise TypeError("Node 'id' must be a string.")

        constructor_arguments["id"] = data["id"]

    return node_class(**constructor_arguments)


def node_to_dict(node: Node) -> dict[str, Any]:
    """
    Convert a Node object to a serializable dictionary.
    """
    if not isinstance(node, Node):
        raise TypeError("Expected a Node object.")

    return node.to_dict()


def available_node_types() -> list[str]:
    """
    Return the list of registered node types.
    """
    return sorted(NODE_REGISTRY.keys())


def register_node_type(node_class: type[Node]) -> None:
    """
    Register a new Node class in the factory.

    The class must inherit from Node and define a string class variable
    named 'type'.
    """
    if not issubclass(node_class, Node):
        raise TypeError("Registered class must inherit from Node.")

    node_type = getattr(node_class, "type", None)

    if not isinstance(node_type, str):
        raise TypeError("Node class must define a string 'type' attribute.")

    if not node_type:
        raise ValueError("Node class 'type' cannot be empty.")

    NODE_REGISTRY[node_type] = node_class