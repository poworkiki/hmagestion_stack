"""Composant KPI Cards — 5 indicateurs cles CRD."""

from dash import html
import dash_bootstrap_components as dbc


def format_euros(value):
    """Formate un montant en euros (ex: 1 234 567 euros)."""
    if value is None or value == 0:
        return "0 EUR"
    sign = "-" if value < 0 else ""
    abs_val = abs(float(value))
    if abs_val >= 1_000_000:
        return f"{sign}{abs_val:,.0f} EUR".replace(",", " ")
    elif abs_val >= 1_000:
        return f"{sign}{abs_val:,.0f} EUR".replace(",", " ")
    else:
        return f"{sign}{abs_val:,.0f} EUR"


def _calc_delta(current, reference):
    """Calcule le delta en % entre la valeur courante et la reference."""
    if reference is None or reference == 0:
        return None, None
    delta_pct = round((float(current) - float(reference)) / abs(float(reference)) * 100, 1)
    direction = "up" if delta_pct >= 0 else "down"
    return delta_pct, direction


def create_kpi_card(title, value, pct_ca, delta_pct=None, delta_direction=None):
    """Cree une KPI card individuelle.

    Args:
        title: Titre de la card (ex: "CA", "MCV")
        value: Montant en euros
        pct_ca: Pourcentage du CA
        delta_pct: Evolution en % vs reference (None si pas de reference)
        delta_direction: "up" ou "down"
    """
    # Fleche et couleur du delta
    if delta_pct is not None:
        arrow = "+" if delta_direction == "up" else ""
        delta_class = "kpi-delta-up" if delta_direction == "up" else "kpi-delta-down"
        delta_symbol = " ▲" if delta_direction == "up" else " ▼"
        delta_text = f"{arrow}{delta_pct}%{delta_symbol}"
        delta_div = html.Div(delta_text, className=delta_class)
    else:
        delta_div = html.Div("—", className="kpi-pct")

    # Couleur de la valeur selon signe
    value_color = "#9b2c2c" if value is not None and float(value) < 0 else "#1a365d"

    return dbc.Col(
        html.Div(
            [
                html.Div(title, className="kpi-title"),
                html.Div(
                    format_euros(value),
                    className="kpi-value",
                    style={"color": value_color},
                ),
                html.Div(f"{pct_ca}% du CA" if pct_ca else "", className="kpi-pct"),
                delta_div,
            ],
            className="kpi-card",
        ),
        lg=2, md=4, sm=6, xs=12,
        className="mb-2",
    )


def create_kpi_row(df_crd, df_ref=None):
    """Cree la rangee de 5 KPI cards depuis un DataFrame v_crd.

    Args:
        df_crd: DataFrame avec les colonnes CRD (1 ligne)
        df_ref: DataFrame de reference pour le delta (1 ligne, optionnel)
    """
    if df_crd.empty:
        return dbc.Row(
            dbc.Col(
                html.Div("Aucune donnee pour cette periode.",
                         className="text-center text-muted p-4"),
                width=12,
            )
        )

    row = df_crd.iloc[0]
    ref = df_ref.iloc[0] if df_ref is not None and not df_ref.empty else None

    kpis = [
        ("CA", "ca", "pct_mcv"),  # pct_ca = 100% pour CA, on utilise pct_mcv comme info
        ("MCV", "mcv", "pct_mcv"),
        ("Res. Exploitation", "resultat_exploitation", "pct_res_exploit"),
        ("Resultat Net", "resultat_net", "pct_res_net"),
        ("CAF", "caf", "pct_caf"),
    ]

    cards = []
    for title, col, pct_col in kpis:
        value = row.get(col, 0)
        # Pour le CA, le % du CA est 100% par definition
        if col == "ca":
            pct_ca = 100.0
        else:
            pct_ca = row.get(pct_col, 0)

        # Calcul delta si reference disponible
        if ref is not None and col in ref.index:
            delta_pct, delta_dir = _calc_delta(value, ref.get(col, 0))
        else:
            delta_pct, delta_dir = None, None

        cards.append(create_kpi_card(title, value, pct_ca, delta_pct, delta_dir))

    return dbc.Row(cards, className="g-2")
