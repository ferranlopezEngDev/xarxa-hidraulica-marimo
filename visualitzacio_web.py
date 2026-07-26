"""Gràfics de resultats; separats de la llibreta per mantenir l'exemple net."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from xarxa_microxip import AvaluacioXarxa


def crear_figura_resultats(avaluacio: AvaluacioXarxa):
    """Crea la distribució piezomètrica i el mapa de cabals cel·lulars."""
    topologia = avaluacio.topologia
    estat = avaluacio.estat
    posicions = {
        node.identificador: (node.x, node.y)
        for node in topologia.nodes
    }
    colors = {
        "col_lector_alimentacio": "#0057d9",
        "lateral_alimentacio": "#0057d9",
        "col_lector_desguas": "#e31a1c",
        "lateral_desguas": "#e31a1c",
        "canal_cel_lular": "#21b521",
    }

    figura, (eix_xarxa, eix_cabals) = plt.subplots(
        1,
        2,
        figsize=(15, 7),
        constrained_layout=True,
    )

    for canal in topologia.canals:
        x1, y1 = posicions[canal.node_origen]
        x2, y2 = posicions[canal.node_desti]
        eix_xarxa.plot(
            (x1, x2),
            (y1, y2),
            color=colors[canal.familia],
            linewidth=1.0,
            alpha=0.7,
        )

    punts = eix_xarxa.scatter(
        [node.x for node in topologia.nodes],
        [node.y for node in topologia.nodes],
        c=[
            estat["nodes"][str(node.identificador)]["head"]
            for node in topologia.nodes
        ],
        cmap="plasma",
        s=17,
        zorder=3,
    )
    figura.colorbar(
        punts,
        ax=eix_xarxa,
        label="Altura piezomètrica H [m]",
        shrink=0.75,
    )
    eix_xarxa.set_title("Distribució piezomètrica")
    eix_xarxa.set_aspect("equal")
    eix_xarxa.set_xlabel("Coordenada paramètrica x")
    eix_xarxa.set_ylabel("Coordenada paramètrica y")

    inici_cel_lules = (
        2 * topologia.files
        + 2 * topologia.files * topologia.columnes
    )
    matriu_cabals = np.zeros((topologia.files, topologia.columnes))
    for fila in range(topologia.files):
        for columna in range(topologia.columnes):
            tub = (
                inici_cel_lules
                + fila * topologia.columnes
                + columna
                + 1
            )
            matriu_cabals[fila, columna] = (
                estat["links"][f"tub_{tub}"]["flow_rate"] * 1.0e9
            )

    mapa = eix_cabals.imshow(
        matriu_cabals,
        origin="lower",
        aspect="auto",
        cmap="viridis",
        extent=(0.5, topologia.columnes + 0.5, 0.5, topologia.files + 0.5),
    )
    figura.colorbar(
        mapa,
        ax=eix_cabals,
        label="Cabal cel·lular [mm³/s]",
        shrink=0.75,
    )
    eix_cabals.set_title("Distribució de cabal pels canals verds")
    eix_cabals.set_xlabel("Columna")
    eix_cabals.set_ylabel("Fila")
    eix_cabals.set_xticks(range(1, topologia.columnes + 1))
    eix_cabals.set_yticks(range(1, topologia.files + 1))
    return figura


def crear_figures_entorn(estudi):
    """Crea la corba Q(ΔH) i la superfície Q(files, columnes)."""
    figura_salt, eix_salt = plt.subplots(figsize=(8, 4.8))
    eix_salt.plot(
        estudi.salts_m,
        estudi.cabals_salt_mm3_s,
        "o-",
        color="#0057d9",
        linewidth=2,
        label=f"Xarxa {estudi.files_centre} × {estudi.columnes_centre}",
    )
    eix_salt.scatter(
        [estudi.salt_centre_m],
        [estudi.cabal_centre_mm3_s],
        s=90,
        color="#e31a1c",
        zorder=5,
        label="Punt de funcionament",
    )
    eix_salt.set_xlabel("Diferència d'altura piezomètrica ΔH [m]")
    eix_salt.set_ylabel("Cabal total Q [mm³/s]")
    eix_salt.set_title("Resposta al voltant del punt de funcionament")
    eix_salt.grid(alpha=0.25)
    eix_salt.legend()
    figura_salt.tight_layout()

    columnes_malla, files_malla = np.meshgrid(estudi.columnes, estudi.files)
    cabals_malla = np.asarray(estudi.cabals_dimensions_mm3_s)
    figura_superficie = plt.figure(figsize=(9, 6.5))
    eix_superficie = figura_superficie.add_subplot(
        111,
        projection="3d",
        computed_zorder=False,
    )
    superficie = eix_superficie.plot_surface(
        columnes_malla,
        files_malla,
        cabals_malla,
        cmap="viridis",
        edgecolor="black",
        linewidth=0.35,
        alpha=0.82,
        zorder=1,
    )
    marge_marcador = max(
        10.0,
        0.04 * (float(cabals_malla.max()) - float(cabals_malla.min())),
    )
    z_marcador = estudi.cabal_centre_mm3_s + marge_marcador
    eix_superficie.plot(
        [estudi.columnes_centre, estudi.columnes_centre],
        [estudi.files_centre, estudi.files_centre],
        [estudi.cabal_centre_mm3_s, z_marcador],
        color="#e31a1c",
        linewidth=1.5,
        zorder=10,
    )
    eix_superficie.scatter(
        [estudi.columnes_centre],
        [estudi.files_centre],
        [z_marcador],
        color="#e31a1c",
        edgecolor="white",
        linewidth=0.8,
        depthshade=False,
        s=90,
        zorder=11,
        label="Punt de funcionament",
    )
    eix_superficie.set_xlabel("Columnes")
    eix_superficie.set_ylabel("Files")
    eix_superficie.set_zlabel("Q total [mm³/s]")
    eix_superficie.invert_xaxis()
    eix_superficie.view_init(elev=48, azim=45)
    eix_superficie.set_title(
        f"Efecte de les dimensions per ΔH = {estudi.salt_centre_m:g} m"
    )
    eix_superficie.legend()
    figura_superficie.colorbar(
        superficie,
        ax=eix_superficie,
        shrink=0.65,
        pad=0.12,
        label="Q total [mm³/s]",
    )
    return figura_salt, figura_superficie
