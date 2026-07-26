from __future__ import annotations

from math import isfinite
from typing import Any


def expected_single_pipe_solution() -> dict[str, Any]:
    """Return the reference analytical solution for the single-pipe case."""
    return {
        "unknown_heads": {"demand": 9.0},
        "link_flow_rates": {"link_1": 0.1},
        "link_delta_h": {"link_1": -1.0},
        "tolerance": 1.0e-8,
    }


def expected_larock_example_2_6_solution() -> dict[str, Any]:
    """Return Larock Example 2.6 reference values."""
    return {
        "unknown_heads": {"split_junction": 13.41858},
        "link_flow_rates": {
            "link_12_in": 3.64,
            "link_10_in": 2.31,
            "link_8_in": 1.33,
        },
        "tolerance": 2.0e-2,
    }


def expected_larock_example_2_7_solution() -> dict[str, Any]:
    """Return Larock Example 2.7 reference values."""
    return {
        "unknown_heads": {"junction": 83.7},
        "link_flow_rates": {
            "link_1": 0.1023,
            "link_2": 0.0200,
            "link_3": 0.0622,
        },
        "head_tolerance": 1.0e-2,
        "flow_tolerance": 2.0e-4,
    }


def expected_larock_problem_2_13_solution() -> dict[str, Any]:
    """Return Larock Problem 2.13 selected-answer reference values."""
    return {
        "unknown_heads": {"midpoint": 3.05},
        "link_flow_rates": {
            "link_upstream": 0.00698,
            "link_downstream": 0.00698,
        },
        "tolerance": 5.0e-5,
    }


def expected_larock_problem_4_1a_solution() -> dict[str, Any]:
    """Return Larock Problem 4.1a selected-answer reference values."""
    return {
        "link_flow_rate_magnitudes": {
            "link_1": 0.606,
            "link_2": 0.560,
            "link_3": 0.106,
            "link_4": 0.0462,
            "link_5": 0.0602,
            "link_6": 0.394,
            "link_7": 0.190,
        },
        "flow_tolerance": 3.5e-2,
        "residual_tolerance": 1.0e-8,
    }


def expected_larock_problem_4_1b_solution() -> dict[str, Any]:
    """Return Larock Problem 4.1b selected-answer reference values."""
    return {
        "link_flow_rate_magnitudes": {
            "link_1": 0.0061,
            "link_2": 0.0323,
            "link_3": 0.0228,
            "link_4": 0.1572,
            "link_5": 0.1177,
            "link_6": 0.1412,
            "link_7": 0.5239,
            "pump_link_7": 0.5239,
        },
        "flow_tolerance": 4.0e-3,
        "residual_tolerance": 1.0e-8,
    }


def expected_larock_problem_4_8_solution() -> dict[str, Any]:
    """Return Larock Problem 4.8 selected-answer reference values."""
    return {
        "unknown_heads": {"upstream_node": 18.575296},
        "link_flow_rates": {
            "link_branch_1": 0.849,
            "link_branch_2": 2.151,
        },
        "tolerance": 2.0e-3,
    }


def validate_result_basic(result: Any, residual_tolerance: float = 1.0e-8) -> None:
    """Validate generic solver success and finite hydraulic values."""
    assert result.success is True
    assert result.state is not None
    assert result.max_abs_residual <= residual_tolerance

    state = result.state

    for node_data in state["nodes"].values():
        assert isfinite(float(node_data["head"]))

    for link_data in state["links"].values():
        assert isfinite(float(link_data["flow_rate"]))
        assert isfinite(float(link_data["delta_h"]))


def validate_single_pipe_result(result: Any) -> None:
    """Validate the analytical single-pipe solution."""
    validate_result_basic(result, residual_tolerance=1.0e-8)

    state = result.state
    assert state is not None
    reference = expected_single_pipe_solution()
    tolerance = float(reference["tolerance"])

    demand_head = float(state["nodes"]["demand"]["head"])
    link_flow = float(state["links"]["link_1"]["flow_rate"])
    link_delta_h = float(state["links"]["link_1"]["delta_h"])

    assert abs(demand_head - reference["unknown_heads"]["demand"]) <= tolerance
    assert abs(link_flow - reference["link_flow_rates"]["link_1"]) <= tolerance
    assert abs(link_delta_h - reference["link_delta_h"]["link_1"]) <= tolerance
    assert result.max_abs_residual <= tolerance


def validate_larock_example_2_6_result(result: Any) -> None:
    """Validate Larock Example 2.6 against the published branch discharges."""
    _validate_reference_case(result, expected_larock_example_2_6_solution())


def validate_larock_example_2_7_result(result: Any) -> None:
    """Validate Larock Example 2.7 against the published three-reservoir flows."""
    _validate_reference_case(result, expected_larock_example_2_7_solution())


def validate_larock_problem_2_13_result(result: Any) -> None:
    """Validate Larock Problem 2.13 against the selected end-of-book answer."""
    _validate_reference_case(result, expected_larock_problem_2_13_solution())


def validate_larock_problem_4_1a_result(result: Any) -> None:
    """Validate Larock Problem 4.1a against the selected end-of-book answer."""
    _validate_reference_case(result, expected_larock_problem_4_1a_solution())


def validate_larock_problem_4_1b_result(result: Any) -> None:
    """Validate Larock Problem 4.1b against the selected end-of-book answer."""
    _validate_reference_case(result, expected_larock_problem_4_1b_solution())


def validate_larock_problem_4_8_result(result: Any) -> None:
    """Validate Larock Problem 4.8 against the selected end-of-book answer."""
    _validate_reference_case(result, expected_larock_problem_4_8_solution())


def validate_medium_generic_network_result(
    result: Any,
    residual_tolerance: float = 1.0e-8,
) -> None:
    """Validate structural properties of the medium generic network."""
    validate_result_basic(result, residual_tolerance=residual_tolerance)

    state = result.state
    assert state is not None

    assert len(state["nodes"]) == 8
    assert len(state["links"]) == 11
    assert len(state["unknown_node_ids"]) == 6
    assert len(state["fixed_node_ids"]) == 2
    assert result.max_abs_residual <= residual_tolerance

    flow_rates = [
        float(link_data["flow_rate"])
        for link_data in state["links"].values()
    ]
    assert any(isfinite(flow_rate) for flow_rate in flow_rates)


def _validate_reference_case(result: Any, reference: dict[str, Any]) -> None:
    """
    Validate a benchmark against published reference heads and flows.

    Some textbook answers are rounded or come from graphical tools such as the
    Moody diagram, so each case carries its own tolerance.
    """
    default_tolerance = float(reference.get("tolerance", 1.0e-8))
    head_tolerance = float(reference.get("head_tolerance", default_tolerance))
    flow_tolerance = float(reference.get("flow_tolerance", default_tolerance))
    residual_tolerance = float(
        reference.get(
            "residual_tolerance",
            max(default_tolerance, head_tolerance, flow_tolerance, 1.0e-8),
        )
    )
    validate_result_basic(result, residual_tolerance=residual_tolerance)

    state = result.state
    assert state is not None

    for node_id, expected_head in reference.get("unknown_heads", {}).items():
        actual_head = float(state["nodes"][node_id]["head"])
        assert abs(actual_head - float(expected_head)) <= head_tolerance

    for link_id, expected_flow in reference.get("link_flow_rates", {}).items():
        actual_flow = float(state["links"][link_id]["flow_rate"])
        assert abs(actual_flow - float(expected_flow)) <= flow_tolerance

    for link_id, expected_flow in reference.get("link_flow_rate_magnitudes", {}).items():
        actual_flow = abs(float(state["links"][link_id]["flow_rate"]))
        assert abs(actual_flow - float(expected_flow)) <= flow_tolerance
