# Marimo -- Reference exhaustive

> Document de reference pour la creation de skills Claude Code et le developpement de dashboards/apps Marimo.
> Derniere mise a jour : 2026-04-10

---

## Table des matieres

1. [Architecture et concepts](#1-architecture-et-concepts)
2. [Elements UI complets](#2-elements-ui-complets)
3. [Layout](#3-layout)
4. [Charts et visualisation](#4-charts-et-visualisation)
5. [Data -- SQL, DataFrames, Transforms](#5-data--sql-dataframes-transforms)
6. [Deployment](#6-deployment)
7. [Theming et CSS](#7-theming-et-css)
8. [Templates et patterns (gallery)](#8-templates-et-patterns-gallery)
9. [Best practices et pieges courants](#9-best-practices-et-pieges-courants)

---

## 1. Architecture et concepts

### 1.1 Qu'est-ce que Marimo ?

Marimo est un **notebook Python reactif** open-source. Contrairement a Jupyter, chaque notebook Marimo est un **fichier Python valide** (`.py`), versionnable avec Git, executable comme script ou deployable comme application web.

### 1.2 Reactivite automatique

Le modele fondamental de Marimo repose sur un **DAG (graphe acyclique dirige)** de cellules. Quand une cellule change, toutes les cellules qui en dependent sont **automatiquement re-executees** dans l'ordre topologique.

```python
import marimo

app = marimo.App(width="medium")

@app.cell
def _():
    import marimo as mo
    return (mo,)

@app.cell
def _(mo):
    slider = mo.ui.slider(1, 100, value=50, label="Valeur")
    slider
    return (slider,)

@app.cell
def _(slider):
    # Cette cellule se re-execute automatiquement quand le slider change
    result = slider.value * 2
    result
    return (result,)

if __name__ == "__main__":
    app.run()
```

**Regles cles** :
- Chaque cellule est une **fonction Python** decoree par `@app.cell`
- Les variables definies dans une cellule sont accessibles dans les autres via le `return`
- Les variables prefixees par `_` (underscore) sont **privees** a la cellule (non exportees)
- Une variable ne peut etre definie que dans **une seule cellule** (pas de redefinition)

### 1.3 `app.setup` -- Bloc d'initialisation global

Le bloc `app.setup` est execute **une seule fois** au demarrage, avant toutes les cellules. Ideal pour les imports et la configuration globale.

```python
import marimo

app = marimo.App(width="full")

with app.setup:
    import marimo as mo
    import altair as alt
    import pandas as pd
    import polars as pl

@app.cell
def _():
    # mo, alt, pd, pl sont disponibles ici sans import
    data = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    data
    return (data,)
```

**Avantages** :
- Les imports sont partages entre toutes les cellules sans `return`
- Execute une seule fois (pas de re-execution reactive)
- Equivalent a un "preambule" Python

### 1.4 `@app.function` -- Fonctions reutilisables

Les fonctions decorees par `@app.function` sont **visibles par toutes les cellules** et participent au DAG reactif.

```python
@app.function(hide_code=True)
def clean_data(dataf, investment_records):
    investments_df = pl.DataFrame(investment_records)
    return (
        dataf.drop(["Dividends", "Stock Splits", "Volume"])
        .join(investments_df, on=["Date", "Ticker"], how="left")
        .with_columns(pl.col("Investment").fill_null(0))
        .sort("Ticker", "Date")
    )

@app.function(hide_code=True)
def calculate_portfolio_value(dataf):
    return (
        dataf.with_columns(
            CumInvestment=pl.col("Investment").cum_sum().over("Ticker")
        )
        .filter(pl.col("CumInvestment") > 0)
        .with_columns(
            SharesBought=pl.when(pl.col("Investment") > 0)
            .then(pl.col("Investment") / pl.col("Close"))
            .otherwise(0)
        )
    )

# Utilisation dans une cellule -- chainable avec .pipe()
@app.cell
def _(df, records):
    result = (
        df
        .pipe(clean_data, investment_records=records)
        .pipe(calculate_portfolio_value)
    )
    return (result,)
```

**Caracteristiques** :
- Accepte `hide_code=True` pour masquer le code en mode app
- Visible globalement sans `return` explicite
- Ideal pour les pipelines de transformation (pattern `.pipe()`)

### 1.5 `@app.cell(hide_code=True)` -- Masquer le code

En mode app (`marimo run`), le code source des cellules est masque par defaut. En mode edit, on peut marquer certaines cellules pour qu'elles soient masquees en mode app.

```python
@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Mon Dashboard
    Ce texte est visible mais le code Python est masque.
    """)
    return
```

### 1.6 `mo.stop()` -- Arret conditionnel

Arrete l'execution d'une cellule (et de ses dependantes) si une condition est remplie. Utile pour les gardes.

```python
@app.cell
def _(filtered_data, mo):
    mo.stop(len(filtered_data) == 0, mo.callout("Aucune donnee selectionnee.", kind="warn"))
    # Le code ci-dessous ne s'execute que si filtered_data n'est pas vide
    chart = create_chart(filtered_data)
    chart
    return (chart,)
```

### 1.7 `mo.state()` -- Etat mutable partage

Pour les cas ou la reactivite naturelle ne suffit pas (ex: boutons qui modifient un etat), `mo.state()` cree un couple getter/setter.

```python
@app.cell
def _():
    get_start_date, set_start_date = mo.state(pd.to_datetime("2020-01-01"))
    get_end_date, set_end_date = mo.state(pd.to_datetime("2025-12-31"))
    return get_start_date, set_start_date, get_end_date, set_end_date

@app.cell
def _(get_start_date, set_start_date):
    start_date = mo.ui.date(
        label="Date debut",
        value=get_start_date().strftime("%Y-%m-%d"),
        on_change=lambda x: set_start_date(pd.to_datetime(x)),
    )
    start_date
    return (start_date,)
```

### 1.8 `mo.cache` -- Mise en cache

Decore une fonction pour cacher ses resultats. Utile pour les calculs longs ou les appels API.

```python
@app.cell
def _(cached_data, threshold):
    @mo.cache
    def heavy_computation(threshold_value):
        return cached_data.pipe(remove_bots, max_session_hours=threshold_value)
    
    result = heavy_computation(threshold.value)
    return (result,)
```

### 1.9 Mode run vs edit

| Mode | Commande | Usage |
|------|----------|-------|
| **Edit** | `marimo edit app.py` | Developpement, edition des cellules |
| **Run** | `marimo run app.py` | Production, lecture seule, app web |

En mode `run`, les cellules avec `hide_code=True` n'affichent que leur sortie. L'utilisateur interagit uniquement via les elements UI.

---

## 2. Elements UI complets

### 2.1 Liste exhaustive des `mo.ui.*`

Tous les elements UI sont reactifs : quand l'utilisateur interagit, `.value` change et les cellules dependantes se re-executent.

#### Entrees de base

| Element | Description | Exemple |
|---------|------------|---------|
| `mo.ui.slider` | Curseur numerique | `mo.ui.slider(0, 100, value=50, step=1, label="Prix")` |
| `mo.ui.range_slider` | Curseur double (intervalle) | `mo.ui.range_slider(0, 100, value=[20, 80], label="Fourchette")` |
| `mo.ui.number` | Champ numerique | `mo.ui.number(start=0, stop=1000, value=100, label="Montant")` |
| `mo.ui.text` | Champ texte | `mo.ui.text(value="", placeholder="Rechercher...", label="Filtre")` |
| `mo.ui.text_area` | Zone de texte multi-lignes | `mo.ui.text_area(value="", label="Notes")` |
| `mo.ui.checkbox` | Case a cocher | `mo.ui.checkbox(value=False, label="Inclure a-nouveaux")` |
| `mo.ui.switch` | Interrupteur on/off | `mo.ui.switch(value=True, label="Mode sombre")` |
| `mo.ui.radio` | Boutons radio | `mo.ui.radio(["HMA", "STIVMAT", "STA", "ETPA"], value="HMA", label="Structure")` |
| `mo.ui.dropdown` | Menu deroulant | `mo.ui.dropdown(options=["2024", "2025", "2026"], value="2026", label="Exercice")` |
| `mo.ui.multiselect` | Selection multiple | `mo.ui.multiselect(options=["Q1","Q2","Q3","Q4"], label="Trimestres")` |
| `mo.ui.date` | Selecteur de date | `mo.ui.date(value="2026-01-01", label="Date debut")` |
| `mo.ui.date_range` | Intervalle de dates | `mo.ui.date_range(start="2026-01-01", stop="2026-12-31", label="Periode")` |
| `mo.ui.button` | Bouton d'action | `mo.ui.button(label="Rafraichir", on_click=lambda v: v+1)` |
| `mo.ui.run_button` | Bouton "executer" | `mo.ui.run_button(label="Lancer le calcul")` |
| `mo.ui.file` | Upload de fichier | `mo.ui.file(filetypes=[".csv", ".xlsx"], label="Importer")` |
| `mo.ui.file_browser` | Navigateur de fichiers | `mo.ui.file_browser(initial_path="./data/")` |

#### Entrees avancees

| Element | Description | Exemple |
|---------|------------|---------|
| `mo.ui.code_editor` | Editeur de code | `mo.ui.code_editor(language="sql", value="SELECT *")` |
| `mo.ui.microphone` | Enregistrement audio | `mo.ui.microphone()` |
| `mo.ui.refresh` | Timer de rafraichissement | `mo.ui.refresh(default_interval="5s")` |
| `mo.ui.array` | Collection d'elements UI | `mo.ui.array([mo.ui.text() for _ in range(3)])` |
| `mo.ui.dictionary` | Dictionnaire d'elements UI | `mo.ui.dictionary({"nom": mo.ui.text(), "age": mo.ui.number(0, 100)})` |
| `mo.ui.batch` | Grouper des elements UI | Voir section 2.3 |
| `mo.ui.form` | Envelopper un element dans un formulaire | Voir section 2.3 |

#### Donnees et visualisation

| Element | Description | Exemple |
|---------|------------|---------|
| `mo.ui.table` | Tableau interactif | `mo.ui.table(df, selection="multi")` |
| `mo.ui.dataframe` | Transformations no-code | `mo.ui.dataframe(df, lazy=False)` |
| `mo.ui.data_editor` | Edition de donnees en place | `mo.ui.data_editor(df)` |
| `mo.ui.altair_chart` | Graphique Altair interactif | `mo.ui.altair_chart(chart)` |
| `mo.ui.plotly` | Graphique Plotly interactif | `mo.ui.plotly(fig)` |
| `mo.ui.chat` | Interface de chat IA | `mo.ui.chat(model)` |

### 2.2 `mo.ui.slider` -- Options avancees

```python
# Slider simple
prix = mo.ui.slider(0, 10000, value=5000, step=100, label="Prix max", full_width=True)

# Slider depuis une serie pandas/polars
year = mo.ui.slider.from_series(
    df["annee"], full_width=True, label="Annee", step=1
)

# Range slider
fourchette = mo.ui.range_slider(0, 100, value=[20, 80], label="Fourchette CA")
# fourchette.value retourne un tuple (20, 80)

# Range slider depuis une serie
population = mo.ui.range_slider.from_series(
    df["population"], full_width=True, label="Population"
)
```

### 2.3 `mo.ui.batch` et `mo.ui.form` -- Grouper les interactions

**`batch`** : regroupe plusieurs elements UI pour que leurs changements declenchent une seule mise a jour.

```python
# Batch via Markdown (syntaxe {element})
filters = mo.md("""
**Filtres**

Structure: {structure}
Exercice: {exercice}
Trimestre: {trimestre}
""").batch(
    structure=mo.ui.dropdown(["HMA", "STIVMAT", "STA", "ETPA"], value="HMA"),
    exercice=mo.ui.dropdown(["2024", "2025", "2026"], value="2026"),
    trimestre=mo.ui.dropdown(["T1", "T2", "T3", "T4", "Tous"], value="Tous"),
)
filters
# Acces : filters.value["structure"], filters.value["exercice"], etc.
```

**`form`** : enveloppe un element UI pour ne soumettre la valeur que sur clic "Submit".

```python
# Formulaire avec bouton Submit
search_form = mo.ui.text(placeholder="Numero de compte...").form(
    submit_button_label="Rechercher"
)
search_form
# search_form.value est None jusqu'au clic Submit
```

### 2.4 `mo.ui.table` -- Tableau interactif avance

```python
# Depuis une liste de dicts
table = mo.ui.table(
    [
        {"compte": "601100", "libelle": "Achats matieres premieres", "solde": -15420.50},
        {"compte": "701000", "libelle": "Ventes produits finis", "solde": 48300.00},
    ],
    selection="multi",  # "single", "multi", None
    pagination=True,
    page_size=20,
    label="Grand Livre",
)
table
# table.value retourne les lignes selectionnees

# Depuis un DataFrame
table_df = mo.ui.table(df, selection="multi", max_height=400)

# Options avancees
table_advanced = mo.ui.table(
    data,
    hover_template="{{compte}} - {{libelle}}",
    header_tooltip={
        "compte": "Numero de compte PCG",
        "solde": "Solde en euros",
    },
    pagination=False,
    max_height=300,  # Sticky header avec scroll
)
```

### 2.5 `mo.ui.dataframe` -- Transformations no-code

L'element `mo.ui.dataframe` fournit une interface graphique pour filtrer, trier, grouper, pivoter un DataFrame sans ecrire de code.

```python
transformer = mo.ui.dataframe(
    df,
    lazy=False,  # True pour les gros DataFrames (lazy evaluation)
    format_mapping={
        "montant": lambda v: f"{v:,.2f} EUR",
        "taux": "{:.1%}".format,
    },
)
transformer

# Dans une autre cellule, acceder au DataFrame transforme :
transformer.value
```

### 2.6 `mo.ui.data_editor` -- Edition en place

Permet a l'utilisateur de **modifier** les donnees directement dans un tableau editable.

```python
investments = mo.ui.data_editor(
    pd.DataFrame([
        {"Date": "2025-01-01", "Compte": "601100", "Montant": 500},
        {"Date": "2025-02-01", "Compte": "701000", "Montant": 800},
    ])
)
investments
# investments.value retourne le DataFrame modifie par l'utilisateur
```

### 2.7 `mo.stat` -- KPI / Statistique avec tendance

Affiche un indicateur chiffre avec caption de tendance (fleche haut/bas).

```python
ca_stat = mo.stat(
    label="Chiffre d'affaires",
    value="1 245 300 EUR",
    caption="+12%",
    direction="increase",  # "increase" ou "decrease"
    bordered=True,
)

resultat_stat = mo.stat(
    label="Resultat net",
    value="-45 200 EUR",
    caption="-8%",
    direction="decrease",
    bordered=True,
)

mo.hstack([ca_stat, resultat_stat], widths="equal", gap=1)
```

### 2.8 `mo.download` -- Bouton de telechargement

```python
# Telechargement CSV
csv_download = mo.download(
    data=df.to_csv().encode("utf-8"),
    filename="export_balance.csv",
    mimetype="text/csv",
    label="Telecharger CSV",
)

# Telechargement JSON
json_download = mo.download(
    data=json.dumps(data).encode("utf-8"),
    filename="rapport.json",
    mimetype="application/json",
    label="Telecharger JSON",
)

# Telechargement avec generation lazy (pour les gros fichiers)
lazy_download = mo.download(
    data=lambda: generate_big_report(),  # Callable, execute au clic
    filename="rapport_complet.xlsx",
    label="Generer et telecharger",
)

mo.hstack([csv_download, json_download, lazy_download])
```

---

## 3. Layout

### 3.1 `mo.hstack` et `mo.vstack` -- Empilement

```python
# Horizontal -- elements cote a cote
mo.hstack([element1, element2, element3])

# Horizontal avec options
mo.hstack(
    [stat1, stat2, stat3, stat4, stat5],
    widths="equal",    # "equal" ou liste de fractions [1, 2, 1]
    gap=1,             # Espacement en rem (defaut: 0.5)
    align="center",    # "start", "center", "end", "stretch"
    justify="center",  # "start", "center", "end", "space-between", "space-around"
    wrap=True,         # Retour a la ligne si depasse
)

# Vertical -- elements empiles
mo.vstack([
    mo.md("# Titre"),
    filters,
    chart,
    table,
])

# Vertical avec options
mo.vstack(
    [header, content, footer],
    gap=2,
    align="stretch",
)
```

### 3.2 `mo.ui.tabs` -- Onglets

```python
tab_sig = mo.vstack([sig_chart, sig_table])
tab_crd = mo.vstack([crd_chart, crd_table])
tab_bilan = mo.vstack([bilan_chart, bilan_table])

tabs = mo.ui.tabs({
    "SIG": tab_sig,
    "CRD": tab_crd,
    "Bilan": tab_bilan,
})
tabs
# tabs.value retourne le nom de l'onglet selectionne
```

### 3.3 `mo.accordion` -- Sections repliables

```python
mo.accordion({
    "Aide : Cellules SQL": mo.md("""
    Creez une cellule SQL via le bouton SQL en bas du notebook.
    Referencez les DataFrames Python comme des tables.
    """),
    "Aide : Filtres": mo.md("""
    Les filtres de la sidebar s'appliquent a tous les graphiques.
    """),
})
```

### 3.4 `mo.sidebar` -- Barre laterale

```python
mo.sidebar([
    mo.md("# Mon Dashboard"),
    mo.md("Filtrez les donnees ci-dessous."),
    year_slider,
    population_slider,
    structure_dropdown,
    mo.md("---"),
    mo.md("_Derniere MAJ: 2026-04-10_"),
])
```

La sidebar est **fixe** sur le cote gauche en mode app. Elle contient typiquement les filtres globaux du dashboard.

### 3.5 `mo.callout` -- Encadre d'alerte

```python
mo.callout("Donnees mises a jour avec succes.", kind="success")
mo.callout("Attention : exercice non cloture.", kind="warn")
mo.callout("Erreur de connexion a la base.", kind="danger")
mo.callout("Les soldes excluent les a-nouveaux.", kind="info")
mo.callout("Selectionnez des donnees dans le graphique.", kind="neutral")
```

Valeurs possibles pour `kind` : `"success"`, `"warn"`, `"danger"`, `"info"`, `"neutral"`.

### 3.6 `mo.md` -- Markdown riche

```python
# Markdown simple
mo.md("# Titre principal")

# Markdown avec variables Python (f-string)
mo.md(f"""
## Balance de {structure.value}
Exercice **{exercice.value}** -- {nb_comptes} comptes
""")

# Markdown avec admonitions (style callout)
mo.md(r"""
/// tip
Ce notebook est optimise pour le mode app. Appuyez sur Cmd/Ctrl+. pour basculer.
///
""")

# Markdown avec icones Lucide
mo.md(f"Cliquez sur {mo.icon('lucide:database')} pour creer une cellule SQL")

# Markdown avec LaTeX
mo.md(r"""
La formule du seuil de rentabilite :
$$SR = \frac{CF}{Taux\ MCV} = \frac{CF}{\frac{MCV}{CA}}$$
""")
```

### 3.7 Layout en colonnes (`width="columns"`)

```python
app = marimo.App(width="columns")

@app.cell(column=0)
def _():
    # Cette cellule apparait dans la colonne gauche
    ...

@app.cell(column=1)
def _():
    # Cette cellule apparait dans la colonne droite
    ...
```

### 3.8 Layout en grille (fichier JSON)

Pour un layout de dashboard avance avec positionnement libre des cellules :

```python
app = marimo.App(
    width="medium",
    layout_file="layouts/grid-dashboard.grid.json",
)
```

Le fichier `.grid.json` definit la position et la taille de chaque cellule sur une grille. Ce layout est genere visuellement via l'editeur Marimo (drag-and-drop en mode edit).

### 3.9 `width` -- Largeur de l'application

```python
app = marimo.App(width="medium")   # Defaut, centree avec marges
app = marimo.App(width="full")     # Pleine largeur (dashboards)
app = marimo.App(width="compact")  # Plus etroit
app = marimo.App(width="columns")  # Mode colonnes
```

---

## 4. Charts et visualisation

### 4.1 Altair (recommande)

Altair est la librairie de visualisation la mieux integree a Marimo. Les graphiques Altair peuvent etre **interactifs** via `mo.ui.altair_chart`.

```python
import altair as alt

# Graphique simple (non interactif)
chart = alt.Chart(df).mark_bar().encode(
    x="categorie:N",
    y="montant:Q",
    color="structure:N",
)
chart  # Affiche le graphique

# Graphique interactif (selections capturees)
interactive_chart = mo.ui.altair_chart(
    alt.Chart(df)
    .mark_circle(opacity=0.7)
    .encode(
        x="montant:Q",
        y="resultat:Q",
        color="structure:N",
        size=alt.Size("ca:Q", scale=alt.Scale(range=[100, 2000])),
        tooltip=["structure:N", "montant:Q", "resultat:Q", "ca:Q"],
    )
    .properties(height=400, width=600)
)
interactive_chart

# Dans une autre cellule, acceder aux points selectionnes :
interactive_chart.value  # DataFrame des points selectionnes
```

**Exemples de types de graphiques** :

```python
# Barres empilees
alt.Chart(df).mark_bar().encode(
    x="mois:N",
    y="montant:Q",
    color="rubrique:N",
)

# Ligne temporelle
alt.Chart(df).mark_line().encode(
    x="date:T",
    y="solde:Q",
    color="structure:N",
)

# Camembert
alt.Chart(df).mark_arc().encode(
    theta="montant:Q",
    color="categorie:N",
)

# Heatmap
alt.Chart(df).mark_rect().encode(
    x="mois:O",
    y="compte:N",
    color="solde:Q",
)

# Aires empilees
alt.Chart(df).mark_area(opacity=0.3, line=True).encode(
    x=alt.X("date:T", title="Date"),
    y=alt.Y("valeur:Q", title="Montant"),
)
```

### 4.2 Plotly

```python
import plotly.express as px
import plotly.graph_objs as go

# Graphique Plotly simple
fig = px.scatter(df, x="ca", y="resultat", color="structure")

# Envelopper dans mo.ui.plotly pour la selection interactive
plotly_chart = mo.ui.plotly(fig)
plotly_chart

# Acceder aux points selectionnes
plotly_chart.value
```

### 4.3 Matplotlib

Matplotlib est supporte nativement. Les figures sont affichees directement.

```python
import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.use("agg")  # Backend non-interactif (obligatoire dans Marimo)

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(df["categorie"], df["montant"])
ax.set_title("Charges par categorie")
ax.set_ylabel("Montant (EUR)")
plt.tight_layout()
fig  # Retourner la figure pour l'afficher
```

### 4.4 Polars `.plot` natif

Polars integre un raccourci `.plot` qui genere des graphiques Altair/Vega-Lite.

```python
# Ligne simple
df.plot.line("date", "montant")

# Barres
df.plot.bar("categorie", "total")
```

### 4.5 Combiner layout + charts

```python
@app.cell
def _(filtered_data, mo):
    # Ligne de KPI
    stats = mo.hstack([
        mo.stat(label="CA", value=f"{ca:,.0f} EUR", caption=f"{ca_pct:+.1%}", direction="increase", bordered=True),
        mo.stat(label="Resultat", value=f"{res:,.0f} EUR", caption=f"{res_pct:+.1%}", direction="decrease", bordered=True),
        mo.stat(label="MCV", value=f"{mcv:,.0f} EUR", bordered=True),
    ], widths="equal", gap=1)

    # Graphiques
    charts = mo.hstack([bar_chart, line_chart], widths="equal")

    # Assemblage vertical
    mo.vstack([stats, charts, table])
    return
```

---

## 5. Data -- SQL, DataFrames, Transforms

### 5.1 SQL natif avec `mo.sql()`

Marimo integre DuckDB pour executer du SQL directement. Les DataFrames Python sont accessibles comme des tables SQL.

**Installation** :
```bash
pip install "marimo[sql]"
# ou
uv add "marimo[sql]"
```

**Utilisation** :

```python
import marimo as mo
import polars as pl

# Charger des donnees
ventes = pl.read_csv("ventes.csv")

# Requete SQL sur le DataFrame Python (reference par son nom de variable)
result_df = mo.sql(f"""
    SELECT 
        structure,
        SUM(montant) as total_ca,
        COUNT(*) as nb_ecritures
    FROM ventes
    WHERE annee = 2026
    GROUP BY structure
    ORDER BY total_ca DESC
""")

result_df  # Retourne un Polars DataFrame (ou Pandas si Polars n'est pas installe)
```

**Points cles** :
- `mo.sql()` retourne un **Polars DataFrame** (si polars installe) ou Pandas
- Les f-strings permettent d'interpoler des variables Python dans les requetes
- Le resultat est assigne a une variable et participe au DAG reactif
- Le parseur de Marimo analyse statiquement le SQL pour le graphe de dependances

### 5.2 Connexion PostgreSQL via DuckDB

DuckDB peut se connecter a PostgreSQL via son extension `postgres`.

```python
@app.cell
def _():
    import os
    import duckdb
    
    PASSWORD = os.getenv("PGPASSWORD", "mysecretpassword")
    return (PASSWORD,)

@app.cell
def _(PASSWORD):
    _df = mo.sql(f"""
        INSTALL postgres;
        LOAD postgres;
        
        ATTACH 'dbname=postgres user=postgres password={PASSWORD} host=localhost port=5432' 
        AS pg_db (TYPE POSTGRES);
    """)
    return

@app.cell
def _():
    balance_df = mo.sql(f"""
        SELECT * FROM pg_db.public.balance_generale
        WHERE annee = 2026
        LIMIT 100
    """)
    balance_df
    return (balance_df,)
```

### 5.3 Connexion directe PostgreSQL (psycopg2/pg8000)

Pour une connexion directe sans passer par DuckDB :

```python
@app.cell
def _():
    import pg8000
    import polars as pl
    import os

    conn = pg8000.connect(
        host="localhost",
        port=5432,
        database="postgres",
        user="postgres",
        password=os.getenv("PGPASSWORD"),
    )
    
    df = pl.read_database(
        "SELECT * FROM v_sig WHERE entite_code = 'HMA' AND annee = 2026",
        connection=conn,
    )
    conn.close()
    return (df,)
```

### 5.4 Connexion SQLite

```python
_df = mo.sql(f"""
    ATTACH 'path/to/database.sqlite' AS sqlite_db (TYPE SQLITE);
""")

result = mo.sql(f"""
    SELECT * FROM sqlite_db.table_name LIMIT 10;
""")
```

### 5.5 DuckDB -- Requetes sur fichiers

DuckDB peut lire directement des fichiers CSV, Parquet, JSON sans chargement prealable.

```python
# Lire un CSV
df = mo.sql(f"SELECT * FROM 'data/ventes.csv' WHERE montant > 1000")

# Lire un Parquet
df = mo.sql(f"SELECT * FROM 'data/balance.parquet'")

# Lire plusieurs fichiers avec glob
df = mo.sql(f"SELECT * FROM 'data/*.csv'")

# Lire un JSON
df = mo.sql(f"SELECT * FROM 'data/config.json'")
```

### 5.6 `mo.ui.dataframe` -- Transformations interactives

Interface graphique no-code pour manipuler un DataFrame :

```python
transformer = mo.ui.dataframe(df)
transformer
# L'utilisateur peut filtrer, trier, grouper, renommer via l'UI
# transformer.value retourne le DataFrame transforme
```

### 5.7 Parametrage SQL avec variables UI

```python
@app.cell
def _(mo):
    structure = mo.ui.dropdown(["HMA", "STIVMAT", "STA", "ETPA"], value="HMA")
    annee = mo.ui.slider(2024, 2026, value=2026)
    mo.hstack([structure, annee])
    return structure, annee

@app.cell
def _(structure, annee):
    # La requete se re-execute quand les filtres changent
    sig_df = mo.sql(f"""
        SELECT *
        FROM v_sig
        WHERE entite_code = '{structure.value}'
          AND annee = {annee.value}
        ORDER BY sig_ordre
    """)
    sig_df
    return (sig_df,)
```

### 5.8 Export automatique

```python
# Auto-download en HTML
app = marimo.App(auto_download=["html"])

# Bouton de telechargement explicite
download_btn = mo.download(
    data=df.to_csv().encode("utf-8"),
    filename="export.csv",
    mimetype="text/csv",
    label="Exporter en CSV",
)
```

---

## 6. Deployment

### 6.1 Dockerfile de production

```dockerfile
# syntax=docker/dockerfile:1.4
FROM python:3.11-slim

# Installer uv pour la gestion rapide des packages
COPY --from=ghcr.io/astral-sh/uv:0.4.20 /uv /bin/uv
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

# Copier et installer les dependances
COPY --link requirements.txt .
RUN uv pip install -r requirements.txt

# Copier les fichiers de l'application
COPY --link app.py .
COPY --link layouts/ layouts/
COPY --link custom.css .

EXPOSE 8080

# Creer un utilisateur non-root
RUN useradd -m app_user
USER app_user

# Mode run = lecture seule, production
CMD ["marimo", "run", "app.py", "--host", "0.0.0.0", "-p", "8080"]
```

### 6.2 `requirements.txt` typique pour un dashboard comptable

```
marimo
polars
pandas
altair
plotly
pg8000
duckdb
psycopg2-binary
python-dotenv
```

### 6.3 Inline script metadata (PEP 723)

Marimo supporte les metadonnees de script en ligne pour specifier les dependances :

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "altair==5.4.1",
#     "marimo",
#     "polars==1.18.0",
#     "pg8000==1.31.0",
# ]
# ///

import marimo
app = marimo.App(width="full")
...
```

### 6.4 Options de la CLI `marimo run`

```bash
# Production basique
marimo run app.py --host 0.0.0.0 -p 8080

# Avec auto-reload en developpement
marimo edit app.py --host 0.0.0.0 -p 8080

# Options utiles
marimo run app.py \
    --host 0.0.0.0 \
    -p 8080 \
    --headless \           # Pas d'ouverture de navigateur
    --include-code         # Montrer le code source en mode run
```

### 6.5 Docker Compose pour le stack HMA

```yaml
version: "3.8"
services:
  marimo-dashboard:
    build: ./marimo-dashboard
    ports:
      - "8080:8080"
    environment:
      - PGPASSWORD=${HMA_DB_PASSWORD}
      - PGHOST=hma-db
      - PGPORT=5432
      - PGDATABASE=postgres
      - PGUSER=postgres
    networks:
      - coolify
    restart: unless-stopped

networks:
  coolify:
    external: true
```

### 6.6 Configuration via `pyproject.toml`

```toml
[tool.marimo]
# Largeur par defaut
width = "full"

[tool.marimo.display]
# CSS personnalise
custom_css = ["custom.css"]

[tool.marimo.server]
# Port par defaut
port = 8080
host = "0.0.0.0"
```

---

## 7. Theming et CSS

### 7.1 CSS personnalise -- Methodes

**Methode 1 : via `marimo.App()`**

```python
app = marimo.App(css_file="custom.css")
```

**Methode 2 : via `pyproject.toml`**

```toml
[tool.marimo.display]
custom_css = ["custom.css"]
```

### 7.2 Selecteurs CSS utiles

```css
/* Cibler une cellule par son nom */
[data-cell-name='kpi_row'] {
    background-color: #f8f9fa;
    border-radius: 8px;
    padding: 16px;
}

/* Cibler la sortie d'une cellule */
[data-cell-name='header'] [data-cell-role='output'] {
    text-align: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    border-radius: 12px;
}

/* Theme sombre adaptatif avec light-dark() */
[data-cell-name='sidebar'] {
    background-color: light-dark(#f0f0f0, #1a1a2e);
}

/* Personnaliser les statistiques (mo.stat) */
.marimo-stat {
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Personnaliser les tableaux */
.marimo-table {
    font-size: 13px;
}

.marimo-table th {
    background-color: #2c3e50;
    color: white;
}

/* Largeur personnalisee */
:root {
    --marimo-content-width: 1400px;
}
```

### 7.3 Theme sombre / clair

Marimo supporte nativement le mode sombre. Utiliser `light-dark()` en CSS pour les couleurs adaptatives :

```css
body {
    background-color: light-dark(#ffffff, #0d1117);
    color: light-dark(#1f2328, #e6edf3);
}
```

### 7.4 Icones Lucide

Marimo integre les icones Lucide :

```python
mo.icon("lucide:database")
mo.icon("lucide:bar-chart-2")
mo.icon("lucide:euro")
mo.icon("lucide:trending-up")
mo.icon("lucide:trending-down")
mo.icon("lucide:alert-triangle")
mo.icon("lucide:check-circle")
```

---

## 8. Templates et patterns (gallery)

### 8.1 Pattern : Dashboard avec sidebar de filtres

Source : `marimo-team/marimo/examples/layouts/sidebar.py`

```python
import marimo

app = marimo.App(width="full")

with app.setup:
    import marimo as mo
    import altair as alt

@app.cell
def _(year, population, structure):
    # Filtrer les donnees
    filtered = df[
        (df["annee"] == year.value)
        & (df["ca"] > population.value[0])
        & (df["ca"] < population.value[1])
    ]
    if structure.value != "Toutes":
        filtered = filtered[filtered["entite"] == structure.value]
    return (filtered,)

@app.cell
def _(filtered, mo):
    chart = mo.ui.altair_chart(
        alt.Chart(filtered).mark_circle(opacity=0.7).encode(
            x="ca:Q",
            y="resultat:Q",
            color="entite:N",
            tooltip=["entite:N", "ca:Q", "resultat:Q"],
        ).properties(height=400)
    )
    chart
    return (chart,)

@app.cell
def _(chart):
    chart.value if not chart.value.empty else None
    return

@app.cell
def _(mo, year, population, structure):
    mo.sidebar([
        mo.md("# Dashboard HMA"),
        mo.md("Explorez les donnees financieres"),
        year,
        population,
        structure,
        mo.md("---"),
        mo.md("_Source: PostgreSQL HMA_"),
    ])
    return
```

### 8.2 Pattern : Dashboard KPI avec stats et tendances

Source : `marimo-team/gallery-examples/notebooks/dashboard/movies.py`

```python
@app.cell
def _(filtered, previous, mo):
    # Calculer les variations
    ca_current = filtered["ca"].sum()
    ca_previous = previous["ca"].sum()
    ca_rate = (ca_current - ca_previous) / ca_previous if ca_previous else 0

    ca_stat = mo.stat(
        label="Chiffre d'affaires",
        bordered=True,
        caption=f"{ca_rate:.0%}",
        direction="increase" if ca_rate > 0 else "decrease",
        value=f"{ca_current:,.0f} EUR",
    )

    res_current = filtered["resultat"].sum()
    res_previous = previous["resultat"].sum()
    res_rate = (res_current - res_previous) / res_previous if res_previous else 0

    resultat_stat = mo.stat(
        label="Resultat net",
        bordered=True,
        caption=f"{res_rate:.0%}",
        direction="increase" if res_rate > 0 else "decrease",
        value=f"{res_current:,.0f} EUR",
    )

    mo.hstack([ca_stat, resultat_stat], widths="equal", gap=1)
    return
```

### 8.3 Pattern : Pipeline de donnees avec `@app.function` et `.pipe()`

Source : `marimo-team/gallery-examples/notebooks/dashboard/portfolio.py`

```python
@app.function(hide_code=True)
def set_types(dataf):
    return dataf.with_columns([
        pl.col("date").cast(pl.Date),
        pl.col("montant").cast(pl.Float64),
    ])

@app.function(hide_code=True)
def enrich_data(dataf):
    return dataf.with_columns(
        annee=pl.col("date").dt.year(),
        mois=pl.col("date").dt.month(),
        trimestre=pl.col("date").dt.quarter(),
    )

@app.function(hide_code=True)
def aggregate(dataf):
    return dataf.group_by(["annee", "trimestre", "entite"]).agg([
        pl.sum("montant").alias("total"),
        pl.count("id").alias("nb_ecritures"),
    ])

# Utilisation chainee
@app.cell
def _(raw_data):
    result = (
        raw_data
        .pipe(set_types)
        .pipe(enrich_data)
        .pipe(aggregate)
    )
    return (result,)
```

### 8.4 Pattern : Boutons d'action avec `mo.state`

Source : `marimo-team/gallery-examples/notebooks/dashboard/movies.py`

```python
@app.cell
def _():
    get_start, set_start = mo.state(pd.to_datetime("2024-01-01"))
    get_end, set_end = mo.state(pd.to_datetime("2026-12-31"))
    return get_start, set_start, get_end, set_end

@app.cell
def _(set_start, set_end):
    def year_button(year):
        s = pd.to_datetime(f"{year}-01-01")
        e = pd.to_datetime(f"{year}-12-31")
        def handle(v):
            set_start(s)
            set_end(e)
            return 1
        return mo.ui.button(label=str(year), on_click=handle)

    btn_2024 = year_button(2024)
    btn_2025 = year_button(2025)
    btn_2026 = year_button(2026)

    mo.hstack([mo.md("Exercice rapide:"), btn_2024, btn_2025, btn_2026])
    return btn_2024, btn_2025, btn_2026
```

### 8.5 Pattern : Selection dans un graphique -> tableau detail

Source : `marimo-team/gallery-examples/notebooks/dashboard/movies.py`

```python
@app.cell
def _(filtered_data, mo):
    _chart = alt.Chart(filtered_data).mark_circle().encode(
        x="ca:Q",
        y="resultat:Q",
        color="categorie:N",
        tooltip=["libelle", "ca:Q", "resultat:Q"],
    )
    chart = mo.ui.altair_chart(_chart)
    chart
    return (chart,)

@app.cell
def _(chart, mo):
    # Affiche un message si rien n'est selectionne
    mo.stop(len(chart.value) == 0, mo.callout("Selectionnez des points pour voir le detail."))
    
    # Sinon affiche le tableau des points selectionnes
    mo.ui.table(chart.value, selection=None)
    return
```

### 8.6 Pattern : Cache partiel du pipeline

Source : `marimo-team/gallery-examples/notebooks/dashboard/world-of-warcraft.py`

```python
# La partie "lourde" du pipeline est calculee une fois
@app.cell
def _(df):
    cached = (
        df
        .pipe(set_types)
        .pipe(clean_data)
        .pipe(sessionize, threshold=30 * 60 * 1000)
        .pipe(add_features)
    )
    return (cached,)

# Seule cette partie se re-execute quand le slider change
@app.cell
def _(cached, threshold):
    result = cached.pipe(remove_bots, max_session_hours=threshold.value)
    return (result,)
```

### 8.7 Pattern : Dashboard comptable HMA (template)

Template complet adapte au contexte HMA :

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "altair==5.4.1",
#     "polars==1.18.0",
#     "pg8000==1.31.0",
# ]
# ///

import marimo

app = marimo.App(width="full", css_file="custom.css")

with app.setup:
    import marimo as mo
    import altair as alt
    import polars as pl
    import pg8000
    import os

# --- Connexion DB ---
@app.cell(hide_code=True)
def _():
    conn = pg8000.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "postgres"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
    )
    return (conn,)

# --- Chargement des donnees ---
@app.cell(hide_code=True)
def _(conn):
    sig_data = pl.read_database(
        "SELECT * FROM v_sig WHERE annee = 2026",
        connection=conn,
    )
    crd_data = pl.read_database(
        "SELECT * FROM v_crd WHERE annee = 2026",
        connection=conn,
    )
    return sig_data, crd_data

# --- Filtres ---
@app.cell(hide_code=True)
def _(sig_data, mo):
    structure = mo.ui.dropdown(
        options=["Toutes"] + sig_data["entite_code"].unique().to_list(),
        value="Toutes",
        label="Structure",
    )
    return (structure,)

# --- Filtrage reactif ---
@app.cell(hide_code=True)
def _(sig_data, structure):
    filtered = sig_data
    if structure.value != "Toutes":
        filtered = sig_data.filter(pl.col("entite_code") == structure.value)
    return (filtered,)

# --- KPI ---
@app.cell(hide_code=True)
def _(filtered, mo):
    ca = filtered.filter(pl.col("sig_ordre") == 1)["solde"].sum()
    va = filtered.filter(pl.col("sig_ordre") == 3)["solde"].sum()
    ebe = filtered.filter(pl.col("sig_ordre") == 5)["solde"].sum()
    rn = filtered.filter(pl.col("sig_ordre") == 9)["solde"].sum()

    mo.hstack([
        mo.stat(label="CA", value=f"{ca:,.0f} EUR", bordered=True),
        mo.stat(label="VA", value=f"{va:,.0f} EUR", bordered=True),
        mo.stat(label="EBE", value=f"{ebe:,.0f} EUR", bordered=True),
        mo.stat(label="Resultat net", value=f"{rn:,.0f} EUR", bordered=True),
    ], widths="equal", gap=1)
    return

# --- Graphiques ---
@app.cell(hide_code=True)
def _(filtered):
    sig_chart = alt.Chart(filtered).mark_bar().encode(
        x=alt.X("sig_libelle:N", sort="-y", title="Solde intermediaire"),
        y=alt.Y("solde:Q", title="Montant (EUR)"),
        color=alt.condition(
            alt.datum.solde > 0,
            alt.value("#2ecc71"),
            alt.value("#e74c3c"),
        ),
        tooltip=["sig_libelle:N", "solde:Q"],
    ).properties(height=400, title="Soldes Intermediaires de Gestion")
    sig_chart
    return

# --- Tableau detail ---
@app.cell(hide_code=True)
def _(filtered, mo):
    mo.ui.table(filtered, selection=None)
    return

# --- Sidebar ---
@app.cell(hide_code=True)
def _(structure, mo):
    mo.sidebar([
        mo.md("# Dashboard SIG"),
        mo.md("Soldes Intermediaires de Gestion"),
        mo.md("---"),
        structure,
        mo.md("---"),
        mo.md("_Source: PostgreSQL HMA_"),
        mo.md("_Vue: v_sig_"),
    ])
    return

# --- Onglets ---
@app.cell(hide_code=True)
def _(sig_chart, sig_table, crd_chart, mo):
    tabs = mo.ui.tabs({
        "SIG": mo.vstack([sig_chart, sig_table]),
        "CRD": crd_chart,
    })
    tabs
    return

if __name__ == "__main__":
    app.run()
```

---

## 9. Best practices et pieges courants

### 9.1 La regle du `.value` (CRITIQUE)

**Piege n.1** : acceder a `.value` dans la meme cellule que la creation de l'element UI.

```python
# MAUVAIS -- boucle infinie / valeur jamais a jour
@app.cell
def _(mo):
    slider = mo.ui.slider(0, 100)
    result = slider.value * 2  # NE PAS FAIRE CA
    return

# BON -- separer creation et lecture
@app.cell
def _(mo):
    slider = mo.ui.slider(0, 100)
    slider  # Afficher l'element
    return (slider,)

@app.cell
def _(slider):
    result = slider.value * 2  # OK : cellule differente
    return (result,)
```

**Raison** : lire `.value` dans la meme cellule que la creation creerait une dependance circulaire. La cellule se re-executerait a chaque changement, recreant l'element et perdant l'etat.

### 9.2 Variables privees (underscore)

Les variables prefixees par `_` ne sont pas exportees et ne creent pas de dependances.

```python
@app.cell
def _(df):
    _temp = df.filter(pl.col("montant") > 0)  # Variable privee
    _chart = alt.Chart(_temp).mark_bar()...     # Variable privee
    chart = mo.ui.altair_chart(_chart)           # Variable exportee
    chart
    return (chart,)
```

### 9.3 Une seule definition par variable

Chaque variable ne peut etre definie que dans **une seule cellule**. Si deux cellules definissent `df`, Marimo signale une erreur.

```python
# MAUVAIS
@app.cell
def _():
    df = load_data_a()
    return (df,)

@app.cell
def _():
    df = load_data_b()  # ERREUR : df deja defini
    return (df,)

# BON
@app.cell
def _():
    df_a = load_data_a()
    return (df_a,)

@app.cell
def _():
    df_b = load_data_b()
    return (df_b,)
```

### 9.4 Gardes avec `mo.stop()`

Toujours proteger les cellules qui dependent de selections optionnelles.

```python
@app.cell
def _(chart, mo):
    mo.stop(
        chart.value is None or len(chart.value) == 0,
        mo.callout("Selectionnez des points dans le graphique ci-dessus.", kind="info")
    )
    # Code qui utilise chart.value en toute securite
    mo.ui.table(chart.value)
    return
```

### 9.5 Performances -- Separation cache/reactif

Separer les calculs lourds (qui ne changent pas) des calculs legers (qui dependent des filtres UI).

```python
# Calcul lourd -- execute une fois
@app.cell
def _():
    raw = pl.read_database("SELECT * FROM grand_livre WHERE annee = 2026", conn)
    enriched = raw.pipe(set_types).pipe(enrich_data)
    return (enriched,)

# Calcul leger -- re-execute quand le filtre change
@app.cell
def _(enriched, structure):
    filtered = enriched.filter(pl.col("entite_code") == structure.value)
    return (filtered,)
```

### 9.6 Ne pas utiliser `print()` pour l'affichage

Dans Marimo, l'affichage se fait en **retournant** une valeur a la fin de la cellule (derniere expression). `print()` envoie vers stdout, pas vers l'UI.

```python
# MAUVAIS
@app.cell
def _(df):
    print(df.head())  # Invisible dans l'UI

# BON
@app.cell
def _(df):
    df.head()  # Derniere expression = affichee
    return
```

### 9.7 Markdown dynamique (f-strings)

```python
@app.cell
def _(ca, structure, mo):
    mo.md(f"""
    ## Resultats {structure.value}
    
    Le chiffre d'affaires s'eleve a **{ca:,.0f} EUR**.
    """)
    return
```

### 9.8 Gestion des secrets

Ne jamais hardcoder de secrets. Utiliser les variables d'environnement.

```python
@app.cell(hide_code=True)
def _():
    import os
    password = os.getenv("PGPASSWORD")
    if not password:
        raise ValueError("PGPASSWORD non defini")
    return (password,)
```

### 9.9 Structure recommandee d'un notebook Marimo

```
1. app.setup     -> imports globaux
2. Connexion DB  -> hide_code=True
3. Chargement    -> hide_code=True
4. Filtres UI    -> hide_code=True
5. Filtrage      -> hide_code=True
6. KPI/Stats     -> hide_code=True
7. Graphiques    -> hide_code=True
8. Tableaux      -> hide_code=True
9. Sidebar       -> hide_code=True
10. Tabs/Layout  -> hide_code=True
```

### 9.10 Polars vs Pandas

Marimo fonctionne avec les deux, mais **Polars est prefere** :
- `mo.sql()` retourne Polars si installe
- Polars est plus rapide pour les gros volumes
- API plus expressive (`.pipe()`, `.with_columns()`, `.filter()`)
- Meilleure gestion des types (dates, nulls)

### 9.11 Erreurs courantes et solutions

| Erreur | Cause | Solution |
|--------|-------|----------|
| `CycleError` | Dependance circulaire entre cellules | Reorganiser les cellules, utiliser `_` pour les variables privees |
| `MultipleDefinitionError` | Variable definie dans 2+ cellules | Renommer avec suffixe (`df_sig`, `df_crd`) |
| Graphique vide | `.value` lu dans la meme cellule | Separer creation et lecture dans 2 cellules |
| SQL ne trouve pas la table | DataFrame pas retourne par la cellule | Ajouter `return (df,)` |
| CSS ne s'applique pas | Fichier CSS non reference | Ajouter `css_file="custom.css"` dans `App()` |
| Import manquant | Module pas dans requirements | Ajouter dans le bloc `# /// script` ou `requirements.txt` |

---

## Annexe : Fichiers d'exemples de reference

### Exemples officiels (marimo-team/marimo)

| Dossier | Fichiers |
|---------|----------|
| `examples/ui/` | `slider.py`, `dropdown.py`, `table.py`, `table_advanced.py`, `dataframe.py`, `form.py`, `batch.py`, `batch_and_form.py`, `tabs.py`, `tabs_advanced.py`, `checkbox.py`, `radio.py`, `button.py`, `date.py`, `date_range.py`, `number.py`, `text.py`, `text_area.py`, `multiselect.py`, `switch.py`, `download.py`, `data_editor.py`, `data_explorer.py`, `file.py`, `file_browser.py`, `code_editor.py`, `microphone.py`, `chat.py`, `refresh.py`, `run_button.py`, `range_slider.py`, `array_element.py`, `arrays_and_dicts.py`, `dictionary.py`, `matrix.py`, `image_comparison_demo.py`, `layout.py` |
| `examples/layouts/` | `columns.py`, `grid-dashboard.py`, `sidebar.py`, `slides.py` |
| `examples/sql/` | `connect_to_postgres.py`, `connect_to_sqlite.py`, `connect_to_persistent_db.py`, `connect_to_motherduck.py`, `duckdb_example.py`, `querying_dataframes.py`, `parametrizing_sql_queries.py`, `read_csv.py`, `read_json.py`, `read_parquet.py`, `histograms.py` |
| `examples/frameworks/` | Integrations tierces |
| `examples/outputs/` | Sorties non-UI |
| `examples/third_party/` | Librairies externes |

### Gallery (marimo-team/gallery-examples)

| Dossier | Fichiers |
|---------|----------|
| `notebooks/dashboard/` | `movies.py` (KPI + stats + selection), `portfolio.py` (app.function + pipe), `world-of-warcraft.py` (cache + pipe + slider), `lego/` |
| `notebooks/sql/` | Exemples SQL |
| `notebooks/analysis/` | Analyses de donnees |
| `notebooks/geo/` | Cartes et geodonnees |

---

> Document genere pour servir de reference exhaustive a la creation de skills Claude Code pour le stack HMA.
> Sources : documentation officielle marimo.io, depot GitHub marimo-team/marimo, gallery marimo-team/gallery-examples.
