"""Estudi paramètric local al voltant d'un punt de funcionament."""

from __future__ import annotations

from dataclasses import dataclass

from xarxa_microxip import avaluar_xarxa


@dataclass(frozen=True)
class EstudiEntorn:
    """Resultats de la corba de salt i de la superfície de dimensions."""

    files_centre: int
    columnes_centre: int
    salt_centre_m: float
    cabal_centre_mm3_s: float
    salts_m: tuple[float, ...]
    cabals_salt_mm3_s: tuple[float, ...]
    convergencies_salt: tuple[bool, ...]
    files: tuple[int, ...]
    columnes: tuple[int, ...]
    cabals_dimensions_mm3_s: tuple[tuple[float, ...], ...]
    convergencies_dimensions: tuple[tuple[bool, ...], ...]


def estudi_referencia_precalculat() -> EstudiEntorn:
    """Retorna el mateix estudi 10×14 mostrat a la llibreta estàtica."""
    cabals_dimensions = (
        (3941.269415, 3996.232165, 4040.613858, 4076.261661, 4104.615443),
        (3889.394708, 3935.896297, 3973.506880, 4003.737940, 4027.757579),
        (3827.579445, 3866.025829, 3897.150858, 3922.156227, 3941.971831),
        (3756.320294, 3791.459443, 3819.921173, 3842.792527, 3860.912007),
        (3687.998203, 3720.437570, 3746.901788, 3768.227169, 3785.091172),
    )
    return EstudiEntorn(
        files_centre=10,
        columnes_centre=14,
        salt_centre_m=1.0,
        cabal_centre_mm3_s=3897.150858,
        salts_m=(0.6, 0.8, 0.9, 1.0, 1.1, 1.2, 1.4),
        cabals_salt_mm3_s=(
            2959.831440,
            3449.462435,
            3677.798566,
            3897.150858,
            4105.933723,
            4310.618205,
            4695.349023,
        ),
        convergencies_salt=(True,) * 7,
        files=(8, 9, 10, 11, 12),
        columnes=(12, 13, 14, 15, 16),
        cabals_dimensions_mm3_s=cabals_dimensions,
        convergencies_dimensions=tuple(
            tuple(True for _ in range(5))
            for _ in range(5)
        ),
    )


def estudiar_entorn_punt(
    *,
    files: int,
    columnes: int,
    salt_m: float,
    altura_canal_mm: float,
    coeficient_cel_lular_k: float,
    exponent_cel_lular_n: float,
    amplitud_salt_percent: float = 40.0,
    radi_dimensions: int = 2,
) -> EstudiEntorn:
    """Avalua Q al voltant del punt indicat, com a l'exemple estàtic.

    Es resolen set salts equiespaiats dins ``±amplitud_salt_percent`` i una
    malla de dimensions enteres ``±radi_dimensions``. El punt central es
    calcula una sola vegada i es reutilitza als dos estudis.
    """
    if salt_m <= 0:
        raise ValueError("El salt piezomètric ha de ser positiu.")
    if not 0 < amplitud_salt_percent < 100:
        raise ValueError("L'amplitud del salt ha d'estar entre 0 i 100%.")
    if radi_dimensions < 1:
        raise ValueError("El radi de dimensions ha de ser com a mínim 1.")

    fracció = amplitud_salt_percent / 100.0
    salts = tuple(
        salt_m * (1.0 - fracció + 2.0 * fracció * i / 6.0)
        for i in range(7)
    )
    valors_files = tuple(range(max(1, files - radi_dimensions), files + radi_dimensions + 1))
    valors_columnes = tuple(
        range(max(1, columnes - radi_dimensions), columnes + radi_dimensions + 1)
    )

    memòria: dict[tuple[int, int, float], tuple[float, bool]] = {}

    def resoldre(f: int, c: int, h: float) -> tuple[float, bool]:
        clau = (f, c, round(h, 14))
        if clau not in memòria:
            resultat = avaluar_xarxa(
                f,
                c,
                h,
                altura_canal_mm=altura_canal_mm,
                coeficient_cel_lular_k=coeficient_cel_lular_k,
                exponent_cel_lular_n=exponent_cel_lular_n,
                imprimir_resum=False,
            )
            memòria[clau] = (
                resultat.cabal_entrada_mm3_s,
                resultat.resultat.success,
            )
        return memòria[clau]

    resultats_salt = tuple(resoldre(files, columnes, h) for h in salts)
    resultats_dimensions = tuple(
        tuple(resoldre(f, c, salt_m) for c in valors_columnes)
        for f in valors_files
    )
    cabal_centre, _ = resoldre(files, columnes, salt_m)

    return EstudiEntorn(
        files_centre=files,
        columnes_centre=columnes,
        salt_centre_m=salt_m,
        cabal_centre_mm3_s=cabal_centre,
        salts_m=salts,
        cabals_salt_mm3_s=tuple(valor[0] for valor in resultats_salt),
        convergencies_salt=tuple(valor[1] for valor in resultats_salt),
        files=valors_files,
        columnes=valors_columnes,
        cabals_dimensions_mm3_s=tuple(
            tuple(valor[0] for valor in fila)
            for fila in resultats_dimensions
        ),
        convergencies_dimensions=tuple(
            tuple(valor[1] for valor in fila)
            for fila in resultats_dimensions
        ),
    )
