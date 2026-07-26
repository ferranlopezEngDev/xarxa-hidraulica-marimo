from __future__ import annotations

from typing import Any

from hn3ttk.connections.base import Connection
from hn3ttk.connections.custom_factor_polynomial import (
    CustomFactorPolynomialConnection,
)
from hn3ttk.connections.linear_interpolation import LinearInterpolationConnection
from hn3ttk.connections.pipe_darcy import PipeDarcy
from hn3ttk.connections.pipe_fixed_power_law import PipeFixedPowerLaw
from hn3ttk.connections.pipe_local_power_law import PipeLocalPowerLaw
from hn3ttk.connections.polynomial_regression import PolynomialRegressionConnection
from hn3ttk.connections.spline_interpolation import SplineInterpolationConnection
from hn3ttk.connections.spline_secant_extrapolation import (
    SplineSecantExtrapolationConnection,
)
from hn3ttk.connections.spline_tangent_extrapolation import (
    SplineTangentExtrapolationConnection,
)


CONNECTION_REGISTRY: dict[str, type[Connection]] = {
    PipeDarcy.type: PipeDarcy,
    PipeLocalPowerLaw.type: PipeLocalPowerLaw,
    PipeFixedPowerLaw.type: PipeFixedPowerLaw,
    LinearInterpolationConnection.type: LinearInterpolationConnection,
    PolynomialRegressionConnection.type: PolynomialRegressionConnection,
    SplineInterpolationConnection.type: SplineInterpolationConnection,
    SplineSecantExtrapolationConnection.type: SplineSecantExtrapolationConnection,
    SplineTangentExtrapolationConnection.type: SplineTangentExtrapolationConnection,
    CustomFactorPolynomialConnection.type: CustomFactorPolynomialConnection,
}


def connection_from_dict(data: dict[str, Any]) -> Connection:
    """
    Build a Connection object from a dictionary.

    Expected format:

        {
            "id": "connection_1",
            "type": "pipe_fixed_power_law",
            "parameters": {...},
            "metadata": {...}
        }

    The "id" and "metadata" fields are optional.
    The "type" and "parameters" fields are required.
    """
    if not isinstance(data, dict):
        raise TypeError("Connection data must be a dictionary.")

    if "type" not in data:
        raise ValueError("Connection data must contain a 'type' field.")

    if "parameters" not in data:
        raise ValueError("Connection data must contain a 'parameters' field.")

    connection_type = data["type"]

    if not isinstance(connection_type, str):
        raise TypeError("Connection 'type' must be a string.")

    if connection_type not in CONNECTION_REGISTRY:
        available_types = ", ".join(sorted(CONNECTION_REGISTRY.keys()))
        raise ValueError(
            f"Unknown connection type '{connection_type}'. "
            f"Available types: {available_types}"
        )

    parameters = data["parameters"]

    if not isinstance(parameters, dict):
        raise TypeError("Connection 'parameters' must be a dictionary.")

    metadata = data.get("metadata", {})

    if not isinstance(metadata, dict):
        raise TypeError("Connection 'metadata' must be a dictionary.")

    connection_class = CONNECTION_REGISTRY[connection_type]

    constructor_arguments: dict[str, Any] = {
        "parameters": dict(parameters),
        "metadata": dict(metadata),
    }

    if "id" in data:
        if not isinstance(data["id"], str):
            raise TypeError("Connection 'id' must be a string.")

        constructor_arguments["id"] = data["id"]

    return connection_class(**constructor_arguments)


def connection_to_dict(connection: Connection) -> dict[str, Any]:
    """
    Convert a Connection object to a serializable dictionary.
    """
    if not isinstance(connection, Connection):
        raise TypeError("Expected a Connection object.")

    return connection.to_dict()


def available_connection_types() -> list[str]:
    """
    Return the list of registered connection types.
    """
    return sorted(CONNECTION_REGISTRY.keys())


def register_connection_type(connection_class: type[Connection]) -> None:
    """
    Register a new Connection class in the factory.

    The class must inherit from Connection and define a string class variable
    named 'type'.
    """
    if not issubclass(connection_class, Connection):
        raise TypeError("Registered class must inherit from Connection.")

    connection_type = getattr(connection_class, "type", None)

    if not isinstance(connection_type, str):
        raise TypeError("Connection class must define a string 'type' attribute.")

    if not connection_type:
        raise ValueError("Connection class 'type' cannot be empty.")

    CONNECTION_REGISTRY[connection_type] = connection_class
