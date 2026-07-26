# Simulador WASM de la xarxa de refrigeració

Aplicació Marimo que resol la xarxa amb HN3Ttk directament al navegador.
Està preparada per publicar-se amb GitHub Pages i no necessita cap servidor
Python.

S'ha utilitzat Codex com a eina de suport per preparar i documentar aquesta
llibreta, concebuda com un exemple complet i interactiu d'ús del repositori
HN3Ttk.

## Paràmetres interactius

- nombre de files;
- nombre de columnes;
- diferència d'altura piezomètrica;
- altura dels canals rectangulars;
- coeficient `K` dels canals verds;
- exponent `n` dels canals verds.

La mateixa aplicació també calcula l'entorn del punt de funcionament:

- corba de cabal variant `ΔH`;
- superfície 3D variant files i columnes;
- amplitud de l'estudi configurable.

El cas inicial reprodueix la xarxa proporcionada de 10 × 14 cel·les.

## Prova local

Instal·lació:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Execució com a aplicació Marimo:

```powershell
.\.venv\Scripts\marimo.exe run app.py
```

Construcció WASM:

```powershell
.\.venv\Scripts\marimo.exe export html-wasm app.py -o site --mode run --show-code -f
```

La carpeta `site` s'ha de servir mitjançant HTTP:

```powershell
python -m http.server --directory site
```

## Publicació amb GitHub Pages

1. Crear un repositori nou a GitHub.
2. Copiar-hi el contingut d'aquesta carpeta.
3. Fer `push` a la branca `main`.
4. A `Settings > Pages > Build and deployment`, seleccionar
   `GitHub Actions`.

El workflow `.github/workflows/pages.yml` construeix i publica l'aplicació
automàticament.

## Estructura

- `app.py`: interfície Marimo interactiva.
- `xarxa_microxip.py`: constructor i solver paramètric.
- `channel_connections.py`: adaptació de les connexions rectangulars i KQⁿ.
- `network_image_data.py`: dades transcrites del cas original.
- `visualitzacio_web.py`: gràfics, separats de l'exemple d'ús.
- `estudis_web.py`: estudi paramètric al voltant del punt seleccionat.
- `solvers.py`: pàgina WASM de comparació dels solvers.
- `comparacio_solvers.py`: execució homogènia i mesura dels solvers.
- `hn3ttk/`: còpia local de la biblioteca, empaquetada dins del WASM.
- `site/`: exportació WASM llesta per servir.

El codi de la llibreta es mostra per defecte perquè serveixi com a exemple net
d'ús del repositori.
