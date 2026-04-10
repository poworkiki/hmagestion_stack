"""Composant Graphiques — courbes, barres, donut."""

import plotly.express as px
import plotly.graph_objects as go


COLORS = {
    "ca": "#2c5282",
    "mcv": "#2f855a",
    "resultat_net": "#d69e2e",
    "charges_variables": "#e53e3e",
    "charges_fixes": "#dd6b20",
}

MOIS_NOMS = [
    "", "Jan", "Fev", "Mar", "Avr", "Mai", "Jun",
    "Jul", "Aou", "Sep", "Oct", "Nov", "Dec",
]


def create_line_chart(df_ytd):
    """Courbe d'evolution mensuelle (CA, MCV, Resultat net).

    Args:
        df_ytd: DataFrame v_ytd_mensuel (12 lignes max)
    """
    if df_ytd.empty:
        return go.Figure().update_layout(
            title="Aucune donnee mensuelle",
            template="plotly_white",
        )

    df = df_ytd.copy()
    df["mois_nom"] = df["mois"].apply(lambda m: MOIS_NOMS[int(m)] if 1 <= int(m) <= 12 else "")

    fig = go.Figure()

    for col, name, color in [
        ("ca", "CA", COLORS["ca"]),
        ("resultat", "Resultat", COLORS["resultat_net"]),
    ]:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["mois_nom"],
                y=df[col],
                name=name,
                mode="lines+markers",
                line={"color": color, "width": 2},
                marker={"size": 6},
                hovertemplate="%{x}<br>%{y:,.0f} EUR<extra>" + name + "</extra>",
            ))

    fig.update_layout(
        title="Evolution mensuelle",
        xaxis_title="",
        yaxis_title="Montant (EUR)",
        yaxis_tickformat=",",
        template="plotly_white",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        margin={"t": 50, "b": 30, "l": 60, "r": 20},
        height=350,
    )

    return fig


def create_donut_chart(df_crd):
    """Donut repartition charges variables vs charges fixes.

    Args:
        df_crd: DataFrame v_crd (1 ligne)
    """
    if df_crd.empty:
        return go.Figure().update_layout(
            title="Aucune donnee",
            template="plotly_white",
        )

    row = df_crd.iloc[0]
    charges_var = abs(float(row.get("charges_variables", 0)))
    charges_fix = abs(float(row.get("charges_fixes", 0)))

    if charges_var == 0 and charges_fix == 0:
        return go.Figure().update_layout(
            title="Pas de charges",
            template="plotly_white",
        )

    fig = go.Figure(go.Pie(
        labels=["Charges variables", "Charges fixes"],
        values=[charges_var, charges_fix],
        hole=0.45,
        marker={"colors": [COLORS["charges_variables"], COLORS["charges_fixes"]]},
        textinfo="label+percent",
        textposition="outside",
        hovertemplate="%{label}<br>%{value:,.0f} EUR<br>%{percent}<extra></extra>",
    ))

    fig.update_layout(
        title="Repartition des charges",
        template="plotly_white",
        showlegend=False,
        margin={"t": 50, "b": 20, "l": 20, "r": 20},
        height=350,
    )

    return fig


def create_bar_chart(df_drilldown, title="Detail par rubrique"):
    """Barres horizontales par rubrique CRD.

    Args:
        df_drilldown: DataFrame avec colonnes crd_rubrique + total
    """
    if df_drilldown.empty:
        return go.Figure().update_layout(
            title="Aucun detail",
            template="plotly_white",
        )

    df = df_drilldown.copy()
    df = df.sort_values("total", key=abs, ascending=True)

    colors = [COLORS["ca"] if v >= 0 else COLORS["charges_variables"]
              for v in df["total"]]

    fig = go.Figure(go.Bar(
        x=df["total"],
        y=df["crd_rubrique"] if "crd_rubrique" in df.columns else df.index,
        orientation="h",
        marker_color=colors,
        hovertemplate="%{y}<br>%{x:,.0f} EUR<extra></extra>",
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Montant (EUR)",
        xaxis_tickformat=",",
        yaxis_title="",
        template="plotly_white",
        margin={"t": 50, "b": 30, "l": 200, "r": 20},
        height=max(250, len(df) * 30 + 100),
    )

    return fig


def create_comparison_chart(df_multi, kpi_cols=None):
    """Barres groupees pour comparaison multi-structures.

    Args:
        df_multi: DataFrame avec entite_nom + colonnes KPI
        kpi_cols: liste des colonnes a comparer
    """
    if df_multi.empty:
        return go.Figure().update_layout(
            title="Aucune donnee",
            template="plotly_white",
        )

    if kpi_cols is None:
        kpi_cols = ["ca", "mcv", "resultat_exploitation", "resultat_net", "caf"]

    kpi_labels = {
        "ca": "CA",
        "mcv": "MCV",
        "resultat_exploitation": "Res. Exploit.",
        "resultat_net": "Res. Net",
        "caf": "CAF",
    }

    fig = go.Figure()

    for _, row in df_multi.iterrows():
        values = [float(row.get(col, 0)) for col in kpi_cols]
        labels = [kpi_labels.get(col, col) for col in kpi_cols]
        fig.add_trace(go.Bar(
            x=labels,
            y=values,
            name=row.get("entite_nom", ""),
            hovertemplate="%{x}<br>%{y:,.0f} EUR<extra>" + str(row.get("entite_nom", "")) + "</extra>",
        ))

    fig.update_layout(
        title="Comparaison inter-structures",
        barmode="group",
        yaxis_title="Montant (EUR)",
        yaxis_tickformat=",",
        template="plotly_white",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        margin={"t": 60, "b": 30, "l": 60, "r": 20},
        height=400,
    )

    return fig
