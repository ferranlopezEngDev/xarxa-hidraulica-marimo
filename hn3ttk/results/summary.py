from __future__ import annotations

from typing import Any

from hn3ttk.results.tables import _get_state


def result_summary(result_or_state: Any) -> dict[str, Any]:
    """Return a compact summary dictionary for a result or state."""
    summary: dict[str, Any] = {}
    state: dict[str, Any] | None = None

    if hasattr(result_or_state, "success"):
        summary.update(
            {
                "success": bool(result_or_state.success),
                "message": str(result_or_state.message),
                "iterations": int(result_or_state.iterations),
                "max_abs_residual": float(result_or_state.max_abs_residual),
                "solver": result_or_state.metadata.get("solver"),
                "metadata": result_or_state.metadata,
            }
        )

        if getattr(result_or_state, "state", None) is not None:
            state = _get_state(result_or_state)
    elif isinstance(result_or_state, dict):
        state = result_or_state
    else:
        raise TypeError(
            "Expected a SolverResult-like object or a state dictionary."
        )

    if state is not None:
        summary.update(
            {
                "system_id": state["system_id"],
                "alpha": state["alpha"],
                "n_nodes": len(state["nodes"]),
                "n_links": len(state["links"]),
                "n_unknown_nodes": len(state["unknown_node_ids"]),
                "n_fixed_nodes": len(state["fixed_node_ids"]),
                "residual_units": state["residuals"].get("units", "m3/s"),
            }
        )

        if "max_abs_residual" not in summary:
            summary["max_abs_residual"] = float(state["residuals"]["max_abs"])

    return summary


def print_result_summary(result_or_state: Any) -> None:
    """Print a compact, beginner-friendly result summary."""
    summary = result_summary(result_or_state)

    if "system_id" in summary:
        print(f"System: {summary['system_id']}")

    if "success" in summary:
        print(f"Success: {summary['success']}")

    if "message" in summary:
        print(f"Message: {summary['message']}")

    if "iterations" in summary:
        print(f"Iterations: {summary['iterations']}")

    if "max_abs_residual" in summary:
        residual_units = summary.get("residual_units", "m3/s")
        print(
            "Max residual: "
            f"{summary['max_abs_residual']:.6g} {residual_units}"
        )

    if "n_nodes" in summary:
        print(f"Nodes: {summary['n_nodes']}")

    if "n_links" in summary:
        print(f"Links: {summary['n_links']}")

    if "n_unknown_nodes" in summary:
        print(f"Unknown heads: {summary['n_unknown_nodes']}")

    if "n_fixed_nodes" in summary:
        print(f"Fixed heads: {summary['n_fixed_nodes']}")
