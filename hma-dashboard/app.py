"""Dashboard CRD sur mesure — Application Dash principale."""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

from data import get_entites, get_annees

# ── Application Dash ─────────────────────────────────────────────

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="CRD — Dashboard HMA",
    suppress_callback_exceptions=True,
)
server = app.server  # pour gunicorn

# ── Donnees de reference pour les filtres ────────────────────────

try:
    df_entites = get_entites()
    entite_options = [
        {"label": row["nom"], "value": str(row["id"])}
        for _, row in df_entites.iterrows()
    ]
    annee_options = [{"label": str(a), "value": int(a)} for a in get_annees()]
except Exception:
    entite_options = [
        {"label": "HMA", "value": "hma"},
        {"label": "STIVMAT", "value": "stivmat"},
        {"label": "STA", "value": "sta"},
        {"label": "ETPA", "value": "etpa"},
    ]
    annee_options = [
        {"label": "2026", "value": 2026},
        {"label": "2025", "value": 2025},
    ]

trimestre_options = [
    {"label": "Annee complete", "value": 0},
    {"label": "T1", "value": 1},
    {"label": "T2", "value": 2},
    {"label": "T3", "value": 3},
    {"label": "T4", "value": 4},
]

reference_options = [
    {"label": "Trimestre precedent", "value": "trim_prec"},
    {"label": "Exercice N-1", "value": "n-1"},
    {"label": "Exercice N-2", "value": "n-2"},
]

# ── Sidebar filtres ──────────────────────────────────────────────

sidebar = dbc.Col(
    [
        html.H4("CRD Dashboard", className="mb-4"),
        html.Hr(style={"borderColor": "#4a5568"}),

        dbc.Label("Structure"),
        dcc.Dropdown(
            id="filtre-structure",
            options=entite_options,
            value=entite_options[0]["value"] if entite_options else None,
            clearable=False,
            className="mb-3",
        ),

        dbc.Label("Exercice"),
        dcc.Dropdown(
            id="filtre-annee",
            options=annee_options,
            value=annee_options[0]["value"] if annee_options else 2026,
            clearable=False,
            className="mb-3",
        ),

        dbc.Label("Trimestre"),
        dcc.Dropdown(
            id="filtre-trimestre",
            options=trimestre_options,
            value=0,
            clearable=False,
            className="mb-3",
        ),

        html.Hr(style={"borderColor": "#4a5568"}),

        dbc.Label("Evolution vs."),
        dcc.Dropdown(
            id="filtre-reference",
            options=reference_options,
            value="n-1",
            clearable=False,
            className="mb-3",
        ),

        html.Hr(style={"borderColor": "#4a5568"}),

        dbc.Checklist(
            id="mode-comparaison",
            options=[{"label": " Mode comparaison", "value": "on"}],
            value=[],
            className="mt-2",
            style={"color": "white"},
        ),
    ],
    width=2,
    className="sidebar",
)

# ── Contenu principal ────────────────────────────────────────────

content = dbc.Col(
    [
        # Titre dynamique
        html.H3(id="titre-dashboard", className="mb-3 mt-3"),

        # KPI Cards
        html.Div(id="kpi-cards-container", className="mb-4"),

        # Tableau CRD + drilldown
        html.Div(id="crd-table-container", className="mb-4"),

        # Graphiques
        dbc.Row(
            [
                dbc.Col(
                    html.Div(id="chart-line-container", className="chart-card"),
                    lg=8,
                ),
                dbc.Col(
                    html.Div(id="chart-donut-container", className="chart-card"),
                    lg=4,
                ),
            ],
            className="mb-4",
        ),

        dbc.Row(
            [
                dbc.Col(
                    html.Div(id="chart-bar-container", className="chart-card"),
                    lg=12,
                ),
            ],
            className="mb-4",
        ),

        # Comparaison (masque par defaut)
        html.Div(id="comparison-container", style={"display": "none"}),

        # Store pour l'etat drilldown
        dcc.Store(id="drilldown-state", data={}),
    ],
    width=10,
    style={"padding": "0 1.5rem"},
)

# ── Layout principal ─────────────────────────────────────────────

app.layout = dbc.Container(
    dbc.Row([sidebar, content]),
    fluid=True,
    style={"padding": 0},
)

# ── Import des callbacks ─────────────────────────────────────────

import callbacks  # noqa: F401, E402

# ── Point d'entree ───────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
