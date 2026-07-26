"""Pàgina Marimo WASM per comparar els solvers d'HN3Ttk."""

import marimo

__generated_with = "0.23.15"
app = marimo.App(width="full")


@app.cell
def _():
    import inspect
    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import scipy as _scipy
    import hn3ttk as _hn3ttk

    from comparacio_solvers import comparar_solvers

    return comparar_solvers, inspect, mo, np, plt


@app.cell
def _(mo):
    mo.md(
        r"""
        # Comparació dels solvers al punt d'interès

        [← Torna al simulador de la xarxa](../)

        Aquesta pàgina resol **exactament la mateixa xarxa** amb quatre
        algoritmes d'HN3Ttk. La comparació utilitza la mateixa estimació
        inicial i exigeix un residu màxim de \(10^{-12}\ \mathrm{m^3/s}\).

        Es comparen:

        1. Newton-Raphson;
        2. Newton-Raphson amortit;
        3. `SciPy root`, mètode `hybr`;
        4. `SciPy least_squares`, mètode `trf`.

        > El temps depèn de l'ordinador i del navegador. Convergència, cabal
        > i residu són els criteris tècnics principals.

        > El codi de la funció de comparació es pot consultar al final.
        """
    )
    return


@app.cell
def _(mo):
    controls = mo.ui.dictionary(
        {
            "files": mo.ui.number(start=1, stop=15, step=1, value=10, label="Files"),
            "columnes": mo.ui.number(
                start=1, stop=20, step=1, value=14, label="Columnes"
            ),
            "salt": mo.ui.number(
                start=0.0,
                stop=1.0,
                step=0.000001,
                value=1.0,
                label="Diferència piezomètrica ΔH [m]",
            ),
            "altura": mo.ui.number(
                start=0.1, stop=2.0, step=0.01, value=0.5, label="Altura [mm]"
            ),
            "k": mo.ui.number(
                start=0.1, stop=10.0, step=0.001, value=2.483, label="K"
            ),
            "n": mo.ui.number(
                start=1.0, stop=3.0, step=0.01, value=1.8, label="n"
            ),
        }
    )
    formulari = controls.form(
        submit_button_label="Compara els solvers",
        bordered=True,
    )
    formulari
    return (formulari,)


@app.cell
def _(comparar_solvers, formulari, mo):
    valors = formulari.value or {
        "files": 10,
        "columnes": 14,
        "salt": 1.0,
        "altura": 0.5,
        "k": 2.483,
        "n": 1.8,
    }
    mo.output.replace(
        mo.callout("Executant els quatre solvers al navegador…", kind="info")
    )
    resultats = comparar_solvers(
        files=int(valors["files"]),
        columnes=int(valors["columnes"]),
        salt_m=float(valors["salt"]),
        altura_canal_mm=float(valors["altura"]),
        coeficient_cel_lular_k=float(valors["k"]),
        exponent_cel_lular_n=float(valors["n"]),
    )
    return resultats, valors


@app.cell
def _(mo, resultats, valors):
    files_taula = "\n".join(
        "| {nom} | {ok} | {q} | {residu:.3e} | {it} | {temps:.4f} |".format(
            nom=r.nom,
            ok="Sí" if r.convergencia else "No",
            q="—" if r.cabal_mm3_s is None else f"{r.cabal_mm3_s:.6f}",
            residu=r.residu_maxim_m3_s,
            it=r.iteracions,
            temps=r.temps_s,
        )
        for r in resultats
    )
    mo.md(
        fr"""
        ## Resultats

        Punt comparat: **{int(valors["files"])} × {int(valors["columnes"])}**,
        \(\Delta H={float(valors["salt"]):.6f}\ \mathrm{{m}}\).

        | Solver | Convergeix | Q [mm³/s] | Residu màxim [m³/s] | Iteracions | Temps [s] |
        |---|:---:|---:|---:|---:|---:|
        {files_taula}
        """
    )
    return


@app.cell
def _(mo, np, plt, resultats):
    noms = [r.nom for r in resultats]
    temps = [r.temps_s for r in resultats]
    residus = [
        max(r.residu_maxim_m3_s, np.finfo(float).tiny)
        for r in resultats
    ]
    colors = ["#18864b" if r.convergencia else "#d62728" for r in resultats]

    figura, (eix_temps, eix_residu) = plt.subplots(
        1, 2, figsize=(14, 5.5), constrained_layout=True
    )
    eix_temps.barh(noms, temps, color=colors)
    eix_temps.set_xlabel("Temps [s]")
    eix_temps.set_title("Temps d'execució")
    eix_temps.grid(axis="x", alpha=0.25)

    eix_residu.barh(noms, residus, color=colors)
    eix_residu.axvline(1.0e-12, color="black", linestyle="--", label="Tolerància")
    eix_residu.set_xscale("log")
    eix_residu.set_xlabel("Residu màxim [m³/s]")
    eix_residu.set_title("Qualitat del balanç nodal")
    eix_residu.grid(axis="x", alpha=0.25)
    eix_residu.legend()

    mo.vstack(
        [
            figura,
            mo.md(
                """
                Verd indica que el solver declara convergència i compleix
                simultàniament la tolerància de residu. Vermell indica que
                almenys una de les dues condicions no es compleix.
                """
            ),
        ]
    )
    return


@app.cell
def _(comparar_solvers, inspect, mo):
    mo.md(
        "# Codi de la comparació\n\n"
        "```python\n"
        + inspect.getsource(comparar_solvers)
        + "\n```"
    )
    return


if __name__ == "__main__":
    app.run()
