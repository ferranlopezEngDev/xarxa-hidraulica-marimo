from __future__ import annotations

from typing import Any

from hn3ttk.connections import connection_from_dict
from hn3ttk.nodes import node_from_dict
from hn3ttk.system.hydraulic_system import HydraulicSystem
from hn3ttk.system.link import Link


def system_from_dict(data: dict[str, Any]) -> HydraulicSystem:
    """
    Build a HydraulicSystem object from a dictionary.

    Expected format:

        {
            "id": "system_1",
            "nodes": [...],
            "connections": [...],
            "links": [...],
            "metadata": {...}
        }

    The expected structure is compatible with HydraulicSystem.to_dict().
    """
    if not isinstance(data, dict):
        raise TypeError("System data must be a dictionary.")

    if "nodes" not in data:
        raise ValueError("System data must contain a 'nodes' field.")

    if "connections" not in data:
        raise ValueError("System data must contain a 'connections' field.")

    if "links" not in data:
        raise ValueError("System data must contain a 'links' field.")

    system_id = data.get("id", "hydraulic_system")

    if not isinstance(system_id, str):
        raise TypeError("System 'id' must be a string.")

    if not system_id:
        raise ValueError("System 'id' cannot be empty.")

    metadata = data.get("metadata", {})

    if not isinstance(metadata, dict):
        raise TypeError("System 'metadata' must be a dictionary.")

    node_data_list = data["nodes"]
    connection_data_list = data["connections"]
    link_data_list = data["links"]

    if not isinstance(node_data_list, list):
        raise TypeError("System 'nodes' must be a list.")

    if not isinstance(connection_data_list, list):
        raise TypeError("System 'connections' must be a list.")

    if not isinstance(link_data_list, list):
        raise TypeError("System 'links' must be a list.")

    system = HydraulicSystem(
        id=system_id,
        metadata=dict(metadata),
    )

    for node_data in node_data_list:
        node = node_from_dict(node_data)
        system.add_node(node)

    for connection_data in connection_data_list:
        connection = connection_from_dict(connection_data)
        system.add_connection(connection)

    for link_data in link_data_list:
        link = Link.from_dict(link_data)
        system.add_link(link)

    system.validate()

    return system


def system_to_dict(system: HydraulicSystem) -> dict[str, Any]:
    """
    Convert a HydraulicSystem object to a serializable dictionary.
    """
    if not isinstance(system, HydraulicSystem):
        raise TypeError("Expected a HydraulicSystem object.")

    return system.to_dict()