from __future__ import annotations

from math import pi

from hn3ttk.connections import (
    LinearInterpolationConnection,
    PipeDarcy,
    PipeFixedPowerLaw,
)
from hn3ttk.nodes import DemandNode, InjectionNode, JunctionNode, ReservoirNode
from hn3ttk.system import HydraulicSystem


def _add_pipe_link(
    system: HydraulicSystem,
    *,
    connection_id: str,
    from_node_id: str,
    to_node_id: str,
    link_id: str,
    k: float,
    n: float = 2.0,
) -> None:
    """Create a PipeFixedPowerLaw connection and attach it to the system."""
    system.add_connection(
        PipeFixedPowerLaw(
            id=connection_id,
            parameters={
                "k": float(k),
                "n": float(n),
            },
        )
    )
    system.connect(
        connection_id=connection_id,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        link_id=link_id,
    )


def _add_darcy_pipe_link(
    system: HydraulicSystem,
    *,
    connection_id: str,
    from_node_id: str,
    to_node_id: str,
    link_id: str,
    length: float,
    diameter: float,
    roughness: float,
    kinematic_viscosity: float,
    gravity: float = 9.81,
) -> None:
    """Create a PipeDarcy connection and attach it to the system."""
    system.add_connection(
        PipeDarcy(
            id=connection_id,
            parameters={
                "length": float(length),
                "diameter": float(diameter),
                "roughness": float(roughness),
                "kinematic_viscosity": float(kinematic_viscosity),
                "gravity": float(gravity),
            },
        )
    )
    system.connect(
        connection_id=connection_id,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        link_id=link_id,
    )


def build_single_pipe_system() -> HydraulicSystem:
    """Build the canonical reservoir -> pipe -> demand validation case."""
    system = HydraulicSystem(id="single_pipe_system")

    system.add_node(
        ReservoirNode(
            id="reservoir",
            parameters={
                "elevation": 0.0,
                "head": 10.0,
            },
        )
    )
    system.add_node(
        DemandNode(
            id="demand",
            parameters={
                "elevation": 0.0,
                "initial_head": 5.0,
                "demand": 0.1,
            },
        )
    )

    _add_pipe_link(
        system,
        connection_id="pipe",
        from_node_id="reservoir",
        to_node_id="demand",
        link_id="link_1",
        k=100.0,
        n=2.0,
    )

    return system


def build_parallel_pipes_system() -> HydraulicSystem:
    """Build a small system with two parallel pipes feeding one junction."""
    system = HydraulicSystem(id="parallel_pipes_system")

    system.add_node(
        ReservoirNode(
            id="reservoir_high",
            parameters={
                "elevation": 0.0,
                "head": 20.0,
            },
        )
    )
    system.add_node(
        ReservoirNode(
            id="reservoir_low",
            parameters={
                "elevation": 0.0,
                "head": 10.0,
            },
        )
    )
    system.add_node(
        JunctionNode(
            id="junction",
            parameters={
                "elevation": 0.0,
                "initial_head": 15.0,
                "external_flow": 0.0,
            },
        )
    )

    _add_pipe_link(
        system,
        connection_id="pipe_1",
        from_node_id="reservoir_high",
        to_node_id="junction",
        link_id="link_high_junction_1",
        k=100.0,
    )
    _add_pipe_link(
        system,
        connection_id="pipe_2",
        from_node_id="reservoir_high",
        to_node_id="junction",
        link_id="link_high_junction_2",
        k=400.0,
    )
    _add_pipe_link(
        system,
        connection_id="pipe_3",
        from_node_id="junction",
        to_node_id="reservoir_low",
        link_id="link_junction_low",
        k=100.0,
    )

    return system


def build_three_reservoirs_system() -> HydraulicSystem:
    """Build a central junction connected to three fixed-head reservoirs."""
    system = HydraulicSystem(id="three_reservoirs_system")

    system.add_node(
        ReservoirNode(
            id="reservoir_high_1",
            parameters={
                "elevation": 0.0,
                "head": 30.0,
            },
        )
    )
    system.add_node(
        ReservoirNode(
            id="reservoir_high_2",
            parameters={
                "elevation": 0.0,
                "head": 20.0,
            },
        )
    )
    system.add_node(
        ReservoirNode(
            id="reservoir_low",
            parameters={
                "elevation": 0.0,
                "head": 10.0,
            },
        )
    )
    system.add_node(
        JunctionNode(
            id="central_junction",
            parameters={
                "elevation": 0.0,
                "initial_head": 15.0,
                "external_flow": 0.0,
            },
        )
    )

    _add_pipe_link(
        system,
        connection_id="pipe_high_1",
        from_node_id="reservoir_high_1",
        to_node_id="central_junction",
        link_id="link_high_1_junction",
        k=100.0,
    )
    _add_pipe_link(
        system,
        connection_id="pipe_high_2",
        from_node_id="reservoir_high_2",
        to_node_id="central_junction",
        link_id="link_high_2_junction",
        k=200.0,
    )
    _add_pipe_link(
        system,
        connection_id="pipe_low",
        from_node_id="central_junction",
        to_node_id="reservoir_low",
        link_id="link_junction_low",
        k=150.0,
    )

    return system


def build_larock_example_2_6_parallel_branch_system() -> HydraulicSystem:
    """
    Build Larock Example Problem 2.6 using fixed power-law pipes.

    Source:
        Larock, Jeppson, Watters, *Hydraulics of Pipeline Systems*,
        Example Problem 2.6.

    Units are kept exactly as in the textbook example: feet and ft3/s.
    """
    system = HydraulicSystem(
        id="larock_example_2_6_parallel_branch_system",
        metadata={
            "source": "Larock Example Problem 2.6",
            "units": "ft, ft3/s",
        },
    )

    system.add_node(
        ReservoirNode(
            id="reservoir_high",
            parameters={
                "elevation": 40.0,
                "head": 40.0,
            },
        )
    )
    system.add_node(
        ReservoirNode(
            id="reservoir_low",
            parameters={
                "elevation": 0.0,
                "head": 0.0,
            },
        )
    )
    system.add_node(
        JunctionNode(
            id="split_junction",
            parameters={
                "elevation": 0.0,
                "initial_head": 13.4,
                "external_flow": 0.0,
            },
        )
    )

    _add_pipe_link(
        system,
        connection_id="pipe_12_in",
        from_node_id="reservoir_high",
        to_node_id="split_junction",
        link_id="link_12_in",
        k=2.01,
        n=2.0,
    )
    _add_pipe_link(
        system,
        connection_id="pipe_10_in",
        from_node_id="split_junction",
        to_node_id="reservoir_low",
        link_id="link_10_in",
        k=2.51,
        n=2.0,
    )
    _add_pipe_link(
        system,
        connection_id="pipe_8_in",
        from_node_id="split_junction",
        to_node_id="reservoir_low",
        link_id="link_8_in",
        k=7.65,
        n=2.0,
    )

    return system


def build_larock_example_2_7_three_reservoirs_system() -> HydraulicSystem:
    """
    Build Larock Example Problem 2.7, the classical three-reservoir problem.

    Source:
        Larock, Jeppson, Watters, *Hydraulics of Pipeline Systems*,
        Example Problem 2.7.

    Units are kept exactly as in the textbook example: meters and m3/s.
    """
    system = HydraulicSystem(
        id="larock_example_2_7_three_reservoirs_system",
        metadata={
            "source": "Larock Example Problem 2.7",
            "units": "m, m3/s",
        },
    )

    for node_id, head in (
        ("reservoir_100_m", 100.0),
        ("reservoir_85_m", 85.0),
        ("reservoir_60_m", 60.0),
    ):
        system.add_node(
            ReservoirNode(
                id=node_id,
                parameters={
                    "elevation": head,
                    "head": head,
                },
            )
        )

    system.add_node(
        DemandNode(
            id="junction",
            parameters={
                "elevation": 100.0,
                "initial_head": 83.7,
                "demand": 0.06,
            },
        )
    )

    _add_pipe_link(
        system,
        connection_id="pipe_1",
        from_node_id="reservoir_100_m",
        to_node_id="junction",
        link_id="link_1",
        k=1469.0,
        n=1.974,
    )
    _add_pipe_link(
        system,
        connection_id="pipe_2",
        from_node_id="reservoir_85_m",
        to_node_id="junction",
        link_id="link_2",
        k=2432.0,
        n=1.927,
    )
    _add_pipe_link(
        system,
        connection_id="pipe_3",
        from_node_id="junction",
        to_node_id="reservoir_60_m",
        link_id="link_3",
        k=5646.0,
        n=1.971,
    )

    return system


def build_larock_problem_2_13_single_pipe_system() -> HydraulicSystem:
    """
    Build Larock Problem 2.13 as a split single-pipe Darcy benchmark.

    The textbook problem is a single pipe between two reservoirs. We split the
    pipe into two identical halves and insert one zero-demand junction so the
    head-based network solver still has one unknown hydraulic head.

    Source:
        Larock, Jeppson, Watters, *Hydraulics of Pipeline Systems*,
        Problem 2.13 with selected answer in Appendix D.
    """
    system = HydraulicSystem(
        id="larock_problem_2_13_single_pipe_system",
        metadata={
            "source": "Larock Problem 2.13",
            "units": "m, m3/s",
        },
    )

    system.add_node(
        ReservoirNode(
            id="reservoir_high",
            parameters={
                "elevation": 6.1,
                "head": 6.1,
            },
        )
    )
    system.add_node(
        ReservoirNode(
            id="reservoir_low",
            parameters={
                "elevation": 0.0,
                "head": 0.0,
            },
        )
    )
    system.add_node(
        JunctionNode(
            id="midpoint",
            parameters={
                "elevation": 0.0,
                "initial_head": 3.05,
                "external_flow": 0.0,
            },
        )
    )

    darcy_kwargs = {
        "length": 457.0 / 2.0,
        "diameter": 0.10,
        "roughness": 0.00061,
        "kinematic_viscosity": 1.004e-6,
    }

    _add_darcy_pipe_link(
        system,
        connection_id="pipe_upstream",
        from_node_id="reservoir_high",
        to_node_id="midpoint",
        link_id="link_upstream",
        **darcy_kwargs,
    )
    _add_darcy_pipe_link(
        system,
        connection_id="pipe_downstream",
        from_node_id="midpoint",
        to_node_id="reservoir_low",
        link_id="link_downstream",
        **darcy_kwargs,
    )

    return system


def build_larock_problem_4_1a_system() -> HydraulicSystem:
    """
    Build Larock Problem 4.1a, the six-node Darcy network from Chapter 4.

    Source:
        Larock, Jeppson, Watters, *Hydraulics of Pipeline Systems*,
        Problem 4.1a with selected discharge answer in Appendix D, Problem 4.23(a).

    Units are kept exactly as in the textbook problem: meters and m3/s.
    """
    system = HydraulicSystem(
        id="larock_problem_4_1a_system",
        metadata={
            "source": "Larock Problem 4.1a / Appendix D Problem 4.23(a)",
            "units": "m, m3/s",
        },
    )

    system.add_node(
        ReservoirNode(
            id="node_1",
            parameters={
                "elevation": 0.0,
                "head": 300.0,
            },
        )
    )

    for node_id, initial_head, external_flow in (
        ("node_2", 293.8, 0.0),
        ("node_3", 231.4, -0.5),
        ("node_4", 225.3, -0.25),
        ("node_5", 293.4, -0.25),
        ("node_6", 300.4, 0.5),
    ):
        system.add_node(
            JunctionNode(
                id=node_id,
                parameters={
                    "elevation": 0.0,
                    "initial_head": initial_head,
                    "external_flow": external_flow,
                },
            )
        )

    darcy_kwargs = {
        "roughness": 0.00002,
        "kinematic_viscosity": 1.0e-6,
    }

    _add_darcy_pipe_link(
        system,
        connection_id="pipe_1",
        from_node_id="node_1",
        to_node_id="node_2",
        link_id="link_1",
        length=500.0,
        diameter=0.5,
        **darcy_kwargs,
    )
    _add_darcy_pipe_link(
        system,
        connection_id="pipe_2",
        from_node_id="node_2",
        to_node_id="node_3",
        link_id="link_2",
        length=500.0,
        diameter=0.3,
        **darcy_kwargs,
    )
    _add_darcy_pipe_link(
        system,
        connection_id="pipe_3",
        from_node_id="node_1",
        to_node_id="node_6",
        link_id="link_3",
        length=600.0,
        diameter=0.5,
        **darcy_kwargs,
    )
    _add_darcy_pipe_link(
        system,
        connection_id="pipe_4",
        from_node_id="node_2",
        to_node_id="node_5",
        link_id="link_4",
        length=600.0,
        diameter=0.4,
        **darcy_kwargs,
    )
    _add_darcy_pipe_link(
        system,
        connection_id="pipe_5",
        from_node_id="node_3",
        to_node_id="node_4",
        link_id="link_5",
        length=600.0,
        diameter=0.2,
        **darcy_kwargs,
    )
    _add_darcy_pipe_link(
        system,
        connection_id="pipe_6",
        from_node_id="node_6",
        to_node_id="node_5",
        link_id="link_6",
        length=500.0,
        diameter=0.4,
        **darcy_kwargs,
    )
    _add_darcy_pipe_link(
        system,
        connection_id="pipe_7",
        from_node_id="node_5",
        to_node_id="node_4",
        link_id="link_7",
        length=500.0,
        diameter=0.2,
        **darcy_kwargs,
    )

    return system


def build_larock_problem_4_1b_system() -> HydraulicSystem:
    """
    Build Larock Problem 4.1b, the pumped Darcy network from Chapter 4.

    Source:
        Larock, Jeppson, Watters, *Hydraulics of Pipeline Systems*,
        Problem 4.1b with selected discharge answer in Appendix D, Problem 4.23(b).

    The textbook's pipe 7 contains both a pump and a downstream 0.6 m pipe.
    We model that branch as two connections joined by one zero-demand midpoint so the
    benchmark can still validate the published branch discharge.

    Units are kept exactly as in the textbook problem: meters and m3/s.
    """
    system = HydraulicSystem(
        id="larock_problem_4_1b_system",
        metadata={
            "source": "Larock Problem 4.1b / Appendix D Problem 4.23(b)",
            "units": "m, m3/s",
        },
    )

    system.add_node(
        ReservoirNode(
            id="reservoir_100_m",
            parameters={
                "elevation": 0.0,
                "head": 100.0,
            },
        )
    )
    system.add_node(
        ReservoirNode(
            id="reservoir_80_m",
            parameters={
                "elevation": 0.0,
                "head": 80.0,
            },
        )
    )

    for node_id, initial_head, external_flow in (
        ("node_1", 100.0, -0.1),
        ("node_2", 99.9, -0.15),
        ("node_3", 98.9, -0.18),
        ("node_4", 101.4, -0.1),
        ("pipe_7_midpoint", 104.6, 0.0),
    ):
        system.add_node(
            JunctionNode(
                id=node_id,
                parameters={
                    "elevation": 0.0,
                    "initial_head": initial_head,
                    "external_flow": external_flow,
                },
            )
        )

    darcy_kwargs = {
        "roughness": 0.00002,
        "kinematic_viscosity": 1.0e-6,
    }

    _add_darcy_pipe_link(
        system,
        connection_id="pipe_1",
        from_node_id="reservoir_100_m",
        to_node_id="node_1",
        link_id="link_1",
        length=500.0,
        diameter=0.4,
        **darcy_kwargs,
    )
    _add_darcy_pipe_link(
        system,
        connection_id="pipe_2",
        from_node_id="node_1",
        to_node_id="node_2",
        link_id="link_2",
        length=1500.0,
        diameter=0.5,
        **darcy_kwargs,
    )
    _add_darcy_pipe_link(
        system,
        connection_id="pipe_3",
        from_node_id="node_1",
        to_node_id="node_3",
        link_id="link_3",
        length=1400.0,
        diameter=0.25,
        **darcy_kwargs,
    )
    _add_darcy_pipe_link(
        system,
        connection_id="pipe_4",
        from_node_id="node_4",
        to_node_id="node_3",
        link_id="link_4",
        length=1600.0,
        diameter=0.45,
        **darcy_kwargs,
    )
    _add_darcy_pipe_link(
        system,
        connection_id="pipe_5",
        from_node_id="node_4",
        to_node_id="node_2",
        link_id="link_5",
        length=900.0,
        diameter=0.4,
        **darcy_kwargs,
    )
    _add_darcy_pipe_link(
        system,
        connection_id="pipe_6",
        from_node_id="node_4",
        to_node_id="node_1",
        link_id="link_6",
        length=1800.0,
        diameter=0.5,
        **darcy_kwargs,
    )

    system.add_connection(
        LinearInterpolationConnection(
            id="pump_7",
            parameters={
                "flow_rates": [0.2, 0.4, 0.7],
                "head_losses": [30.0, 27.0, 21.0],
                "extrapolate": True,
            },
        )
    )
    system.connect(
        connection_id="pump_7",
        from_node_id="reservoir_80_m",
        to_node_id="pipe_7_midpoint",
        link_id="pump_link_7",
    )
    _add_darcy_pipe_link(
        system,
        connection_id="pipe_7",
        from_node_id="pipe_7_midpoint",
        to_node_id="node_4",
        link_id="link_7",
        length=900.0,
        diameter=0.6,
        **darcy_kwargs,
    )

    return system


def build_larock_problem_4_8_parallel_pipes_system() -> HydraulicSystem:
    """
    Build Larock Problem 4.8 with a fixed total inflow and two parallel branches.

    The branch with the open globe valve is represented by embedding the local
    loss coefficient directly into the fixed power-law coefficient.

    Source:
        Larock, Jeppson, Watters, *Hydraulics of Pipeline Systems*,
        Problem 4.8 with selected answer in Appendix D.
    """
    system = HydraulicSystem(
        id="larock_problem_4_8_parallel_pipes_system",
        metadata={
            "source": "Larock Problem 4.8",
            "units": "ft, ft3/s",
        },
    )

    system.add_node(
        InjectionNode(
            id="upstream_node",
            parameters={
                "elevation": 0.0,
                "initial_head": 18.6,
                "injection": 3.0,
            },
        )
    )
    system.add_node(
        ReservoirNode(
            id="downstream_reservoir",
            parameters={
                "elevation": 0.0,
                "head": 0.0,
            },
        )
    )

    diameter_6_in = 6.0 / 12.0
    diameter_8_in = 8.0 / 12.0
    area_6_in = pi * diameter_6_in**2 / 4.0
    area_8_in = pi * diameter_8_in**2 / 4.0

    valve_branch_k = (
        (0.018 * 1500.0 / diameter_6_in) + 10.0
    ) / (2.0 * 32.2 * area_6_in**2)
    plain_branch_k = (
        0.015 * 1400.0 / diameter_8_in
    ) / (2.0 * 32.2 * area_8_in**2)

    _add_pipe_link(
        system,
        connection_id="branch_with_globe_valve",
        from_node_id="upstream_node",
        to_node_id="downstream_reservoir",
        link_id="link_branch_1",
        k=valve_branch_k,
        n=2.0,
    )
    _add_pipe_link(
        system,
        connection_id="plain_branch",
        from_node_id="upstream_node",
        to_node_id="downstream_reservoir",
        link_id="link_branch_2",
        k=plain_branch_k,
        n=2.0,
    )

    return system


def build_hardy_cross_loop_system() -> HydraulicSystem:
    """
    Build a looped network inspired by classical Hardy-Cross examples.

    Topology:
        source -> demand_1
        demand_1 -> demand_2
        demand_2 -> demand_3
        demand_3 -> reservoir_low
        demand_1 -> demand_3

    The branch demand_1 -> demand_2 -> demand_3 and the shortcut
    demand_1 -> demand_3 provide two alternative paths and therefore a small
    looped benchmark in the graph-theoretic sense.
    """
    system = HydraulicSystem(id="hardy_cross_loop_system")

    system.add_node(
        ReservoirNode(
            id="source",
            parameters={
                "elevation": 0.0,
                "head": 50.0,
            },
        )
    )
    system.add_node(
        ReservoirNode(
            id="reservoir_low",
            parameters={
                "elevation": 0.0,
                "head": 35.0,
            },
        )
    )
    system.add_node(
        DemandNode(
            id="demand_1",
            parameters={
                "elevation": 0.0,
                "initial_head": 46.0,
                "demand": 0.03,
            },
        )
    )
    system.add_node(
        DemandNode(
            id="demand_2",
            parameters={
                "elevation": 0.0,
                "initial_head": 44.0,
                "demand": 0.02,
            },
        )
    )
    system.add_node(
        DemandNode(
            id="demand_3",
            parameters={
                "elevation": 0.0,
                "initial_head": 42.0,
                "demand": 0.04,
            },
        )
    )

    _add_pipe_link(
        system,
        connection_id="pipe_source_d1",
        from_node_id="source",
        to_node_id="demand_1",
        link_id="link_source_d1",
        k=80.0,
    )
    _add_pipe_link(
        system,
        connection_id="pipe_d1_d2",
        from_node_id="demand_1",
        to_node_id="demand_2",
        link_id="link_d1_d2",
        k=140.0,
    )
    _add_pipe_link(
        system,
        connection_id="pipe_d2_d3",
        from_node_id="demand_2",
        to_node_id="demand_3",
        link_id="link_d2_d3",
        k=120.0,
    )
    _add_pipe_link(
        system,
        connection_id="pipe_d3_low",
        from_node_id="demand_3",
        to_node_id="reservoir_low",
        link_id="link_d3_low",
        k=90.0,
    )
    _add_pipe_link(
        system,
        connection_id="pipe_d1_d3",
        from_node_id="demand_1",
        to_node_id="demand_3",
        link_id="link_d1_d3",
        k=160.0,
    )

    return system


def build_medium_generic_network_system() -> HydraulicSystem:
    r"""
    Build a medium-size generic hydraulic network.

    ASCII sketch:

        reservoir_source
              | \
              |  \
             j1   j2
             |\   |\
             | \  | \
             |  \ |  \
             j3---+---j5
              \       |
               \      |
                j4----+
                  \   |
                   \  |
                     j6 ---- reservoir_low

    Link orientation is only a reference convention. Negative flow means the
    actual direction is opposite to the stored link orientation.
    """
    system = HydraulicSystem(id="medium_generic_network_system")

    system.add_node(
        ReservoirNode(
            id="reservoir_source",
            parameters={
                "elevation": 0.0,
                "head": 60.0,
            },
        )
    )
    system.add_node(
        ReservoirNode(
            id="reservoir_low",
            parameters={
                "elevation": 0.0,
                "head": 40.0,
            },
        )
    )

    demand_data = [
        ("junction_1", 55.0, 0.04),
        ("junction_2", 54.0, 0.03),
        ("junction_3", 52.0, 0.05),
        ("junction_4", 50.0, 0.04),
        ("junction_5", 48.0, 0.03),
        ("junction_6", 46.0, 0.02),
    ]

    for node_id, initial_head, demand in demand_data:
        system.add_node(
            DemandNode(
                id=node_id,
                parameters={
                    "elevation": 0.0,
                    "initial_head": initial_head,
                    "demand": demand,
                },
            )
        )

    pipe_data = [
        ("pipe_source_j1", "reservoir_source", "junction_1", "link_source_j1", 80.0),
        ("pipe_source_j2", "reservoir_source", "junction_2", "link_source_j2", 120.0),
        ("pipe_j1_j3", "junction_1", "junction_3", "link_j1_j3", 100.0),
        ("pipe_j2_j3", "junction_2", "junction_3", "link_j2_j3", 150.0),
        ("pipe_j3_j4", "junction_3", "junction_4", "link_j3_j4", 90.0),
        ("pipe_j4_j5", "junction_4", "junction_5", "link_j4_j5", 110.0),
        ("pipe_j5_j6", "junction_5", "junction_6", "link_j5_j6", 130.0),
        ("pipe_j6_low", "junction_6", "reservoir_low", "link_j6_low", 100.0),
        ("pipe_j2_j5", "junction_2", "junction_5", "link_j2_j5", 180.0),
        ("pipe_j1_j4", "junction_1", "junction_4", "link_j1_j4", 200.0),
        ("pipe_j3_j6", "junction_3", "junction_6", "link_j3_j6", 220.0),
    ]

    for connection_id, from_node_id, to_node_id, link_id, k in pipe_data:
        _add_pipe_link(
            system,
            connection_id=connection_id,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            link_id=link_id,
            k=k,
        )

    return system
