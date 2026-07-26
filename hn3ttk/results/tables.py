from __future__ import annotations

from typing import Any


def _get_state(result_or_state: Any) -> dict[str, Any]:
    """Return a state dictionary from a SolverResult-like object or dict."""
    if hasattr(result_or_state, "state"):
        state = result_or_state.state

        if state is None:
            raise ValueError(
                "The provided SolverResult does not contain a state. "
                "Solve the system successfully or evaluate the state first."
            )

        return state

    if isinstance(result_or_state, dict):
        return result_or_state

    raise TypeError(
        "Expected a SolverResult-like object with a 'state' attribute or a "
        "state dictionary."
    )


def nodes_table(result_or_state: Any) -> list[dict[str, Any]]:
    """Return node results as a list of flat dictionaries."""
    state = _get_state(result_or_state)
    rows: list[dict[str, Any]] = []

    for node_id, node_data in state["nodes"].items():
        rows.append(
            {
                "node_id": node_id,
                "type": node_data["type"],
                "head": float(node_data["head"]),
                "elevation": float(node_data["elevation"]),
                "pressure_head": float(node_data["pressure_head"]),
                "external_flow": float(node_data["external_flow"]),
                "is_fixed_head": bool(node_data["is_fixed_head"]),
                "is_unknown_head": bool(node_data["is_unknown_head"]),
                "metadata": node_data["metadata"],
            }
        )

    return rows


def links_table(result_or_state: Any) -> list[dict[str, Any]]:
    """Return link results as a list of flat dictionaries."""
    state = _get_state(result_or_state)
    rows: list[dict[str, Any]] = []

    for link_id, link_data in state["links"].items():
        rows.append(
            {
                "link_id": link_id,
                "connection_id": link_data["connection_id"],
                "connection_type": link_data["connection_type"],
                "from_node_id": link_data["from_node_id"],
                "to_node_id": link_data["to_node_id"],
                "delta_h": float(link_data["delta_h"]),
                "flow_rate": float(link_data["flow_rate"]),
                "metadata": link_data["metadata"],
            }
        )

    return rows


def residuals_table(result_or_state: Any) -> list[dict[str, Any]]:
    """Return residuals by node as a list of flat dictionaries."""
    state = _get_state(result_or_state)
    residual_units = state["residuals"].get("units", "m3/s")

    return [
        {
            "node_id": node_id,
            "residual": float(residual_value),
            "units": residual_units,
        }
        for node_id, residual_value in state["residuals"]["by_node"].items()
    ]


def unknown_heads_table(result_or_state: Any) -> list[dict[str, Any]]:
    """Return the unknown-head vector with node ids and indices."""
    state = _get_state(result_or_state)

    return [
        {
            "index": index,
            "node_id": node_id,
            "head": float(head_value),
        }
        for index, (node_id, head_value) in enumerate(
            zip(
                state["unknown_node_ids"],
                state["unknown_heads"],
            )
        )
    ]
