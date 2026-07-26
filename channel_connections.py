"""Power-law connections for the parametric microchip cooling network.

Every channel is represented in HN3Ttk with

    delta_H = -K * sign(Q) * abs(Q)**n

where HN3Ttk expects ``delta_H`` in metres and ``Q`` in m3/s.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from math import pi
from typing import Any, ClassVar

from hn3ttk.connections import Connection, PipeFixedPowerLaw, PipeLocalPowerLaw


MM_TO_M = 1.0e-3
MM3_S_TO_M3_S = 1.0e-9


def _positive_finite(name: str, value: float) -> float:
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric.")

    value = float(value)
    if not isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive.")

    return value


@dataclass(frozen=True)
class RectangularChannelGeometry:
    """Geometry of a closed rectangular channel, expressed in metres."""

    length: float
    width: float
    height: float

    def __post_init__(self) -> None:
        for name in ("length", "width", "height"):
            object.__setattr__(
                self,
                name,
                _positive_finite(name, getattr(self, name)),
            )

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def wetted_perimeter(self) -> float:
        return 2.0 * (self.width + self.height)

    @property
    def hydraulic_diameter(self) -> float:
        """Return Dh = 4A/P = 2wh/(w+h)."""
        return 4.0 * self.area / self.wetted_perimeter

    def velocity(self, flow_rate: float) -> float:
        """Return mean velocity [m/s] for a flow rate in m3/s."""
        return float(flow_rate) / self.area

    def reynolds_number(
        self,
        flow_rate: float,
        *,
        kinematic_viscosity: float,
    ) -> float:
        """Return Re = |v|*Dh/nu using the real rectangular area."""
        kinematic_viscosity = _positive_finite(
            "kinematic_viscosity",
            kinematic_viscosity,
        )
        return (
            abs(self.velocity(flow_rate))
            * self.hydraulic_diameter
            / kinematic_viscosity
        )


class RectangularPowerLawConnection(Connection):
    """Canal rectangular amb la formulació local ``K(Q)*Q**n(Q)``.

    ``PipeLocalPowerLaw`` calcula K i n a partir de Darcy-Weisbach, però la
    seva geometria interna és circular. Aquest adaptador utilitza el diàmetre
    hidràulic i transforma el cabal equivalent per conservar la velocitat real
    del rectangle.
    """

    type: ClassVar[str] = "rectangular_local_power_law"

    def __post_init__(self) -> None:
        self.validate()
        parametres = {
            "length": self.length,
            "diameter": self.hydraulic_diameter,
            "roughness": self.roughness,
            "kinematic_viscosity": self.parameters["kinematic_viscosity"],
            "gravity": self.parameters["gravity"],
            # Els cabals d'aquesta xarxa són molt inferiors al valor per
            # defecte de PipeLocalPowerLaw.
            "minimum_flow_rate": self.parameters.get(
                "minimum_flow_rate",
                1.0e-14,
            ),
        }
        self._model_equivalent = PipeLocalPowerLaw(
            id=f"{self.id}__equivalent",
            parameters=parametres,
        )

    def validate(self) -> None:
        super().validate()
        for nom in (
            "length",
            "width",
            "height",
            "kinematic_viscosity",
            "gravity",
        ):
            if nom not in self.parameters:
                raise ValueError(f"Falta el paràmetre '{nom}'.")
            self.parameters[nom] = _positive_finite(
                nom,
                self.parameters[nom],
            )

        roughness = self.parameters.get("roughness", 0.0)
        if not isinstance(roughness, (int, float)):
            raise TypeError("roughness must be numeric.")
        roughness = float(roughness)
        if not isfinite(roughness) or roughness < 0.0:
            raise ValueError("roughness must be finite and non-negative.")
        self.parameters["roughness"] = roughness

    @property
    def length(self) -> float:
        return float(self.parameters["length"])

    @property
    def width(self) -> float:
        return float(self.parameters["width"])

    @property
    def height(self) -> float:
        return float(self.parameters["height"])

    @property
    def roughness(self) -> float:
        return float(self.parameters["roughness"])

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def hydraulic_diameter(self) -> float:
        return 2.0 * self.width * self.height / (self.width + self.height)

    @property
    def area_circular_equivalent(self) -> float:
        return pi * self.hydraulic_diameter**2 / 4.0

    @property
    def escala_cabal(self) -> float:
        """Q equivalent / Q real per conservar la velocitat."""
        return self.area_circular_equivalent / self.area

    def head_loss(self, q: float) -> float:
        return self._model_equivalent.head_loss(float(q) * self.escala_cabal)

    def flow_rate(self, delta_h: float) -> float:
        return (
            self._model_equivalent.flow_rate(float(delta_h))
            / self.escala_cabal
        )

    def head_loss_derivative(self, q: float) -> float:
        return (
            self._model_equivalent.head_loss_derivative(
                float(q) * self.escala_cabal
            )
            * self.escala_cabal
        )

    def flow_rate_derivative(self, delta_h: float) -> float:
        return (
            self._model_equivalent.flow_rate_derivative(float(delta_h))
            / self.escala_cabal
        )

    def reynolds_number(self, q: float) -> float:
        return self._model_equivalent.reynolds_number(
            float(q) * self.escala_cabal
        )

    def flow_regime(self, q: float) -> str:
        return self._model_equivalent.flow_regime(
            float(q) * self.escala_cabal
        )

    def local_power_law_parameters(self, q: float) -> tuple[float, float]:
        """Retorna K i n referits al cabal real de secció rectangular."""
        k_equivalent, exponent = (
            self._model_equivalent.local_power_law_parameters(
                float(q) * self.escala_cabal
            )
        )
        return k_equivalent * self.escala_cabal**exponent, exponent


def rectangular_channel_from_mm(
    *,
    connection_id: str,
    length_mm: float,
    width_mm: float,
    height_mm: float,
    roughness_mm: float = 0.0,
    kinematic_viscosity: float = 1.0e-6,
    gravity: float = 9.81,
    metadata: dict[str, Any] | None = None,
) -> RectangularPowerLawConnection:
    """Crea un canal rectangular potencial a partir de dades en mm."""
    geometry = RectangularChannelGeometry(
        length=_positive_finite("length_mm", length_mm) * MM_TO_M,
        width=_positive_finite("width_mm", width_mm) * MM_TO_M,
        height=_positive_finite("height_mm", height_mm) * MM_TO_M,
    )
    connection_metadata: dict[str, Any] = {
        "channel_kind": "rectangular",
        "source_dimensions_mm": {
            "length": float(length_mm),
            "width": float(width_mm),
            "height": float(height_mm),
        },
        "hydraulic_diameter_m": geometry.hydraulic_diameter,
        "power_law_origin": "PipeLocalPowerLaw + correcció rectangular",
    }
    if metadata:
        connection_metadata.update(metadata)

    return RectangularPowerLawConnection(
        id=connection_id,
        parameters={
            "length": geometry.length,
            "width": geometry.width,
            "height": geometry.height,
            "roughness": float(roughness_mm) * MM_TO_M,
            "kinematic_viscosity": float(kinematic_viscosity),
            "gravity": float(gravity),
            "minimum_flow_rate": 1.0e-14,
        },
        metadata=connection_metadata,
    )


def rectangular_laminar_channel_from_mm(
    *,
    connection_id: str,
    length_mm: float,
    width_mm: float,
    height_mm: float,
    kinematic_viscosity: float = 1.0e-6,
    gravity: float = 9.81,
    metadata: dict[str, Any] | None = None,
) -> PipeFixedPowerLaw:
    """Create the KQ^n connection for a laminar rectangular channel.

    Applying Darcy-Weisbach with ``f=64/Re``, the real rectangular area and
    the hydraulic diameter gives:

        delta_H = -K*Q
        K = 32*nu*L / (g*A*Dh**2)
        n = 1

    This is a hydraulic-diameter approximation.  A rectangular-duct
    aspect-ratio correction can replace it later if required by the reference
    model.
    """
    geometry = RectangularChannelGeometry(
        length=_positive_finite("length_mm", length_mm) * MM_TO_M,
        width=_positive_finite("width_mm", width_mm) * MM_TO_M,
        height=_positive_finite("height_mm", height_mm) * MM_TO_M,
    )
    kinematic_viscosity = _positive_finite(
        "kinematic_viscosity",
        kinematic_viscosity,
    )
    gravity = _positive_finite("gravity", gravity)

    coefficient_k = (
        32.0
        * kinematic_viscosity
        * geometry.length
        / (
            gravity
            * geometry.area
            * geometry.hydraulic_diameter**2
        )
    )

    connection_metadata: dict[str, Any] = {
        "channel_kind": "rectangular",
        "source_dimensions_mm": {
            "length": float(length_mm),
            "width": float(width_mm),
            "height": float(height_mm),
        },
        "geometry_si": {
            "length_m": geometry.length,
            "width_m": geometry.width,
            "height_m": geometry.height,
            "area_m2": geometry.area,
            "hydraulic_diameter_m": geometry.hydraulic_diameter,
        },
        "power_law_origin": "Darcy-Weisbach, f=64/Re",
        "kinematic_viscosity_m2_s": kinematic_viscosity,
        "gravity_m_s2": gravity,
    }
    if metadata:
        connection_metadata.update(metadata)

    return PipeFixedPowerLaw(
        id=connection_id,
        parameters={
            "k": coefficient_k,
            "n": 1.0,
        },
        metadata=connection_metadata,
    )


def power_law_channel_from_pa_mm3s(
    *,
    connection_id: str,
    coefficient_k: float,
    exponent_n: float,
    density: float = 998.2,
    gravity: float = 9.81,
    metadata: dict[str, Any] | None = None,
) -> PipeFixedPowerLaw:
    """Convert ``delta_P[Pa] = K*Q[mm3/s]**n`` into an HN3Ttk connection.

    With ``Q_source = Q_SI / 1e-9`` and ``delta_H = delta_P/(rho*g)``:

        K_HN3Ttk = K_source / (rho*g*(1e-9)**n)
    """
    coefficient_k = _positive_finite("coefficient_k", coefficient_k)
    exponent_n = _positive_finite("exponent_n", exponent_n)
    density = _positive_finite("density", density)
    gravity = _positive_finite("gravity", gravity)

    coefficient_head_si = (
        coefficient_k
        / (density * gravity * MM3_S_TO_M3_S**exponent_n)
    )

    connection_metadata: dict[str, Any] = {
        "channel_kind": "empirical_power_law",
        "source_law": "delta_P[Pa] = K * Q[mm3/s]**n",
        "source_coefficient_k": coefficient_k,
        "source_exponent_n": exponent_n,
        "density_kg_m3": density,
        "gravity_m_s2": gravity,
    }
    if metadata:
        connection_metadata.update(metadata)

    return PipeFixedPowerLaw(
        id=connection_id,
        parameters={
            "k": coefficient_head_si,
            "n": exponent_n,
        },
        metadata=connection_metadata,
    )


# Semantic alias used by the future network constructor.
cellular_channel_from_pa_mm3s = power_law_channel_from_pa_mm3s
