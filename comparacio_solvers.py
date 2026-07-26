"""Comparació reproduïble dels solvers d'HN3Ttk."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from hn3ttk.solvers import (
    SolverResult,
    solve_damped_newton_raphson,
    solve_newton_raphson,
    solve_scipy_least_squares,
    solve_scipy_root,
)

from xarxa_microxip import construir_sistema, generar_topologia


@dataclass(frozen=True)
class ResultatSolver:
    """Fila comparable retornada per un solver."""

    nom: str
    convergencia: bool
    cabal_mm3_s: float | None
    residu_maxim_m3_s: float
    iteracions: int
    temps_s: float
    missatge: str


def comparar_solvers(
    *,
    files: int,
    columnes: int,
    salt_m: float,
    altura_canal_mm: float = 0.5,
    coeficient_cel_lular_k: float = 2.483,
    exponent_cel_lular_n: float = 1.8,
    tolerancia_residu: float = 1.0e-12,
) -> tuple[ResultatSolver, ...]:
    """Resol el mateix sistema amb quatre algoritmes i en mesura el temps."""
    sistema = construir_sistema(
        generar_topologia(files, columnes),
        salt_piezometric_m=salt_m,
        altura_canal_mm=altura_canal_mm,
        coeficient_cel_lular_k=coeficient_cel_lular_k,
        exponent_cel_lular_n=exponent_cel_lular_n,
    )
    solvers: tuple[tuple[str, Callable[[], SolverResult]], ...] = (
        (
            "Newton-Raphson",
            lambda: solve_newton_raphson(
                sistema,
                tolerance=tolerancia_residu,
                step_tolerance=tolerancia_residu,
                max_iterations=100,
            ),
        ),
        (
            "Newton amortit",
            lambda: solve_damped_newton_raphson(
                sistema,
                tolerance=tolerancia_residu,
                step_tolerance=tolerancia_residu,
                max_iterations=100,
            ),
        ),
        (
            "SciPy root (hybr)",
            lambda: solve_scipy_root(
                sistema,
                method="hybr",
                tolerance=1.0e-10,
                residual_tolerance=tolerancia_residu,
                max_function_evaluations=3000,
            ),
        ),
        (
            "SciPy least_squares (trf)",
            lambda: solve_scipy_least_squares(
                sistema,
                method="trf",
                tolerance=tolerancia_residu,
                residual_tolerance=tolerancia_residu,
                max_function_evaluations=3000,
            ),
        ),
    )

    files_resultat: list[ResultatSolver] = []
    for nom, executar in solvers:
        inici = perf_counter()
        try:
            resultat = executar()
            temps = perf_counter() - inici
            cabal = None
            if resultat.state is not None:
                cabal = (
                    float(resultat.state["links"]["tub_1"]["flow_rate"])
                    * 1.0e9
                )
            files_resultat.append(
                ResultatSolver(
                    nom=nom,
                    convergencia=bool(resultat.success)
                    and resultat.max_abs_residual <= tolerancia_residu,
                    cabal_mm3_s=cabal,
                    residu_maxim_m3_s=float(resultat.max_abs_residual),
                    iteracions=int(resultat.iterations),
                    temps_s=temps,
                    missatge=str(resultat.message),
                )
            )
        except Exception as error:
            files_resultat.append(
                ResultatSolver(
                    nom=nom,
                    convergencia=False,
                    cabal_mm3_s=None,
                    residu_maxim_m3_s=float("inf"),
                    iteracions=0,
                    temps_s=perf_counter() - inici,
                    missatge=f"{type(error).__name__}: {error}",
                )
            )
    return tuple(files_resultat)
