"""Composant Tableau CRD — avec drilldown 3 niveaux."""

from dash import html
import dash_bootstrap_components as dbc
from components.kpi_cards import format_euros


# Lignes du CRD dans l'ordre
CRD_LINES = [
    {"key": "ca", "label": "Chiffre d'affaires", "pct_key": None, "bold": True},
    {"key": "charges_variables", "label": "Charges variables", "pct_key": "pct_charges_var",
     "categorie": "Charges variables"},
    {"key": "mcv", "label": "Marge sur cout variable (MCV)", "pct_key": "pct_mcv", "bold": True},
    {"key": "charges_fixes", "label": "Charges fixes d'exploitation", "pct_key": "pct_charges_fixes",
     "categorie": "Charges fixes exploitation"},
    {"key": "resultat_exploitation", "label": "Resultat d'exploitation", "pct_key": "pct_res_exploit", "bold": True},
    {"key": "resultat_financier", "label": "Resultat financier", "pct_key": None,
     "categorie": "Resultat financier"},
    {"key": "rcai", "label": "RCAI", "pct_key": "pct_rcai", "bold": True},
    {"key": "resultat_exceptionnel", "label": "Resultat exceptionnel", "pct_key": None,
     "categorie": "Resultat exceptionnel"},
    {"key": "impot_sur_societes", "label": "Impot sur les societes", "pct_key": None,
     "categorie": "Impot sur les societes"},
    {"key": "resultat_net", "label": "Resultat net", "pct_key": "pct_res_net", "bold": True},
    {"key": "caf", "label": "CAF", "pct_key": "pct_caf", "bold": True},
]


def _progress_bar(value, ca):
    """Cree une barre de progression proportionnelle au CA."""
    if ca is None or ca == 0 or value is None:
        return html.Div()
    pct = min(abs(float(value)) / abs(float(ca)) * 100, 100)
    color = "#2c5282" if float(value) >= 0 else "#9b2c2c"
    return html.Div(
        html.Div(
            style={"width": f"{pct}%", "backgroundColor": color},
            className="crd-bar-inner",
        ),
        className="crd-bar",
    )


def create_crd_row(label, montant, pct_ca, ca, bold=False, categorie=None, row_id=None):
    """Cree une ligne du tableau CRD."""
    classes = "crd-row"
    if bold:
        classes += " subtotal"

    row = html.Div(
        [
            html.Span(label, className="crd-label"),
            html.Span(format_euros(montant), className="crd-montant"),
            html.Span(
                f"{pct_ca}%" if pct_ca is not None else "",
                className="crd-pct",
            ),
            _progress_bar(montant, ca),
        ],
        className=classes,
        id={"type": "crd-row", "index": row_id or label},
        style={"cursor": "pointer"} if categorie else {},
    )
    return row


def create_drilldown_rows(df_drill, level=1):
    """Cree les lignes de drilldown (niveau 1 = rubriques, niveau 2 = comptes)."""
    rows = []
    css_class = f"crd-row drilldown-{level}"

    for _, r in df_drill.iterrows():
        if level == 1:
            label = r.get("crd_rubrique", "")
            montant = r.get("total", 0)
            row_id = f"drill-{label}"
        else:
            label = f"{r.get('compte_numero', '')} — {r.get('compte_libelle', '')}"
            montant = r.get("total", 0)
            row_id = f"compte-{r.get('compte_numero', '')}"

        rows.append(
            html.Div(
                [
                    html.Span(label, className="crd-label"),
                    html.Span(format_euros(montant), className="crd-montant"),
                ],
                className=css_class,
                id={"type": f"drill-row-{level}", "index": row_id},
                style={"cursor": "pointer"} if level == 1 else {},
            )
        )
    return rows


def create_crd_table(df_crd, drilldown_data=None):
    """Cree le tableau CRD complet avec drilldown optionnel.

    Args:
        df_crd: DataFrame v_crd (1 ligne)
        drilldown_data: dict {categorie: {df_rubriques, expanded_rubrique: df_comptes}}
    """
    if df_crd.empty:
        return html.Div("Aucune donnee CRD.", className="text-muted p-3")

    row = df_crd.iloc[0]
    ca = row.get("ca", 0)
    drilldown_data = drilldown_data or {}

    elements = [html.H5("Compte de Resultat Differentiel", className="mb-3")]

    for line in CRD_LINES:
        montant = row.get(line["key"], 0)
        pct_ca = row.get(line["pct_key"]) if line.get("pct_key") else None
        categorie = line.get("categorie")

        elements.append(
            create_crd_row(
                label=line["label"],
                montant=montant,
                pct_ca=pct_ca,
                ca=ca,
                bold=line.get("bold", False),
                categorie=categorie,
                row_id=line["key"],
            )
        )

        # Drilldown niveau 1 : rubriques
        if categorie and categorie in drilldown_data:
            dd = drilldown_data[categorie]
            elements.extend(create_drilldown_rows(dd.get("rubriques", []), level=1))

            # Drilldown niveau 2 : comptes
            if "comptes" in dd and not dd["comptes"].empty:
                elements.extend(create_drilldown_rows(dd["comptes"], level=2))

    return html.Div(elements, className="crd-table")


def create_seuil_section(df_crd):
    """Cree la section seuil de rentabilite / point mort / marge de securite."""
    if df_crd.empty:
        return html.Div()

    row = df_crd.iloc[0]

    return html.Div(
        [
            html.H6("Seuil de rentabilite", className="mb-2"),
            dbc.Row(
                [
                    dbc.Col([
                        html.Div("Seuil de rentabilite", className="kpi-title"),
                        html.Div(format_euros(row.get("seuil_rentabilite", 0)),
                                 className="kpi-value", style={"fontSize": "1.2rem"}),
                    ], md=4),
                    dbc.Col([
                        html.Div("Point mort", className="kpi-title"),
                        html.Div(f"{row.get('point_mort_jours', 0)} jours",
                                 className="kpi-value", style={"fontSize": "1.2rem"}),
                    ], md=4),
                    dbc.Col([
                        html.Div("Marge de securite", className="kpi-title"),
                        html.Div(
                            f"{format_euros(row.get('marge_securite', 0))} "
                            f"({row.get('pct_marge_securite', 0)}%)",
                            className="kpi-value", style={"fontSize": "1.2rem"}),
                    ], md=4),
                ],
            ),
        ],
        className="seuil-section",
    )
