from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from hn3ttk.connections import Connection
from hn3ttk.nodes import Node
from hn3ttk.system.link import Link


@dataclass
class HydraulicSystem:
    """
    Hydraulic network system.

    The system owns:
        - nodes
        - connections
        - links between nodes and connections

    Connections do not know which nodes they connect.
    Nodes do not know which connections are attached to them.

    The system is responsible for topology and residual assembly.

    Link convention:
        q > 0 means flow from link.from_node_id to link.to_node_id

    Head convention:
        delta_h = H_to - H_from

    Constructor arguments
    ---------------------
    id:
        Optional system identifier.
    nodes:
        Dictionary mapping node ids to node objects.
    connections:
        Dictionary mapping connection ids to connection objects.
    links:
        Dictionary mapping link ids to link objects.
    metadata:
        Free-form user metadata stored together with the system.
    """

    id: str = "hydraulic_system"
    nodes: dict[str, Node] = field(default_factory=dict)
    connections: dict[str, Connection] = field(default_factory=dict)
    links: dict[str, Link] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    # ------------------------------------------------------------------
    # Basic validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """
        Validate system containers and cross-references.

        This checks container types, id consistency between dictionary keys and
        stored objects, and that each link references existing nodes and
        connections.
        """
        if not isinstance(self.id, str):
            raise TypeError("System id must be a string.")

        if not self.id:
            raise ValueError("System id cannot be empty.")

        if not isinstance(self.nodes, dict):
            raise TypeError("System nodes must be a dictionary.")

        if not isinstance(self.connections, dict):
            raise TypeError("System connections must be a dictionary.")

        if not isinstance(self.links, dict):
            raise TypeError("System links must be a dictionary.")

        if not isinstance(self.metadata, dict):
            raise TypeError("System metadata must be a dictionary.")

        for node_id, node in self.nodes.items():
            if node_id != node.id:
                raise ValueError(
                    f"Node dictionary key '{node_id}' does not match "
                    f"node id '{node.id}'."
                )

        for connection_id, connection in self.connections.items():
            if connection_id != connection.id:
                raise ValueError(
                    "Connection dictionary key "
                    f"'{connection_id}' does not match "
                    f"connection id '{connection.id}'."
                )

        for link_id, link in self.links.items():
            if link_id != link.id:
                raise ValueError(
                    f"Link dictionary key '{link_id}' does not match "
                    f"link id '{link.id}'."
                )

            self._validate_link_references(link)

    def _validate_link_references(self, link: Link) -> None:
        """Validate that a link references existing nodes and connection."""
        if link.connection_id not in self.connections:
            raise ValueError(
                f"Link '{link.id}' references unknown connection "
                f"'{link.connection_id}'."
            )

        if link.from_node_id not in self.nodes:
            raise ValueError(
                f"Link '{link.id}' references unknown from_node "
                f"'{link.from_node_id}'."
            )

        if link.to_node_id not in self.nodes:
            raise ValueError(
                f"Link '{link.id}' references unknown to_node "
                f"'{link.to_node_id}'."
            )

    # ------------------------------------------------------------------
    # Add objects
    # ------------------------------------------------------------------

    def add_node(self, node: Node) -> None:
        """
        Add a node to the system.

        Raises
        ------
        TypeError
            If ``node`` is not a :class:`Node`.
        ValueError
            If another node with the same id already exists.
        """
        if not isinstance(node, Node):
            raise TypeError("Expected a Node object.")

        if node.id in self.nodes:
            raise ValueError(f"Node id '{node.id}' already exists.")

        self.nodes[node.id] = node

    def add_connection(self, connection: Connection) -> None:
        """Add a connection to the system and enforce unique ids."""
        if not isinstance(connection, Connection):
            raise TypeError("Expected a Connection object.")

        if connection.id in self.connections:
            raise ValueError(f"Connection id '{connection.id}' already exists.")

        self.connections[connection.id] = connection

    def add_link(self, link: Link) -> None:
        """
        Add a topological link to the system.

        The referenced nodes and connection must already exist in the system.
        """
        if not isinstance(link, Link):
            raise TypeError("Expected a Link object.")

        if link.id in self.links:
            raise ValueError(f"Link id '{link.id}' already exists.")

        self._validate_link_references(link)

        self.links[link.id] = link

    def connect(
        self,
        connection_id: str,
        from_node_id: str,
        to_node_id: str,
        link_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Link:
        """
        Create and add a link between a connection and two nodes.

        Parameters
        ----------
        connection_id:
            Existing connection id to place in the network.
        from_node_id:
            Start node for the positive flow orientation.
        to_node_id:
            End node for the positive flow orientation.
        link_id:
            Optional explicit id for the created link.
        metadata:
            Optional metadata dictionary copied into the link.

        Returns
        -------
        Link
            The newly created and inserted link object.
        """
        link_kwargs: dict[str, Any] = {
            "connection_id": connection_id,
            "from_node_id": from_node_id,
            "to_node_id": to_node_id,
            "metadata": {} if metadata is None else dict(metadata),
        }

        if link_id is not None:
            link_kwargs["id"] = link_id

        link = Link(**link_kwargs)
        self.add_link(link)

        return link

    # ------------------------------------------------------------------
    # Get objects
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> Node:
        """Return the node with the requested id."""
        return self.nodes[node_id]

    def get_connection(self, connection_id: str) -> Connection:
        """Return the connection with the requested id."""
        return self.connections[connection_id]

    def get_link(self, link_id: str) -> Link:
        """Return the link with the requested id."""
        return self.links[link_id]

    # ------------------------------------------------------------------
    # Node groups
    # ------------------------------------------------------------------

    def fixed_head_node_ids(self) -> list[str]:
        """Return the ids of all fixed-head nodes in insertion order."""
        return [
            node_id
            for node_id, node in self.nodes.items()
            if node.is_fixed_head()
        ]

    def unknown_head_node_ids(self) -> list[str]:
        """Return the ids of all unknown-head nodes in insertion order."""
        return [
            node_id
            for node_id, node in self.nodes.items()
            if node.is_unknown_head()
        ]

    def initial_unknown_heads(self) -> list[float]:
        """Return the initial head guesses for all unknown-head nodes."""
        return [
            self.nodes[node_id].initial_head()
            for node_id in self.unknown_head_node_ids()
        ]

    def unknown_head_index(self) -> dict[str, int]:
        """
        Return unknown-head node ids mapped to solver/Jacobian indices.

        The ordering matches :meth:`unknown_head_node_ids`.
        """
        return {
            node_id: index
            for index, node_id in enumerate(self.unknown_head_node_ids())
        }

    # ------------------------------------------------------------------
    # Hydraulic evaluation helpers
    # ------------------------------------------------------------------

    def heads_from_unknowns(
        self,
        unknown_heads: list[float] | tuple[float, ...],
        alpha: float = 1.0,
    ) -> dict[str, float]:
        """
        Build a complete node-head dictionary from unknown-head values.

        Fixed-head nodes are filled using node.fixed_head(alpha).
        Unknown-head nodes are filled from the supplied vector.
        """
        unknown_node_ids = self.unknown_head_node_ids()

        if len(unknown_heads) != len(unknown_node_ids):
            raise ValueError(
                "Number of unknown head values does not match number of "
                "unknown-head nodes."
            )

        heads: dict[str, float] = {}

        for node_id, node in self.nodes.items():
            if node.is_fixed_head():
                heads[node_id] = node.fixed_head(alpha)

        for node_id, head in zip(unknown_node_ids, unknown_heads):
            heads[node_id] = float(head)

        return heads

    def link_delta_h(self, link_id: str, heads: dict[str, float]) -> float:
        """
        Return delta_h across a link.

        Convention:
            delta_h = H_to - H_from
        """
        link = self.get_link(link_id)

        h_from = float(heads[link.from_node_id])
        h_to = float(heads[link.to_node_id])

        return h_to - h_from

    def link_flow_rate(self, link_id: str, heads: dict[str, float]) -> float:
        """
        Return signed flow rate through a link.

        Convention:
            q > 0 means flow from from_node_id to to_node_id.
        """
        link = self.get_link(link_id)
        connection = self.get_connection(link.connection_id)

        delta_h = self.link_delta_h(link_id, heads)

        return connection.flow_rate(delta_h)

    def all_link_flow_rates(self, heads: dict[str, float]) -> dict[str, float]:
        """Return signed flow rate for every link."""
        return {
            link_id: self.link_flow_rate(link_id, heads)
            for link_id in self.links
        }

    # ------------------------------------------------------------------
    # Residual assembly
    # ------------------------------------------------------------------

    def residuals_by_node(
        self,
        unknown_heads: list[float] | tuple[float, ...],
        alpha: float = 1.0,
    ) -> dict[str, float]:
        """
        Assemble mass-balance residuals for unknown-head nodes and return them
        as a dictionary indexed by node id.

        Residual convention:

            residual = external_flow + inflow_from_links - outflow_to_links

        For each link:
            q > 0 from from_node to to_node

            contribution to from_node = -q
            contribution to to_node   = +q

        At solution:
            residual = 0

        Units:
            m³/s
        """
        heads = self.heads_from_unknowns(unknown_heads, alpha)

        residual_by_node = {
            node_id: self.nodes[node_id].external_flow(alpha)
            for node_id in self.unknown_head_node_ids()
        }

        for link_id, link in self.links.items():
            q = self.link_flow_rate(link_id, heads)

            if link.from_node_id in residual_by_node:
                residual_by_node[link.from_node_id] -= q

            if link.to_node_id in residual_by_node:
                residual_by_node[link.to_node_id] += q

        return residual_by_node

    def nodal_flow_residuals(
        self,
        unknown_heads: list[float] | tuple[float, ...],
        alpha: float = 1.0,
    ) -> list[float]:
        """
        Assemble mass-balance residuals for unknown-head nodes.

        This method returns the residual vector in the same order as
        unknown_head_node_ids(), so it is suitable for nonlinear solvers.

        Residual convention:

            residual = external_flow + inflow_from_links - outflow_to_links

        At solution:
            residual = 0

        Units:
            m³/s
        """
        residual_by_node = self.residuals_by_node(unknown_heads, alpha)

        return [
            residual_by_node[node_id]
            for node_id in self.unknown_head_node_ids()
        ]

    def max_abs_residual(
        self,
        unknown_heads: list[float] | tuple[float, ...],
        alpha: float = 1.0,
    ) -> float:
        """
        Return the maximum absolute nodal residual.

        Units:
            m³/s
        """
        residuals = self.residuals_by_node(unknown_heads, alpha)

        if not residuals:
            return 0.0

        return max(abs(value) for value in residuals.values())

    def dense_jacobian(
        self,
        unknown_heads: list[float] | tuple[float, ...],
        alpha: float = 1.0,
        derivative_mode: str = "default",
    ) -> np.ndarray:
        """
        Assemble the dense Jacobian dR/dH for unknown-head node residuals.
        """
        Connection._validate_jacobian_derivative_mode(derivative_mode)

        unknown_node_ids = self.unknown_head_node_ids()
        unknown_index = self.unknown_head_index()
        n_unknowns = len(unknown_node_ids)
        jacobian = np.zeros((n_unknowns, n_unknowns), dtype=float)

        if n_unknowns == 0:
            return jacobian

        heads = self.heads_from_unknowns(unknown_heads, alpha)

        for link_id, link in self.links.items():
            connection = self.get_connection(link.connection_id)
            delta_h = self.link_delta_h(link_id, heads)
            dq_dh = connection.jacobian_derivative(
                delta_h,
                method=derivative_mode,
            )

            from_index = unknown_index.get(link.from_node_id)
            to_index = unknown_index.get(link.to_node_id)

            if from_index is not None:
                jacobian[from_index, from_index] += dq_dh

                if to_index is not None:
                    jacobian[from_index, to_index] -= dq_dh

            if to_index is not None:
                if from_index is not None:
                    jacobian[to_index, from_index] -= dq_dh

                jacobian[to_index, to_index] += dq_dh

        return jacobian

    def jacobian(
        self,
        unknown_heads: list[float] | tuple[float, ...],
        alpha: float = 1.0,
        derivative_mode: str = "default",
    ) -> np.ndarray:
        """Alias for dense_jacobian()."""
        return self.dense_jacobian(
            unknown_heads=unknown_heads,
            alpha=alpha,
            derivative_mode=derivative_mode,
        )

    def finite_difference_jacobian(
        self,
        unknown_heads: list[float] | tuple[float, ...],
        alpha: float = 1.0,
        relative_step: float = 1.0e-6,
        absolute_step: float = 1.0e-8,
    ) -> np.ndarray:
        """
        Assemble the dense residual Jacobian using central finite differences.
        """
        x = np.asarray(unknown_heads, dtype=float)
        n_unknowns = len(x)
        jacobian = np.zeros((n_unknowns, n_unknowns), dtype=float)

        if n_unknowns == 0:
            return jacobian

        for column_index in range(n_unknowns):
            step = max(
                absolute_step,
                relative_step * max(abs(x[column_index]), 1.0),
            )

            x_plus = x.copy()
            x_minus = x.copy()

            x_plus[column_index] += step
            x_minus[column_index] -= step

            residual_plus = np.asarray(
                self.nodal_flow_residuals(x_plus.tolist(), alpha),
                dtype=float,
            )
            residual_minus = np.asarray(
                self.nodal_flow_residuals(x_minus.tolist(), alpha),
                dtype=float,
            )

            jacobian[:, column_index] = (
                residual_plus - residual_minus
            ) / (2.0 * step)

        return jacobian

    # ------------------------------------------------------------------
    # Result evaluation
    # ------------------------------------------------------------------

    def evaluate_state(
        self,
        unknown_heads: list[float] | tuple[float, ...],
        alpha: float = 1.0,
    ) -> dict[str, Any]:
        """
        Evaluate the complete hydraulic state of the system.

        This method is intended for result inspection, export, debugging and
        post-processing. It is not the solver residual vector.

        Returns
        -------
        dict[str, Any]
            Dictionary containing node results, link results, residuals and
            global summary values.
        """
        heads = self.heads_from_unknowns(unknown_heads, alpha)
        flows = self.all_link_flow_rates(heads)
        residuals = self.residuals_by_node(unknown_heads, alpha)

        node_results: dict[str, dict[str, Any]] = {}

        for node_id, node in self.nodes.items():
            head = heads[node_id]

            node_results[node_id] = {
                "id": node.id,
                "type": node.type,
                "head": head,
                "elevation": node.elevation(),
                "pressure_head": node.pressure_head(head=head),
                "external_flow": node.external_flow(alpha),
                "is_fixed_head": node.is_fixed_head(),
                "is_unknown_head": node.is_unknown_head(),
                "metadata": dict(node.metadata),
            }

        link_results: dict[str, dict[str, Any]] = {}

        for link_id, link in self.links.items():
            connection = self.get_connection(link.connection_id)
            delta_h = self.link_delta_h(link_id, heads)
            flow_rate = flows[link_id]

            link_results[link_id] = {
                "id": link.id,
                "connection_id": link.connection_id,
                "connection_type": connection.type,
                "from_node_id": link.from_node_id,
                "to_node_id": link.to_node_id,
                "delta_h": delta_h,
                "flow_rate": flow_rate,
                "metadata": dict(link.metadata),
            }

        residual_vector = [
            residuals[node_id]
            for node_id in self.unknown_head_node_ids()
        ]

        max_abs_residual = (
            0.0
            if not residuals
            else max(abs(value) for value in residuals.values())
        )

        return {
            "system_id": self.id,
            "alpha": float(alpha),
            "unknown_node_ids": self.unknown_head_node_ids(),
            "fixed_node_ids": self.fixed_head_node_ids(),
            "unknown_heads": [float(value) for value in unknown_heads],
            "nodes": node_results,
            "links": link_results,
            "residuals": {
                "by_node": residuals,
                "vector": residual_vector,
                "max_abs": max_abs_residual,
                "units": "m3/s",
            },
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Convert the system to a serializable dictionary."""
        return {
            "id": self.id,
            "nodes": [
                node.to_dict()
                for node in self.nodes.values()
            ],
            "connections": [
                connection.to_dict()
                for connection in self.connections.values()
            ],
            "links": [
                link.to_dict()
                for link in self.links.values()
            ],
            "metadata": self.metadata,
        }
