"""Callbacks Dash — logique reactive (filtres → composants)."""

import dash
from dash import html, callback, Output, Input, State, no_update, dcc, ALL, ctx
import dash_bootstrap_components as dbc
import json

from data import get_crd, get_crd_reference, get_crd_drilldown, get_ytd_mensuel, get_crd_multi
from components.kpi_cards import create_kpi_row
from components.crd_table import create_crd_table, create_seuil_section, CRD_LINES
from components.charts import (
    create_line_chart, create_donut_chart,
    create_bar_chart, create_comparison_chart,
)


# ── Callback principal : filtres → tout ──────────────────────────

@callback(
    Output("titre-dashboard", "children"),
    Output("kpi-cards-container", "children"),
    Output("crd-table-container", "children"),
    Output("chart-line-container", "children"),
    Output("chart-donut-container", "children"),
    Output("chart-bar-container", "children"),
    Output("comparison-container", "children"),
    Output("comparison-container", "style"),
    Input("filtre-structure", "value"),
    Input("filtre-annee", "value"),
    Input("filtre-trimestre", "value"),
    Input("filtre-reference", "value"),
    Input("mode-comparaison", "value"),
    State("drilldown-state", "data"),
)
def update_dashboard(entite_id, annee, trimestre, ref_type, mode_comp, drilldown_state):
    """Met a jour tous les composants quand un filtre change."""
    if not entite_id or not annee:
        return ("", html.Div(), html.Div(), html.Div(), html.Div(), html.Div(),
                html.Div(), {"display": "none"})

    trimestre_val = trimestre if trimestre and trimestre > 0 else None

    # Mode comparaison
    if mode_comp and "on" in mode_comp:
        return _render_comparison(annee, trimestre_val)

    # ── Donnees ──
    try:
        df_crd = get_crd(entite_id, annee, trimestre_val)
        df_ref = get_crd_reference(entite_id, annee, trimestre_val, ref_type)
        df_ytd = get_ytd_mensuel(entite_id, annee)
        df_drill_cats = get_crd_drilldown(entite_id, annee, trimestre_val)
    except Exception as e:
        error = html.Div(f"Erreur de chargement : {e}", className="text-danger p-3")
        return ("Erreur", error, html.Div(), html.Div(), html.Div(), html.Div(),
                html.Div(), {"display": "none"})

    # ── Titre ──
    entite_nom = df_crd.iloc[0]["entite_nom"] if not df_crd.empty else "—"
    trim_label = f" — T{trimestre_val}" if trimestre_val else ""
    titre = f"{entite_nom} — Exercice {annee}{trim_label}"

    # ── KPI Cards ──
    kpi = create_kpi_row(df_crd, df_ref)

    # ── Tableau CRD + seuil ──
    crd_table = html.Div([
        create_crd_table(df_crd),
        create_seuil_section(df_crd),
    ])

    # ── Graphiques ──
    chart_line = dcc.Graph(
        figure=create_line_chart(df_ytd),
        config={"displayModeBar": False},
    )
    chart_donut = dcc.Graph(
        figure=create_donut_chart(df_crd),
        config={"displayModeBar": False},
    )
    chart_bar = dcc.Graph(
        figure=create_bar_chart(df_drill_cats, title="Detail par categorie CRD"),
        config={"displayModeBar": False},
    )

    return (titre, kpi, crd_table, chart_line, chart_donut, chart_bar,
            html.Div(), {"display": "none"})


def _render_comparison(annee, trimestre_val):
    """Rendu du mode comparaison multi-structures."""
    try:
        df_multi = get_crd_multi([1, 2, 3, 4], annee, trimestre_val)
    except Exception as e:
        error = html.Div(f"Erreur comparaison : {e}", className="text-danger p-3")
        return ("Comparaison", html.Div(), html.Div(), html.Div(), html.Div(), html.Div(),
                error, {"display": "block"})

    trim_label = f" — T{trimestre_val}" if trimestre_val else ""
    titre = f"Comparaison — Exercice {annee}{trim_label}"

    comp_chart = dcc.Graph(
        figure=create_comparison_chart(df_multi),
        config={"displayModeBar": False},
    )

    return (titre, html.Div(), html.Div(), html.Div(), html.Div(), html.Div(),
            comp_chart, {"display": "block"})


# ── Callback drilldown (clic sur ligne CRD) ──────────────────────

@callback(
    Output("drilldown-state", "data"),
    Output("crd-table-container", "children", allow_duplicate=True),
    Input({"type": "crd-row", "index": ALL}, "n_clicks"),
    State("filtre-structure", "value"),
    State("filtre-annee", "value"),
    State("filtre-trimestre", "value"),
    State("drilldown-state", "data"),
    prevent_initial_call=True,
)
def handle_drilldown(n_clicks_list, entite_id, annee, trimestre, drilldown_state):
    """Gere le clic sur une ligne CRD pour le drilldown."""
    if not ctx.triggered or not any(n for n in n_clicks_list if n):
        return no_update, no_update

    # Identifier la ligne cliquee
    triggered_id = ctx.triggered_id
    clicked_key = triggered_id["index"]

    # Trouver la categorie CRD correspondante
    categorie = None
    for line in CRD_LINES:
        if line["key"] == clicked_key and "categorie" in line:
            categorie = line["categorie"]
            break

    if not categorie:
        return no_update, no_update

    trimestre_val = trimestre if trimestre and trimestre > 0 else None

    # Toggle drilldown
    if drilldown_state is None:
        drilldown_state = {}

    if categorie in drilldown_state:
        del drilldown_state[categorie]
    else:
        df_rubriques = get_crd_drilldown(entite_id, annee, trimestre_val, categorie=categorie)
        drilldown_state[categorie] = {"rubriques": True}

    # Re-render le tableau avec le drilldown
    df_crd = get_crd(entite_id, annee, trimestre_val)

    drilldown_data = {}
    for cat in drilldown_state:
        df_rub = get_crd_drilldown(entite_id, annee, trimestre_val, categorie=cat)
        drilldown_data[cat] = {"rubriques": df_rub}

    table = html.Div([
        create_crd_table(df_crd, drilldown_data),
        create_seuil_section(df_crd),
    ])

    return drilldown_state, table
