from hn3ttk.connections.base import Connection
from hn3ttk.connections.custom_factor_polynomial import (
    CustomFactorPolynomialConnection,
)
from hn3ttk.connections.factory import (
    available_connection_types,
    connection_from_dict,
    connection_to_dict,
    register_connection_type,
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

__all__ = [
    "Connection",
    "CustomFactorPolynomialConnection",
    "LinearInterpolationConnection",
    "PipeDarcy",
    "PipeFixedPowerLaw",
    "PipeLocalPowerLaw",
    "PolynomialRegressionConnection",
    "SplineInterpolationConnection",
    "SplineSecantExtrapolationConnection",
    "SplineTangentExtrapolationConnection",
    "available_connection_types",
    "connection_from_dict",
    "connection_to_dict",
    "register_connection_type",
]
