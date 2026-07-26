from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class Link:
    """
    Topological link between one connection and two nodes.

    A Link defines how a local hydraulic connection is placed inside a network.

    Constructor arguments
    ---------------------
    connection_id:
        Id of the connection model placed in the network.
    from_node_id:
        Id of the upstream reference node for the positive flow direction.
    to_node_id:
        Id of the downstream reference node for the positive flow direction.
    id:
        Optional link identifier. If omitted, a unique id is generated.
    metadata:
        Free-form user metadata.

    Sign convention:
        q > 0 means flow from from_node_id to to_node_id

    Head convention:
        delta_h = H_to - H_from
    """

    connection_id: str
    from_node_id: str
    to_node_id: str
    id: str = field(default_factory=lambda: f"link_{uuid4().hex}")
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """
        Validate link fields and basic topology consistency.

        This method checks string ids, ensures the link is not self-connected
        and validates the metadata container type.
        """
        if not isinstance(self.id, str):
            raise TypeError("Link id must be a string.")

        if not self.id:
            raise ValueError("Link id cannot be empty.")

        if not isinstance(self.connection_id, str):
            raise TypeError("Link connection_id must be a string.")

        if not self.connection_id:
            raise ValueError("Link connection_id cannot be empty.")

        if not isinstance(self.from_node_id, str):
            raise TypeError("Link from_node_id must be a string.")

        if not self.from_node_id:
            raise ValueError("Link from_node_id cannot be empty.")

        if not isinstance(self.to_node_id, str):
            raise TypeError("Link to_node_id must be a string.")

        if not self.to_node_id:
            raise ValueError("Link to_node_id cannot be empty.")

        if self.from_node_id == self.to_node_id:
            raise ValueError("Link cannot connect a node to itself.")

        if not isinstance(self.metadata, dict):
            raise TypeError("Link metadata must be a dictionary.")

    def reversed(self) -> "Link":
        """
        Return a new link with reversed orientation.

        The new link keeps the same connection id and metadata copy, but swaps
        ``from_node_id`` and ``to_node_id``.
        """
        return Link(
            id=f"{self.id}_reversed",
            connection_id=self.connection_id,
            from_node_id=self.to_node_id,
            to_node_id=self.from_node_id,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the link to a serializable dictionary."""
        return {
            "id": self.id,
            "connection_id": self.connection_id,
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Link":
        """
        Build a link object from a serialized dictionary.

        Parameters
        ----------
        data:
            Dictionary containing ``connection_id``, ``from_node_id`` and
            ``to_node_id``, plus optional ``id`` and ``metadata``.
        """
        if not isinstance(data, dict):
            raise TypeError("Link data must be a dictionary.")

        return cls(
            id=data.get("id", f"link_{uuid4().hex}"),
            connection_id=data["connection_id"],
            from_node_id=data["from_node_id"],
            to_node_id=data["to_node_id"],
            metadata=data.get("metadata", {}),
        )
