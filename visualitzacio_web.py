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
