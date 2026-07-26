"""Construcció i resolució paramètrica de la xarxa de refrigeració.

Aquest és el mòdul principal de càlcul. La funció pública
``avaluar_xarxa(...)`` rep les dimensions de la xarxa i el salt piezomètric,
construeix el model amb HN3Ttk i en calcula els cabals i les alçades.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Literal

from hn3ttk.nodes import FixedHeadNode, JunctionNode
from hn3ttk.solvers import (
    SolverResult,
    solve_alpha_continuation_damped_newton,
)
from hn3ttk.system import HydraulicSystem

from channel_connections import (
    RectangularChannelGeometry,
    cellular_channel_from_pa_mm3s,
    rectangular_channel_from_mm,
)
from network_image_data import (
    CELLULAR_COEFFICIENT_K,
    CELLULAR_EXPONENT_N,
    HORIZONTAL_WIDTHS_MM,
)


FamiliaCanal = Literal[
    "col_lector_alimentacio",
    "col_lector_desguas",
    "lateral_alimentacio",
    "lateral_desguas",
    "canal_cel_lular",
]


@dataclass(frozen=True)
class DefinicioNode:
    """Informació topològica d'un node, independent del solver."""

    identificador: int
    x: float
    y: float
    zona: str


@dataclass(frozen=True)
class DefinicioCanal:
    """Un canal entre dos nodes i les dades que es llegeixen al dibuix."""

    identificador: int
    node_origen: int
    node_desti: int
    familia: FamiliaCanal
    fila: int | None = None
    columna: int | None = None
    longitud_mm: float | None = None
    amplada_mm: float | None = None
    coeficient_k: float | None = None
    exponent_n: float | None = None


@dataclass(frozen=True)
class TopologiaXarxa:
    """Resultat purament geomètric del constructor paramètric."""

    files: int
    columnes: int
    nodes: tuple[DefinicioNode, ...]
    canals: tuple[DefinicioCanal, ...]

    @property
    def nombre_nodes(self) -> int:
        return len(self.nodes)

    @property
    def nombre_canals(self) -> int:
        return len(self.canals)

    @property
    def node_entrada(self) -> int:
        return 1

    @property
    def node_sortida(self) -> int:
        return self.nombre_nodes


@dataclass
class AvaluacioXarxa:
    """Model, solució i diagnòstics retornats per ``avaluar_xarxa``."""

    topologia: TopologiaXarxa
    sistema: HydraulicSystem
    resultat: SolverResult
    altura_canal_mm: float
    salt_piezometric_m: float
    coeficient_cel_lular_k: float
    exponent_cel_lular_n: float
    avisos: list[str]

    @property
    def estat(self) -> dict:
        if self.resultat.state is None:
            raise RuntimeError("El solver no ha retornat l'estat hidràulic.")
        return self.resultat.state

    @property
    def cabal_entrada_m3_s(self) -> float:
        return float(self.estat["links"]["tub_1"]["flow_rate"])

    @property
    def cabal_entrada_mm3_s(self) -> float:
        return self.cabal_entrada_m3_s * 1.0e9


def _enter_positiu(nom: str, valor: int) -> int:
    if not isinstance(valor, int):
        raise TypeError(f"{nom} ha de ser un nombre enter.")
    if valor <= 0:
        raise ValueError(f"{nom} ha de ser positiu.")
    return valor


def _real_positiu(nom: str, valor: float) -> float:
    if not isinstance(valor, (int, float)):
        raise TypeError(f"{nom} ha de ser numèric.")
    valor = float(valor)
    if not isfinite(valor) or valor <= 0.0:
        raise ValueError(f"{nom} ha de ser finit i positiu.")
    return valor


def _real_no_negatiu(nom: str, valor: float) -> float:
    if not isinstance(valor, (int, float)):
        raise TypeError(f"{nom} ha de ser numèric.")
    valor = float(valor)
    if not isfinite(valor) or valor < 0.0:
        raise ValueError(f"{nom} ha de ser finit i no negatiu.")
    return valor


def crear_perfil_amplades(columnes: int) -> tuple[float, ...]:
    """Amplades dels laterals, ordenades per identificador local.

    Per a 14 columnes es retornen exactament els valors de la figura. Per a
    altres mides es conserva el primer tram de 1,5 mm i s'interpolen els trams
    restants entre 1,341 i 0,141 mm.
    """
    columnes = _enter_positiu("columnes", columnes)

    if columnes == len(HORIZONTAL_WIDTHS_MM):
        return HORIZONTAL_WIDTHS_MM
    if columnes == 1:
        return (1.5,)
    if columnes == 2:
        return (1.5, 0.141)

    amplades = [1.5]
    pas = (1.341 - 0.141) / (columnes - 2)
    amplades.extend(1.341 - index * pas for index in range(columnes - 1))
    return tuple(amplades)


def generar_topologia(files: int, columnes: int) -> TopologiaXarxa:
    """Genera nodes i canals sense efectuar cap càlcul hidràulic.

    Les files es numeren de baix a dalt i les columnes de dreta a esquerra,
    igual que el recorregut de l'aigua pel col·lector blau de la figura.
    """
    files = _enter_positiu("files", files)
    columnes = _enter_positiu("columnes", columnes)

    nodes: dict[int, DefinicioNode] = {
        1: DefinicioNode(1, 0.0, 0.0, "entrada")
    }
    canals: list[DefinicioCanal] = []
    amplades = crear_perfil_amplades(columnes)
    nodes_per_fila = 2 * columnes + 2

    def base(fila: int) -> int:
        return (fila - 1) * nodes_per_fila

    def node_collector_blau(fila: int) -> int:
        return base(fila) + 2

    def node_blau(fila: int, columna: int) -> int:
        return base(fila) + 2 * columna + 1

    def node_roig(fila: int, columna: int) -> int:
        return base(fila) + 2 * columna + 2

    def node_collector_roig(fila: int) -> int:
        return base(fila) + 2 * columnes + 3

    # Nodes repetitius de cada fila.
    for fila in range(1, files + 1):
        y_blau = float(2 * fila - 1)
        y_roig = float(2 * fila)

        node_b = node_collector_blau(fila)
        nodes[node_b] = DefinicioNode(node_b, 0.0, y_blau, "alimentacio")

        for columna in range(1, columnes + 1):
            x = float(-columna)
            node_a = node_blau(fila, columna)
            node_d = node_roig(fila, columna)
            nodes[node_a] = DefinicioNode(node_a, x, y_blau, "alimentacio")
            nodes[node_d] = DefinicioNode(node_d, x, y_roig, "desguas")

        node_r = node_collector_roig(fila)
        nodes[node_r] = DefinicioNode(
            node_r,
            float(-(columnes + 1)),
            y_roig,
            "desguas",
        )

    node_sortida = 2 + 2 * files * (columnes + 1)
    nodes[node_sortida] = DefinicioNode(
        node_sortida,
        float(-(columnes + 1)),
        float(2 * files + 1),
        "sortida",
    )

    # Col·lector blau: tubs 1..m, des de l'entrada cap amunt.
    for fila in range(1, files + 1):
        origen = 1 if fila == 1 else node_collector_blau(fila - 1)
        desti = node_collector_blau(fila)
        canals.append(
            DefinicioCanal(
                identificador=fila,
                node_origen=origen,
                node_desti=desti,
                familia="col_lector_alimentacio",
                fila=fila,
                longitud_mm=1.0 if fila == 1 else 2.0,
                amplada_mm=1.4,
            )
        )

    # Col·lector roig: la numeració de la figura va de dalt a baix.
    for fila in range(1, files + 1):
        identificador = 2 * files - fila + 1
        origen = node_collector_roig(fila)
        desti = (
            node_sortida
            if fila == files
            else node_collector_roig(fila + 1)
        )
        canals.append(
            DefinicioCanal(
                identificador=identificador,
                node_origen=origen,
                node_desti=desti,
                familia="col_lector_desguas",
                fila=fila,
                longitud_mm=1.0 if fila == files else 2.0,
                amplada_mm=1.4,
            )
        )

    inici_blau = 2 * files
    inici_roig = 2 * files + files * columnes
    inici_cel_lules = 2 * files + 2 * files * columnes

    for fila in range(1, files + 1):
        for columna in range(1, columnes + 1):
            # Lateral blau: la numeració creix de dreta a esquerra.
            id_blau = inici_blau + (fila - 1) * columnes + columna
            origen_blau = (
                node_collector_blau(fila)
                if columna == 1
                else node_blau(fila, columna - 1)
            )
            desti_blau = node_blau(fila, columna)
            canals.append(
                DefinicioCanal(
                    identificador=id_blau,
                    node_origen=origen_blau,
                    node_desti=desti_blau,
                    familia="lateral_alimentacio",
                    fila=fila,
                    columna=columna,
                    longitud_mm=1.2,
                    amplada_mm=amplades[columna - 1],
                )
            )

            # Lateral roig: el flux va cap a l'esquerra però els identificadors
            # de la figura decreixen en aquest sentit.
            id_roig = (
                inici_roig
                + (fila - 1) * columnes
                + (columnes - columna + 1)
            )
            origen_roig = node_roig(fila, columna)
            desti_roig = (
                node_collector_roig(fila)
                if columna == columnes
                else node_roig(fila, columna + 1)
            )
            canals.append(
                DefinicioCanal(
                    identificador=id_roig,
                    node_origen=origen_roig,
                    node_desti=desti_roig,
                    familia="lateral_desguas",
                    fila=fila,
                    columna=columna,
                    longitud_mm=1.2,
                    amplada_mm=amplades[columnes - columna],
                )
            )

            # Canal verd entre els dos laterals.
            id_cel_lula = (
                inici_cel_lules + (fila - 1) * columnes + columna
            )
            canals.append(
                DefinicioCanal(
                    identificador=id_cel_lula,
                    node_origen=node_blau(fila, columna),
                    node_desti=node_roig(fila, columna),
                    familia="canal_cel_lular",
                    fila=fila,
                    columna=columna,
                    coeficient_k=CELLULAR_COEFFICIENT_K,
                    exponent_n=CELLULAR_EXPONENT_N,
                )
            )

    topologia = TopologiaXarxa(
        files=files,
        columnes=columnes,
        nodes=tuple(nodes[node_id] for node_id in sorted(nodes)),
        canals=tuple(sorted(canals, key=lambda canal: canal.identificador)),
    )
    _validar_topologia(topologia)
    return topologia


def _validar_topologia(topologia: TopologiaXarxa) -> None:
    """Comprovacions estructurals abans de crear objectes HN3Ttk."""
    nodes_esperats = 2 + 2 * topologia.files * (topologia.columnes + 1)
    canals_esperats = topologia.files * (3 * topologia.columnes + 2)

    if topologia.nombre_nodes != nodes_esperats:
        raise RuntimeError("El constructor no ha generat el nombre correcte de nodes.")
    if topologia.nombre_canals != canals_esperats:
        raise RuntimeError("El constructor no ha generat el nombre correcte de canals.")

    ids_nodes = {node.identificador for node in topologia.nodes}
    ids_canals = [canal.identificador for canal in topologia.canals]
    if ids_canals != list(range(1, canals_esperats + 1)):
        raise RuntimeError("Els identificadors dels canals no són consecutius.")

    grau = {node_id: 0 for node_id in ids_nodes}
    for canal in topologia.canals:
        if canal.node_origen not in ids_nodes or canal.node_desti not in ids_nodes:
            raise RuntimeError("Hi ha un canal connectat a un node inexistent.")
        grau[canal.node_origen] += 1
        grau[canal.node_desti] += 1

    if any(valor == 0 for valor in grau.values()):
        raise RuntimeError("La xarxa conté nodes aïllats.")


def construir_sistema(
    topologia: TopologiaXarxa,
    *,
    salt_piezometric_m: float,
    altura_canal_mm: float = 0.5,
    viscositat_cinematica_m2_s: float = 1.0e-6,
    densitat_kg_m3: float = 998.2,
    coeficient_cel_lular_k: float = CELLULAR_COEFFICIENT_K,
    exponent_cel_lular_n: float = CELLULAR_EXPONENT_N,
) -> HydraulicSystem:
    """Converteix la topologia en nodes, connexions i links d'HN3Ttk."""
    salt_piezometric_m = _real_no_negatiu(
        "salt_piezometric_m",
        salt_piezometric_m,
    )
    altura_canal_mm = _real_positiu("altura_canal_mm", altura_canal_mm)
    viscositat_cinematica_m2_s = _real_positiu(
        "viscositat_cinematica_m2_s",
        viscositat_cinematica_m2_s,
    )
    densitat_kg_m3 = _real_positiu("densitat_kg_m3", densitat_kg_m3)
    coeficient_cel_lular_k = _real_positiu(
        "coeficient_cel_lular_k",
        coeficient_cel_lular_k,
    )
    exponent_cel_lular_n = _real_positiu(
        "exponent_cel_lular_n",
        exponent_cel_lular_n,
    )

    sistema = HydraulicSystem(
        id=f"xarxa_microxip_{topologia.files}x{topologia.columnes}",
        metadata={
            "files": topologia.files,
            "columnes": topologia.columnes,
            "salt_piezometric_m": salt_piezometric_m,
            "altura_canal_mm": altura_canal_mm,
            "coeficient_cel_lular_k": coeficient_cel_lular_k,
            "exponent_cel_lular_n": exponent_cel_lular_n,
        },
    )

    for definicio in topologia.nodes:
        node_id = str(definicio.identificador)
        metadades = {
            "x": definicio.x,
            "y": definicio.y,
            "zona": definicio.zona,
        }

        if definicio.identificador == topologia.node_entrada:
            node = FixedHeadNode(
                id=node_id,
                parameters={"elevation": 0.0, "head": salt_piezometric_m},
                metadata=metadades,
            )
        elif definicio.identificador == topologia.node_sortida:
            node = FixedHeadNode(
                id=node_id,
                parameters={"elevation": 0.0, "head": 0.0},
                metadata=metadades,
            )
        else:
            fraccio_inicial = (
                0.75 if definicio.zona == "alimentacio" else 0.25
            )
            node = JunctionNode(
                id=node_id,
                parameters={
                    "elevation": 0.0,
                    "initial_head": fraccio_inicial * salt_piezometric_m,
                    "external_flow": 0.0,
                },
                metadata=metadades,
            )

        sistema.add_node(node)

    for canal in topologia.canals:
        connection_id = f"conn_{canal.identificador}"
        metadades = {
            "tub": canal.identificador,
            "familia": canal.familia,
            "fila": canal.fila,
            "columna": canal.columna,
        }

        if canal.familia == "canal_cel_lular":
            connexio = cellular_channel_from_pa_mm3s(
                connection_id=connection_id,
                coefficient_k=coeficient_cel_lular_k,
                exponent_n=exponent_cel_lular_n,
                density=densitat_kg_m3,
                metadata=metadades,
            )
        else:
            connexio = rectangular_channel_from_mm(
                connection_id=connection_id,
                length_mm=float(canal.longitud_mm),
                width_mm=float(canal.amplada_mm),
                height_mm=altura_canal_mm,
                kinematic_viscosity=viscositat_cinematica_m2_s,
                metadata=metadades,
            )

        sistema.add_connection(connexio)
        sistema.connect(
            connection_id=connection_id,
            from_node_id=str(canal.node_origen),
            to_node_id=str(canal.node_desti),
            link_id=f"tub_{canal.identificador}",
            metadata=metadades,
        )

    sistema.validate()
    return sistema


def _revisar_regim(
    topologia: TopologiaXarxa,
    resultat: SolverResult,
    *,
    altura_canal_mm: float,
    viscositat_cinematica_m2_s: float,
) -> list[str]:
    """Resumeix els règims calculats als canals rectangulars."""
    if resultat.state is None:
        return ["No s'ha pogut revisar el nombre de Reynolds."]

    reynolds_maxim = 0.0
    tub_maxim = 0
    regims = {"laminar": 0, "transition": 0, "turbulent": 0, "stagnant": 0}

    for canal in topologia.canals:
        if canal.familia == "canal_cel_lular":
            continue

        cabal = resultat.state["links"][f"tub_{canal.identificador}"][
            "flow_rate"
        ]
        geometria = RectangularChannelGeometry(
            length=float(canal.longitud_mm) * 1.0e-3,
            width=float(canal.amplada_mm) * 1.0e-3,
            height=altura_canal_mm * 1.0e-3,
        )
        reynolds = geometria.reynolds_number(
            cabal,
            kinematic_viscosity=viscositat_cinematica_m2_s,
        )
        if reynolds == 0.0:
            regim = "stagnant"
        elif reynolds <= 2000.0:
            regim = "laminar"
        elif reynolds >= 4000.0:
            regim = "turbulent"
        else:
            regim = "transition"
        regims[regim] += 1
        if reynolds > reynolds_maxim:
            reynolds_maxim = reynolds
            tub_maxim = canal.identificador

    return [
        (
            f"Re màxim = {reynolds_maxim:.1f} al tub {tub_maxim}; "
            f"règims: {regims['laminar']} laminars, "
            f"{regims['transition']} de transició i "
            f"{regims['turbulent']} turbulents."
        )
    ]


def mostrar_resum(avaluacio: AvaluacioXarxa) -> None:
    """Imprimeix només les magnituds necessàries per interpretar el càlcul."""
    resultat = avaluacio.resultat
    print("\nRESULTAT DE LA XARXA")
    print(f"Dimensions: {avaluacio.topologia.files} x {avaluacio.topologia.columnes}")
    print(f"Nodes: {avaluacio.topologia.nombre_nodes}")
    print(f"Canals: {avaluacio.topologia.nombre_canals}")
    print(f"Convergència: {'sí' if resultat.success else 'no'}")
    print(f"Iteracions/avaluacions: {resultat.iterations}")
    print(f"Residu màxim: {resultat.max_abs_residual:.3e} m³/s")
    print(f"Cabal total: {avaluacio.cabal_entrada_mm3_s:.6g} mm³/s")
    for avis in avaluacio.avisos:
        print(f"Avís: {avis}")


def avaluar_xarxa(
    files: int,
    columnes: int,
    diferencia_altura_piezometrica_m: float,
    *,
    altura_canal_mm: float = 0.5,
    viscositat_cinematica_m2_s: float = 1.0e-6,
    densitat_kg_m3: float = 998.2,
    coeficient_cel_lular_k: float = CELLULAR_COEFFICIENT_K,
    exponent_cel_lular_n: float = CELLULAR_EXPONENT_N,
    generar_grafic: bool = False,
    fitxer_grafic: str | Path = "xarxa_resolta.png",
    imprimir_resum: bool = True,
) -> AvaluacioXarxa:
    """Construeix i resol una xarxa; aquesta és la funció per a l'usuari.

    Els tres arguments posicionals són els únics imprescindibles, fet que
    permet estudiar casos amb un bucle ``for``. La resta tenen valors per
    defecte i només cal indicar-los quan es vulgui modificar el model físic.
    """
    topologia = generar_topologia(files, columnes)
    sistema = construir_sistema(
        topologia,
        salt_piezometric_m=diferencia_altura_piezometrica_m,
        altura_canal_mm=altura_canal_mm,
        viscositat_cinematica_m2_s=viscositat_cinematica_m2_s,
        densitat_kg_m3=densitat_kg_m3,
        coeficient_cel_lular_k=coeficient_cel_lular_k,
        exponent_cel_lular_n=exponent_cel_lular_n,
    )

    if float(diferencia_altura_piezometrica_m) == 0.0:
        caps_nuls = [0.0] * len(sistema.unknown_head_node_ids())
        estat_nul = sistema.evaluate_state(caps_nuls)
        residuals_nuls = estat_nul["residuals"]["vector"]
        resultat = SolverResult(
            success=True,
            message="Estat en repòs: ΔH = 0 i Q = 0.",
            iterations=0,
            unknown_heads=caps_nuls,
            residuals=residuals_nuls,
            max_abs_residual=float(estat_nul["residuals"]["max_abs"]),
            state=estat_nul,
            metadata={"solver": "solució_analítica_nul·la"},
        )
    else:
        resultat = solve_alpha_continuation_damped_newton(
            sistema,
            alpha_start=0.0,
            alpha_end=1.0,
            alpha_steps=10,
            tolerance=1.0e-12,
            step_tolerance=1.0e-12,
            max_iterations_per_step=100,
        )
    avisos = _revisar_regim(
        topologia,
        resultat,
        altura_canal_mm=altura_canal_mm,
        viscositat_cinematica_m2_s=viscositat_cinematica_m2_s,
    )
    avaluacio = AvaluacioXarxa(
        topologia=topologia,
        sistema=sistema,
        resultat=resultat,
        altura_canal_mm=float(altura_canal_mm),
        salt_piezometric_m=float(diferencia_altura_piezometrica_m),
        coeficient_cel_lular_k=float(coeficient_cel_lular_k),
        exponent_cel_lular_n=float(exponent_cel_lular_n),
        avisos=avisos,
    )

    if imprimir_resum:
        mostrar_resum(avaluacio)

    if generar_grafic:
        from plot_xarxa import dibuixar_xarxa

        dibuixar_xarxa(avaluacio, fitxer=fitxer_grafic)

    return avaluacio
