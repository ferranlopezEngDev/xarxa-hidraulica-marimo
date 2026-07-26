"""
Convenience public API for HN3Ttk.

This module is intended for examples, tutorials, notebooks and interactive use.

For package internals and production-style code, prefer explicit imports from
the corresponding submodules.
"""

from hn3ttk.benchmarks import (
    available_default_solvers,
    build_hardy_cross_loop_system,
    build_medium_generic_network_system,
    build_parallel_pipes_system,
    build_single_pipe_system,
    build_three_reservoirs_system,
    compare_solvers,
    expected_single_pipe_solution,
    export_solver_comparison_csv,
    validate_medium_generic_network_result,
    validate_result_basic,
    validate_single_pipe_result,
)
from hn3ttk.connections import (
    Connection,
    CustomFactorPolynomialConnection,
    LinearInterpolationConnection,
    PipeDarcy,
    PipeFixedPowerLaw,
    PipeLocalPowerLaw,
    PolynomialRegressionConnection,
    SplineSecantExtrapolationConnection,
    SplineInterpolationConnection,
    SplineTangentExtrapolationConnection,
    available_connection_types,
    connection_from_dict,
    connection_to_dict,
    register_connection_type,
)
from hn3ttk.nodes import (
    ConfigurableNode,
    DemandNode,
    FixedHeadNode,
    InjectionNode,
    JunctionNode,
    Node,
    ReservoirNode,
    available_node_types,
    node_from_dict,
    node_to_dict,
    register_node_type,
)
from hn3ttk.results import (
    export_links_csv,
    export_nodes_csv,
    export_residuals_csv,
    export_result_folder,
    export_result_json,
    export_state_json,
    export_unknown_heads_csv,
    links_table,
    nodes_table,
    print_result_summary,
    residuals_table,
    result_summary,
    unknown_heads_table,
)
from hn3ttk.solvers import (
    SolverResult,
    solve_alpha_continuation_damped_newton,
    solve_alpha_continuation_newton,
    solve_alpha_continuation_scipy_least_squares,
    solve_alpha_continuation_scipy_root,
    solve_damped_newton_raphson,
    solve_newton_raphson,
    solve_scipy_least_squares,
    solve_scipy_root,
)
from hn3ttk.system import (
    HydraulicSystem,
    Link,
    system_from_dict,
    system_to_dict,
)

__all__ = [
    # Nodes
    "Node",
    "ConfigurableNode",
    "JunctionNode",
    "FixedHeadNode",
    "ReservoirNode",
    "DemandNode",
    "InjectionNode",
    "node_from_dict",
    "node_to_dict",
    "available_node_types",
    "register_node_type",

    # Connections
    "Connection",
    "PipeDarcy",
    "PipeLocalPowerLaw",
    "PipeFixedPowerLaw",
    "LinearInterpolationConnection",
    "PolynomialRegressionConnection",
    "SplineSecantExtrapolationConnection",
    "SplineInterpolationConnection",
    "SplineTangentExtrapolationConnection",
    "CustomFactorPolynomialConnection",
    "connection_from_dict",
    "connection_to_dict",
    "available_connection_types",
    "register_connection_type",

    # System
    "HydraulicSystem",
    "Link",
    "system_from_dict",
    "system_to_dict",

    # Solvers
    "SolverResult",
    "solve_newton_raphson",
    "solve_damped_newton_raphson",
    "solve_alpha_continuation_newton",
    "solve_alpha_continuation_damped_newton",
    "solve_scipy_root",
    "solve_alpha_continuation_scipy_root",
    "solve_scipy_least_squares",
    "solve_alpha_continuation_scipy_least_squares",

    # Results
    "nodes_table",
    "links_table",
    "residuals_table",
    "unknown_heads_table",
    "result_summary",
    "print_result_summary",
    "export_state_json",
    "export_result_json",
    "export_nodes_csv",
    "export_links_csv",
    "export_residuals_csv",
    "export_unknown_heads_csv",
    "export_result_folder",

    # Benchmarks
    "build_single_pipe_system",
    "build_parallel_pipes_system",
    "build_three_reservoirs_system",
    "build_hardy_cross_loop_system",
    "build_medium_generic_network_system",
    "expected_single_pipe_solution",
    "validate_result_basic",
    "validate_single_pipe_result",
    "validate_medium_generic_network_result",
    "available_default_solvers",
    "compare_solvers",
    "export_solver_comparison_csv",
]
