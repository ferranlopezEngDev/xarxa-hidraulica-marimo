"""Aplicació Marimo WASM interactiva per publicar amb GitHub Pages."""

import marimo

__generated_with = "0.23.15"
app = marimo.App(width="full")


@app.cell
def _():
    import inspect
    import marimo as mo
    import matplotlib as _matplotlib
    import numpy as _numpy
    import scipy as _scipy
    import hn3ttk as _hn3ttk

    from channel_connections import (
        power_law_channel_from_pa_mm3s,
        rectangular_channel_from_mm,
    )
    from xarxa_microxip import (
        avaluar_xarxa,
        construir_sistema,
        generar_topologia,
    )
    from estudis_web import (
        estudi_referencia_precalculat,
        estudiar_entorn_punt,
    )
    from visualitzacio_web import (
        crear_figura_resultats,
        crear_figures_entorn,
    )

    return (
        avaluar_xarxa,
        construir_sistema,
        crear_figura_resultats,
        crear_figures_entorn,
        estudi_referencia_precalculat,
        estudiar_entorn_punt,
        generar_topologia,
        inspect,
        mo,
        power_law_channel_from_pa_mm3s,
        rectangular_channel_from_mm,
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        # Simulador hidràulic de la xarxa de refrigeració

        Aquesta aplicació executa **HN3Ttk directament al navegador** mitjançant
        WebAssembly. No envia dades a cap servidor.

        El cas inicial és exactament la xarxa proporcionada: 10 files,
        14 columnes, altura de canal de 0,5 mm, \(K=2{,}483\) i \(n=1{,}8\).
        Modifiqueu els paràmetres i premeu **Calcula la xarxa**.

        > **Codi font:** primer s'explica tot el procediment de manera
        > conceptual. El codi complet de les funcions utilitzades es presenta
        > a l'apèndix final d'aquesta mateixa llibreta.

        > **Ús de Codex:** s'ha utilitzat Codex com a eina de suport per
        > preparar i documentar aquesta llibreta. L'objectiu és mostrar un
        > exemple complet, clar i interactiu de com es pot utilitzar el
        > repositori **HN3Ttk** en un cas d'estudi real.

        **[Obre la pàgina de comparació dels solvers →](./solvers/)**
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 1. Dades extretes de la figura

        La xarxa de referència té 10 files i 14 columnes de cel·les. Això dona:

        \[
        N_\mathrm{nodes}=2+2m(n+1)=302,
        \qquad
        N_\mathrm{canals}=m(3n+2)=440.
        \]

        El peu de figura estableix que els tubs blaus i vermells tenen secció
        rectangular d'altura \(h=0{,}5\ \mathrm{mm}\). Aquesta \(h\) és una
        **dimensió geomètrica**, no una pèrdua de càrrega.

        Les dades restants són:

        - col·lectors verticals: amplada 1,4 mm;
        - laterals: longitud 1,2 mm i amplada variable;
        - canals verds: \(K=2{,}483\), \(n=1{,}8\);
        - llei experimental verda:
          \(\Delta P[\mathrm{Pa}]=KQ[\mathrm{mm^3/s}]^n\).
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 2. Construcció paramètrica de la topologia

        Les files es numeren de baix a dalt i les columnes de dreta a
        esquerra, seguint el recorregut del fluid pel lateral blau.

        Per a cada fila es generen automàticament:

        1. un node del col·lector blau;
        2. \(n\) nodes del lateral blau;
        3. \(n\) nodes del lateral vermell;
        4. un node del col·lector vermell;
        5. \(n\) canals verds que uneixen cada parella de nodes.

        Finalment s'afegeixen el node d'entrada i el de sortida. El constructor
        verifica identificadors consecutius, connexions vàlides i absència de
        nodes aïllats abans de crear el sistema hidràulic.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 3. Model hidràulic de cada canal

        HN3Ttk treballa amb cabals en \(\mathrm{m^3/s}\) i altures en metres.
        Totes les connexions segueixen el conveni:

        \[
        \Delta H=-K\,\operatorname{sign}(Q)|Q|^n.
        \]

        ### Tubs rectangulars blaus i vermells

        Es calcula l'àrea \(A=wh\), el perímetre mullat \(P=2(w+h)\) i el
        diàmetre hidràulic:

        \[
        D_h=\frac{4A}{P}=\frac{2wh}{w+h}.
        \]

        El wrapper conserva la velocitat real de la secció rectangular i usa
        `PipeLocalPowerLaw` per actualitzar \(K(Q)\) i \(n(Q)\) segons Reynolds.

        ### Canals verds

        La llei de la figura es converteix a les unitats d'HN3Ttk:

        \[
        K_\mathrm{SI}
        =\frac{K}{\rho g\,(10^{-9})^n}.
        \]
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 4. Condicions de contorn i equacions

        Es pren la sortida com a referència:

        \[
        H_\mathrm{sortida}=0,
        \qquad
        H_\mathrm{entrada}=\Delta H.
        \]

        Els altres nodes tenen altura desconeguda. HN3Ttk imposa a cadascun
        el balanç de continuïtat:

        \[
        R_i=\sum Q_\mathrm{entra}-\sum Q_\mathrm{surt}=0.
        \]

        El sistema no prescriu el cabal total: aquest és el resultat de
        resoldre simultàniament les pèrdues de càrrega i tots els balanços.
        """
    )
    return


@app.cell
def _(mo):
    controls_xarxa = mo.ui.dictionary(
        {
            "files": mo.ui.number(
                start=1,
                stop=15,
                step=1,
                value=10,
                label="Nombre de files",
            ),
            "columnes": mo.ui.number(
                start=1,
                stop=20,
                step=1,
                value=14,
                label="Nombre de columnes",
            ),
            "salt_h": mo.ui.number(
                start=0.0,
                stop=1.0,
                step=0.000001,
                value=1.0,
                label="Diferència piezomètrica ΔH [m]",
            ),
            "altura": mo.ui.number(
                start=0.1,
                stop=2.0,
                step=0.01,
                value=0.5,
                label="Altura del canal [mm]",
            ),
            "k": mo.ui.number(
                start=0.1,
                stop=10.0,
                step=0.05,
                value=2.483,
                label="Coeficient K dels canals verds",
            ),
            "n": mo.ui.number(
                start=1.0,
                stop=3.0,
                step=0.05,
                value=1.8,
                label="Exponent n dels canals verds",
            ),
        },
        label="Paràmetres de la xarxa",
    )
    formulari_xarxa = controls_xarxa.form(
        submit_button_label="Calcula la xarxa",
        bordered=True,
    )
    formulari_xarxa
    return (formulari_xarxa,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 5. Resolució amb HN3Ttk

        En prémer el botó es crea una instància de `HydraulicSystem`, s'hi
        afegeixen els nodes, les connexions i els links, i es resol el vector
        d'altures desconegudes amb el solver propi de **continuació amb
        Newton-Raphson amortit**:
        `solve_alpha_continuation_damped_newton`.

        La cel·la de codi següent és l'exemple mínim d'ús del repositori:
        rep els paràmetres del formulari i efectua una sola crida a
        `avaluar_xarxa`.
        """
    )
    return


@app.cell
def _(formulari_xarxa):
    parametres_web = formulari_xarxa.value or {
        "files": 10,
        "columnes": 14,
        "salt_h": 1.0,
        "altura": 0.5,
        "k": 2.483,
        "n": 1.8,
    }
    return (parametres_web,)


@app.cell
def _(avaluar_xarxa, mo, parametres_web):
    mo.output.replace(
        mo.callout(
            "Calculant la xarxa al navegador…",
            kind="info",
        )
    )
    avaluacio_web = avaluar_xarxa(
        int(parametres_web["files"]),
        int(parametres_web["columnes"]),
        float(parametres_web["salt_h"]),
        altura_canal_mm=float(parametres_web["altura"]),
        coeficient_cel_lular_k=float(parametres_web["k"]),
        exponent_cel_lular_n=float(parametres_web["n"]),
        imprimir_resum=False,
    )
    return (avaluacio_web,)


@app.cell
def _(avaluacio_web, mo):
    resultat_web = avaluacio_web.resultat
    estat_convergencia = "Sí" if resultat_web.success else "No"
    avisos_web = "<br>".join(avaluacio_web.avisos)
    mo.md(
        f"""
        ## Resultat calculat

        | Magnitud | Valor |
        |---|---:|
        | Dimensions | {avaluacio_web.topologia.files} × {avaluacio_web.topologia.columnes} |
        | Nodes | {avaluacio_web.topologia.nombre_nodes} |
        | Canals | {avaluacio_web.topologia.nombre_canals} |
        | ΔH | {avaluacio_web.salt_piezometric_m:.3f} m |
        | Altura del canal | {avaluacio_web.altura_canal_mm:.3f} mm |
        | K cel·lular | {avaluacio_web.coeficient_cel_lular_k:.4g} |
        | n cel·lular | {avaluacio_web.exponent_cel_lular_n:.4g} |
        | Solver | Continuació amb Newton amortit |
        | **Cabal total** | **{avaluacio_web.cabal_entrada_mm3_s:.3f} mm³/s** |
        | Convergència | {estat_convergencia} |
        | Residu màxim | {resultat_web.max_abs_residual:.3e} m³/s |

        {avisos_web}
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 6. Comprovacions de la solució

        Una solució s'accepta quan el solver convergeix i el residu màxim de
        continuïtat és inferior a la tolerància. També es calcula el nombre de
        Reynolds de tots els tubs rectangulars per informar dels règims
        laminar, de transició o turbulent.

        El cabal total que es mostra és el cabal del primer tub, connectat al
        node d'entrada. Per continuïtat coincideix amb el cabal de sortida.
        """
    )
    return


@app.cell
def _(avaluacio_web, crear_figura_resultats, mo):
    figura_web = crear_figura_resultats(avaluacio_web)
    mo.vstack(
        [
            mo.md("## Distribució interna de la solució"),
            figura_web,
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ### Interpretació

        - Els colors dels nodes mostren l'altura piezomètrica.
        - El mapa de calor mostra el cabal de cadascun dels canals verds.
        - El cabal total correspon al tub d'entrada.
        - Un residu proper a zero confirma el balanç de continuïtat.

        En xarxes grans el càlcul pot tardar uns segons perquè totes les
        equacions es resolen localment al navegador.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 7. Comportament al voltant del punt de funcionament

        El resultat anterior es pren com a **punt central**. Igual que a
        l'exemple estàtic, es fan dos estudis:

        1. set valors de \(\Delta H\) al voltant del valor seleccionat,
           mantenint la geometria;
        2. una superfície 3D variant files i columnes, mantenint \(\Delta H\).

        En obrir la pàgina es mostren immediatament els resultats precalculats
        del cas de referència 10 × 14. L'amplitud del salt i el radi de la
        malla es poden modificar; en prémer el botó, els gràfics es recalculen
        al navegador al voltant del punt seleccionat al formulari principal.
        """
    )
    return


@app.cell
def _(mo):
    controls_estudi = mo.ui.dictionary(
        {
            "amplitud": mo.ui.number(
                start=10,
                stop=80,
                step=5,
                value=40,
                label="Variació de ΔH a cada costat [%]",
            ),
            "radi": mo.ui.number(
                start=1,
                stop=3,
                step=1,
                value=2,
                label="Variació de files i columnes [±]",
            ),
        },
        label="Entorn del punt de funcionament",
    )
    formulari_estudi = controls_estudi.form(
        submit_button_label="Calcula l'estudi paramètric",
        bordered=True,
    )
    formulari_estudi
    return (formulari_estudi,)


@app.cell
def _(
    estudi_referencia_precalculat,
    estudiar_entorn_punt,
    formulari_estudi,
    mo,
    parametres_web,
):
    if formulari_estudi.value is None:
        estudi_entorn = estudi_referencia_precalculat()
        origen_estudi = (
            "Resultats precalculats del cas de referència 10 × 14, "
            "amb ΔH = 1 m."
        )
    else:
        configuracio_estudi = formulari_estudi.value
        mo.output.replace(
            mo.callout(
                "Resolent els casos de l'estudi paramètric al navegador…",
                kind="info",
            )
        )
        estudi_entorn = estudiar_entorn_punt(
            files=int(parametres_web["files"]),
            columnes=int(parametres_web["columnes"]),
            salt_m=float(parametres_web["salt_h"]),
            altura_canal_mm=float(parametres_web["altura"]),
            coeficient_cel_lular_k=float(parametres_web["k"]),
            exponent_cel_lular_n=float(parametres_web["n"]),
            amplitud_salt_percent=float(configuracio_estudi["amplitud"]),
            radi_dimensions=int(configuracio_estudi["radi"]),
        )
        origen_estudi = "Resultats recalculats al navegador."
    return estudi_entorn, origen_estudi


@app.cell
def _(crear_figures_entorn, estudi_entorn, mo, origen_estudi):
    figura_salt, figura_superficie = crear_figures_entorn(estudi_entorn)
    totes_convergeixen = all(estudi_entorn.convergencies_salt) and all(
        valor
        for fila in estudi_entorn.convergencies_dimensions
        for valor in fila
    )
    mo.vstack(
        [
            mo.md(
                f"""
                ### Resultats de l'estudi local

                **{origen_estudi}**

                El punt vermell és el cas seleccionat al formulari principal.
                Tots els casos han convergit: **{'sí' if totes_convergeixen else 'no'}**.
                """
            ),
            figura_salt,
            figura_superficie,
        ]
    )
    return


@app.cell
def _(
    avaluar_xarxa,
    construir_sistema,
    crear_figura_resultats,
    crear_figures_entorn,
    estudi_referencia_precalculat,
    estudiar_entorn_punt,
    generar_topologia,
    inspect,
    mo,
    power_law_channel_from_pa_mm3s,
    rectangular_channel_from_mm,
):
    funcions_documentades = (
        ("generar_topologia", generar_topologia),
        ("rectangular_channel_from_mm", rectangular_channel_from_mm),
        (
            "power_law_channel_from_pa_mm3s",
            power_law_channel_from_pa_mm3s,
        ),
        ("construir_sistema", construir_sistema),
        ("avaluar_xarxa", avaluar_xarxa),
        ("estudi_referencia_precalculat", estudi_referencia_precalculat),
        ("estudiar_entorn_punt", estudiar_entorn_punt),
        ("crear_figura_resultats", crear_figura_resultats),
        ("crear_figures_entorn", crear_figures_entorn),
    )
    blocs_codi = []
    for nom_funcio, funcio in funcions_documentades:
        codi_funcio = inspect.getsource(funcio)
        blocs_codi.append(
            f"### `{nom_funcio}`\n\n```python\n{codi_funcio}\n```"
        )

    mo.md(
        """
        # Apèndix: codi complet de les funcions

        A continuació es presenta el codi real executat per aquesta aplicació.
        Les funcions estan ordenades segons el procediment explicat anteriorment.

        """
        + "\n\n".join(blocs_codi)
    )
    return


if __name__ == "__main__":
    app.run()
