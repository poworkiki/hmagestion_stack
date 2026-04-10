import marimo

__generated_with = "0.13.0"
app = marimo.App(width="full", app_title="HMA — Exploration Comptable")


@app.cell
def _(mo):
    mo.md(
        """
        # Exploration Comptable — HMA

        Notebook interactif connecte a PostgreSQL HMA.
        Selectionnez une structure et un exercice pour explorer les donnees.
        """
    )
    return


@app.cell
def _():
    import marimo as mo
    import os
    import psycopg2
    import psycopg2.extras
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    return go, mo, os, pd, psycopg2, px


@app.cell
def _(os, psycopg2):
    DB_URL = os.environ.get("HMA_DB_URL", "")

    def query(sql, params=None):
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                import pandas as _pd
                rows = cur.fetchall()
                return _pd.DataFrame(rows) if rows else _pd.DataFrame()

    def fmt(v):
        if v is None:
            return "0 €"
        sign = "-" if float(v) < 0 else ""
        parts = f"{abs(float(v)):,.0f}".replace(",", " ")
        return f"{sign}{parts} €"

    return DB_URL, fmt, query


@app.cell
def _(query):
    df_entites = query("SELECT id, code, nom FROM entite ORDER BY nom")
    df_annees = query("SELECT DISTINCT annee FROM balance_generale ORDER BY annee DESC")
    entite_map = {row["nom"]: str(row["id"]) for _, row in df_entites.iterrows()}
    annee_list = df_annees["annee"].tolist() if not df_annees.empty else [2026]
    return annee_list, entite_map


@app.cell
def _(annee_list, entite_map, mo):
    filtre_structure = mo.ui.dropdown(
        options=list(entite_map.keys()),
        value=list(entite_map.keys())[0] if entite_map else None,
        label="Structure",
    )
    filtre_annee = mo.ui.dropdown(
        options=[str(a) for a in annee_list],
        value=str(annee_list[0]) if annee_list else "2026",
        label="Exercice",
    )
    filtre_mois = mo.ui.slider(
        start=1, stop=12, value=12, label="Mois (jusqu'a)", show_value=True,
    )

    mo.hstack([filtre_structure, filtre_annee, filtre_mois], justify="start", gap=1)
    return filtre_annee, filtre_mois, filtre_structure


@app.cell
def _(entite_map, filtre_annee, filtre_structure):
    _entite_id = entite_map.get(filtre_structure.value, "")
    _annee = int(filtre_annee.value)

    entite_id = _entite_id
    annee = _annee
    return annee, entite_id


# ── ONGLETS ─────────────────────────────────────────────────────

@app.cell
def _(mo):
    tabs = mo.ui.tabs({
        "Balance Generale": "bg",
        "Grand Livre": "gl",
        "CRD": "crd",
        "Bilan Fonctionnel": "bf",
        "SQL Libre": "sql_libre",
    })
    tabs
    return (tabs,)


# ── BALANCE GENERALE ────────────────────────────────────────────

@app.cell
def _(annee, entite_id, filtre_mois, mo, pd, px, query, tabs):
    mo.stop(tabs.value != "bg")

    df_bg = query("""
        SELECT compte_numero, compte_libelle, classe, mois, mois_label,
            solde, crd_categorie, sig_solde, bf_categorie
        FROM balance_generale
        WHERE entite_id = %s::uuid AND annee = %s AND mois <= %s
        ORDER BY compte_numero, mois
    """, (entite_id, annee, filtre_mois.value))

    if df_bg.empty:
        mo.md("**Aucune donnee pour cette selection.**")
    else:
        # Resume par classe
        resume = df_bg.groupby("classe").agg(
            solde=("solde", "sum"),
            nb_comptes=("compte_numero", "nunique"),
        ).reset_index()
        resume["classe"] = resume["classe"].astype(str)

        fig_classes = px.bar(
            resume, x="classe", y="solde", color="classe",
            title="Solde par classe comptable",
            labels={"solde": "Solde (€)", "classe": "Classe"},
            text_auto=",.0f",
        )
        fig_classes.update_layout(showlegend=False, yaxis_tickformat=",")

        mo.vstack([
            mo.md(f"### Balance Generale — {df_bg['compte_numero'].nunique()} comptes, {len(df_bg)} lignes"),
            mo.ui.plotly(fig_classes),
            mo.ui.dataframe(df_bg),
        ])
    return


# ── GRAND LIVRE ─────────────────────────────────────────────────

@app.cell
def _(annee, entite_id, filtre_mois, mo, query, tabs):
    mo.stop(tabs.value != "gl")

    # Filtre compte
    gl_filtre_compte = mo.ui.text(
        value="", label="Filtre compte (ex: 411, 60)",
        placeholder="Numero de compte...",
    )
    gl_filtre_compte
    return (gl_filtre_compte,)


@app.cell
def _(annee, entite_id, filtre_mois, gl_filtre_compte, mo, query, tabs):
    mo.stop(tabs.value != "gl")

    compte_filter = gl_filtre_compte.value.strip()
    where_compte = f"AND compte_numero LIKE '{compte_filter}%%'" if compte_filter else ""

    df_gl = query(f"""
        SELECT ecriture_date, journal_code, ecriture_numero,
            compte_numero, compte_libelle, piece_ref, libelle,
            debit, credit, (debit - credit) AS solde
        FROM grand_livre
        WHERE entite_id = %s::uuid AND annee = %s AND mois <= %s
            {where_compte}
        ORDER BY ecriture_date, ecriture_numero
        LIMIT 500
    """, (entite_id, annee, filtre_mois.value))

    if df_gl.empty:
        mo.md("**Aucune ecriture trouvee.**")
    else:
        mo.vstack([
            mo.md(f"### Grand Livre — {len(df_gl)} ecritures (limite 500)"),
            mo.ui.dataframe(df_gl),
        ])
    return


# ── CRD ─────────────────────────────────────────────────────────

@app.cell
def _(annee, entite_id, fmt, go, mo, pd, px, query, tabs):
    mo.stop(tabs.value != "crd")

    df_crd = query("""
        SELECT * FROM v_crd
        WHERE entite_id = %s::uuid AND annee = %s
        ORDER BY trimestre
    """, (entite_id, annee))

    if df_crd.empty:
        mo.md("**Aucune donnee CRD.**")
    else:
        # Agreger annee complete
        total = df_crd.agg({
            "ca": "sum", "charges_variables": "sum", "mcv": "sum",
            "charges_fixes": "sum", "resultat_exploitation": "sum",
            "resultat_financier": "sum", "rcai": "sum",
            "resultat_net": "sum", "caf": "sum",
        })

        # Waterfall
        labels = ["CA", "- Ch. var.", "MCV", "- Ch. fixes",
                  "Res. exploit.", "Res. fin.", "RCAI", "Res. net"]
        values = [
            float(total["ca"]), -float(total["charges_variables"]),
            float(total["mcv"]), -float(total["charges_fixes"]),
            float(total["resultat_exploitation"]),
            float(total["resultat_financier"]),
            float(total["rcai"]), float(total["resultat_net"]),
        ]
        measures = ["absolute", "relative", "total", "relative",
                    "total", "relative", "total", "total"]

        fig_wf = go.Figure(go.Waterfall(
            x=labels, y=values, measure=measures,
            text=[fmt(v) for v in values], textposition="outside",
            increasing={"marker": {"color": "#38a169"}},
            decreasing={"marker": {"color": "#e53e3e"}},
            totals={"marker": {"color": "#3182ce"}},
        ))
        fig_wf.update_layout(
            title="Formation du resultat", yaxis_tickformat=",",
            template="plotly_white", height=400,
        )

        # Evolution trimestrielle
        fig_trim = px.bar(
            df_crd, x="trimestre", y=["ca", "mcv", "resultat_net"],
            barmode="group", title="Evolution trimestrielle",
            labels={"value": "Montant (€)", "trimestre": "Trimestre"},
        )
        fig_trim.update_layout(yaxis_tickformat=",")

        # KPI
        kpi_md = f"""
        | Indicateur | Montant | % CA |
        |---|---|---|
        | **CA** | {fmt(total['ca'])} | 100% |
        | **MCV** | {fmt(total['mcv'])} | {round(float(total['mcv'])/float(total['ca'])*100,1) if float(total['ca']) else 0}% |
        | **Res. exploitation** | {fmt(total['resultat_exploitation'])} | {round(float(total['resultat_exploitation'])/float(total['ca'])*100,1) if float(total['ca']) else 0}% |
        | **Resultat net** | {fmt(total['resultat_net'])} | {round(float(total['resultat_net'])/float(total['ca'])*100,1) if float(total['ca']) else 0}% |
        | **CAF** | {fmt(total['caf'])} | {round(float(total['caf'])/float(total['ca'])*100,1) if float(total['ca']) else 0}% |
        """

        mo.vstack([
            mo.md("### Compte de Resultat Differentiel"),
            mo.md(kpi_md),
            mo.ui.plotly(fig_wf),
            mo.ui.plotly(fig_trim),
        ])
    return


# ── BILAN FONCTIONNEL ───────────────────────────────────────────

@app.cell
def _(annee, entite_id, fmt, go, mo, px, query, tabs):
    mo.stop(tabs.value != "bf")

    df_bf = query("""
        SELECT bf_categorie, SUM(montant) AS montant
        FROM v_bilan_fonctionnel
        WHERE entite_id = %s::uuid AND annee = %s
        GROUP BY bf_categorie
    """, (entite_id, annee))

    if df_bf.empty:
        mo.md("**Aucune donnee Bilan Fonctionnel.**")
    else:
        bf = {row["bf_categorie"]: float(row["montant"]) for _, row in df_bf.iterrows()}
        emplois = bf.get("emplois_stables", 0)
        ressources = bf.get("ressources_stables", 0)
        bfr_e = bf.get("bfr_exploit", 0)
        bfr_he = bf.get("bfr_hors_exploit", 0)
        treso_a = bf.get("tresorerie_active", 0)
        treso_p = bf.get("tresorerie_passive", 0)

        frng = ressources - emplois
        bfr = bfr_e + bfr_he
        tn = treso_a - treso_p

        ok = abs(frng - (bfr + tn)) < 1
        verif = "✓ Equilibre verifie" if ok else f"✗ Ecart : {fmt(abs(frng - (bfr + tn)))}"

        kpi_bf = f"""
        | Indicateur | Montant |
        |---|---|
        | **FRNG** | {fmt(frng)} |
        | **BFR** | {fmt(bfr)} |
        | **Tresorerie Nette** | {fmt(tn)} |
        | **Verification** | {verif} |
        """

        # Bar chart
        fig_bf = go.Figure()
        cats = list(bf.keys())
        vals = list(bf.values())
        colors = ["#2c5282" if v >= 0 else "#c53030" for v in vals]
        labels_bf = {
            "emplois_stables": "Emplois stables", "ressources_stables": "Ressources stables",
            "bfr_exploit": "BFR exploit.", "bfr_hors_exploit": "BFR hors exploit.",
            "tresorerie_active": "Treso. active", "tresorerie_passive": "Treso. passive",
        }
        fig_bf.add_trace(go.Bar(
            x=[labels_bf.get(c, c) for c in cats], y=vals,
            marker_color=colors,
            text=[fmt(v) for v in vals], textposition="outside",
        ))
        fig_bf.update_layout(
            title="Bilan Fonctionnel", yaxis_tickformat=",",
            template="plotly_white", height=400,
        )

        # Drilldown
        df_drill = query("""
            SELECT bf_categorie, compte_numero, compte_libelle,
                SUM(CASE
                    WHEN bf_categorie IN ('emplois_stables','bfr_exploit','bfr_hors_exploit','tresorerie_active')
                    THEN debit - credit ELSE credit - debit
                END) AS montant
            FROM grand_livre
            WHERE entite_id = %s::uuid AND annee = %s AND bf_categorie IS NOT NULL
            GROUP BY bf_categorie, compte_numero, compte_libelle
            HAVING ABS(SUM(debit - credit)) > 0
            ORDER BY bf_categorie, ABS(SUM(debit - credit)) DESC
        """, (entite_id, annee))

        mo.vstack([
            mo.md("### Bilan Fonctionnel"),
            mo.md(kpi_bf),
            mo.ui.plotly(fig_bf),
            mo.md("### Detail par compte"),
            mo.ui.dataframe(df_drill) if not df_drill.empty else mo.md("Aucun detail"),
        ])
    return


# ── SQL LIBRE ───────────────────────────────────────────────────

@app.cell
def _(mo, tabs):
    mo.stop(tabs.value != "sql_libre")

    sql_input = mo.ui.text_area(
        value="SELECT entite_nom, annee, COUNT(*) AS nb_ecritures\nFROM grand_livre\nGROUP BY entite_nom, annee\nORDER BY entite_nom, annee",
        label="Requete SQL (lecture seule)",
        rows=6,
        full_width=True,
    )
    sql_input
    return (sql_input,)


@app.cell
def _(mo, query, sql_input, tabs):
    mo.stop(tabs.value != "sql_libre")

    sql_text = sql_input.value.strip()
    if not sql_text:
        mo.md("Ecrivez une requete SQL ci-dessus.")
    else:
        try:
            df_sql = query(sql_text)
            mo.vstack([
                mo.md(f"**{len(df_sql)} lignes**"),
                mo.ui.dataframe(df_sql),
            ])
        except Exception as e:
            mo.md(f"**Erreur SQL** : `{e}`")
    return


if __name__ == "__main__":
    app.run()
