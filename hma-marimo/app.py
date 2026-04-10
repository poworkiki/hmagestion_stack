import marimo

__generated_with = "0.13.0"
app = marimo.App(width="full", app_title="HMA — Exploration Comptable")

with app.setup:
    import marimo as mo
    import os
    import psycopg2
    import psycopg2.extras
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go


@app.function
def db_query(sql, params=None):
    _DB_URL = os.environ.get("HMA_DB_URL", "")
    with psycopg2.connect(_DB_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return pd.DataFrame(rows) if rows else pd.DataFrame()


@app.function
def fmt(v):
    if v is None:
        return "0 €"
    n = float(v)
    if n == 0:
        return "0 €"
    sign = "-" if n < 0 else ""
    parts = f"{abs(n):,.0f}".replace(",", " ")
    return f"{sign}{parts} €"


# ── TITRE ───────────────────────────────────────────────────────

@app.cell(hide_code=True)
def _():
    mo.md(
        """
        # Exploration Comptable — HMA

        Notebook interactif connecte a PostgreSQL HMA.
        Selectionnez une structure et un exercice pour explorer les donnees.
        """
    )
    return


# ── FILTRES (creation) ──────────────────────────────────────────

@app.cell(hide_code=True)
def _():
    _df_entites = db_query("SELECT id, code, nom FROM entite ORDER BY nom")
    _df_annees = db_query("SELECT DISTINCT annee FROM balance_generale ORDER BY annee DESC")
    entite_map = {row["nom"]: str(row["id"]) for _, row in _df_entites.iterrows()}
    annee_list = [str(a) for a in _df_annees["annee"].tolist()] if not _df_annees.empty else ["2026"]

    filtre_structure = mo.ui.dropdown(
        options=list(entite_map.keys()),
        value=list(entite_map.keys())[0] if entite_map else None,
        label="Structure",
    )
    filtre_annee = mo.ui.dropdown(
        options=annee_list,
        value=annee_list[0] if annee_list else "2026",
        label="Exercice",
    )
    filtre_mois = mo.ui.slider(
        start=1, stop=12, value=12, label="Mois (jusqu'a)", show_value=True,
    )

    mo.hstack([filtre_structure, filtre_annee, filtre_mois], justify="start", gap=1)
    return (annee_list, entite_map, filtre_annee, filtre_mois, filtre_structure)


# ── FILTRES (lecture valeurs — cellule separee) ─────────────────

@app.cell(hide_code=True)
def _(entite_map, filtre_annee, filtre_structure, filtre_mois):
    entite_id = entite_map.get(filtre_structure.value, "")
    annee = int(filtre_annee.value)
    mois_max = filtre_mois.value
    return (annee, entite_id, mois_max)


# ── BALANCE GENERALE ────────────────────────────────────────────

@app.cell(hide_code=True)
def _(annee, entite_id, mois_max):
    _df_bg = db_query("""
        SELECT compte_numero, compte_libelle, classe, mois, mois_label,
            solde, crd_categorie, sig_solde, bf_categorie
        FROM balance_generale
        WHERE entite_id = %s::uuid AND annee = %s AND mois <= %s
        ORDER BY compte_numero, mois
    """, (entite_id, annee, mois_max))

    if _df_bg.empty:
        bg_tab = mo.md("**Aucune donnee pour cette selection.**")
    else:
        _resume = _df_bg.groupby("classe").agg(
            solde=("solde", "sum"),
            nb_comptes=("compte_numero", "nunique"),
        ).reset_index()
        _resume["classe"] = _resume["classe"].astype(str)

        _fig = px.bar(
            _resume, x="classe", y="solde", color="classe",
            title="Solde par classe comptable",
            labels={"solde": "Solde (€)", "classe": "Classe"},
            text_auto=",.0f",
        )
        _fig.update_layout(showlegend=False, yaxis_tickformat=",", template="plotly_white")

        bg_tab = mo.vstack([
            mo.md(f"### {_df_bg['compte_numero'].nunique()} comptes — {len(_df_bg)} lignes"),
            mo.ui.plotly(_fig),
            mo.ui.dataframe(_df_bg),
        ])
    return (bg_tab,)


# ── GRAND LIVRE (filtre compte — creation) ──────────────────────

@app.cell(hide_code=True)
def _():
    gl_filtre_compte = mo.ui.text(
        value="", label="Filtre compte (ex: 411, 60)",
        placeholder="Numero de compte...",
    )
    return (gl_filtre_compte,)


# ── GRAND LIVRE (contenu — lecture valeur) ──────────────────────

@app.cell(hide_code=True)
def _(annee, entite_id, gl_filtre_compte, mois_max):
    _compte = gl_filtre_compte.value.strip()
    _where = f"AND compte_numero LIKE '{_compte}%%'" if _compte else ""

    _df_gl = db_query(f"""
        SELECT ecriture_date, journal_code, ecriture_numero,
            compte_numero, compte_libelle, piece_ref, libelle,
            debit, credit, (debit - credit) AS solde
        FROM grand_livre
        WHERE entite_id = %s::uuid AND annee = %s AND mois <= %s
            {_where}
        ORDER BY ecriture_date, ecriture_numero
        LIMIT 500
    """, (entite_id, annee, mois_max))

    if _df_gl.empty:
        gl_tab = mo.vstack([gl_filtre_compte, mo.md("**Aucune ecriture trouvee.**")])
    else:
        gl_tab = mo.vstack([
            gl_filtre_compte,
            mo.md(f"### {len(_df_gl)} ecritures (limite 500)"),
            mo.ui.dataframe(_df_gl),
        ])
    return (gl_tab,)


# ── CRD ─────────────────────────────────────────────────────────

@app.cell(hide_code=True)
def _(annee, entite_id):
    _df_crd = db_query("""
        SELECT * FROM v_crd
        WHERE entite_id = %s::uuid AND annee = %s
        ORDER BY trimestre
    """, (entite_id, annee))

    if _df_crd.empty:
        crd_tab = mo.md("**Aucune donnee CRD.**")
    else:
        _t = _df_crd.agg({
            "ca": "sum", "charges_variables": "sum", "mcv": "sum",
            "charges_fixes": "sum", "resultat_exploitation": "sum",
            "resultat_financier": "sum", "rcai": "sum",
            "resultat_net": "sum", "caf": "sum",
        })

        _labels = ["CA", "- Ch. var.", "MCV", "- Ch. fixes",
                   "Res. exploit.", "Res. fin.", "RCAI", "Res. net"]
        _values = [
            float(_t["ca"]), -float(_t["charges_variables"]),
            float(_t["mcv"]), -float(_t["charges_fixes"]),
            float(_t["resultat_exploitation"]),
            float(_t["resultat_financier"]),
            float(_t["rcai"]), float(_t["resultat_net"]),
        ]
        _measures = ["absolute", "relative", "total", "relative",
                     "total", "relative", "total", "total"]

        _fig_wf = go.Figure(go.Waterfall(
            x=_labels, y=_values, measure=_measures,
            text=[fmt(v) for v in _values], textposition="outside",
            increasing={"marker": {"color": "#38a169"}},
            decreasing={"marker": {"color": "#e53e3e"}},
            totals={"marker": {"color": "#3182ce"}},
        ))
        _fig_wf.update_layout(
            title="Formation du resultat", yaxis_tickformat=",",
            template="plotly_white", height=420,
        )

        _fig_trim = px.bar(
            _df_crd, x="trimestre", y=["ca", "mcv", "resultat_net"],
            barmode="group", title="Evolution trimestrielle",
            labels={"value": "Montant (€)", "trimestre": "Trimestre"},
        )
        _fig_trim.update_layout(yaxis_tickformat=",", template="plotly_white")

        _ca = float(_t["ca"]) if float(_t["ca"]) != 0 else 1
        _kpi = f"""
| Indicateur | Montant | % CA |
|---|---|---|
| **CA** | {fmt(_t['ca'])} | 100% |
| **MCV** | {fmt(_t['mcv'])} | {round(float(_t['mcv'])/_ca*100,1)}% |
| **Res. exploitation** | {fmt(_t['resultat_exploitation'])} | {round(float(_t['resultat_exploitation'])/_ca*100,1)}% |
| **Resultat net** | {fmt(_t['resultat_net'])} | {round(float(_t['resultat_net'])/_ca*100,1)}% |
| **CAF** | {fmt(_t['caf'])} | {round(float(_t['caf'])/_ca*100,1)}% |
"""

        crd_tab = mo.vstack([
            mo.md(_kpi),
            mo.ui.plotly(_fig_wf),
            mo.ui.plotly(_fig_trim),
        ])
    return (crd_tab,)


# ── BILAN FONCTIONNEL ───────────────────────────────────────────

@app.cell(hide_code=True)
def _(annee, entite_id):
    _df_bf = db_query("""
        SELECT bf_categorie, SUM(montant) AS montant
        FROM v_bilan_fonctionnel
        WHERE entite_id = %s::uuid AND annee = %s
        GROUP BY bf_categorie
    """, (entite_id, annee))

    if _df_bf.empty:
        bf_tab = mo.md("**Aucune donnee Bilan Fonctionnel.**")
    else:
        _bf = {r["bf_categorie"]: float(r["montant"]) for _, r in _df_bf.iterrows()}
        _frng = _bf.get("ressources_stables", 0) - _bf.get("emplois_stables", 0)
        _bfr = _bf.get("bfr_exploit", 0) + _bf.get("bfr_hors_exploit", 0)
        _tn = _bf.get("tresorerie_active", 0) - _bf.get("tresorerie_passive", 0)
        _ok = abs(_frng - (_bfr + _tn)) < 1
        _verif = "✓ Equilibre" if _ok else f"✗ Ecart: {fmt(abs(_frng - (_bfr + _tn)))}"

        _kpi = f"""
| Indicateur | Montant |
|---|---|
| **FRNG** | {fmt(_frng)} |
| **BFR** | {fmt(_bfr)} |
| **Tresorerie Nette** | {fmt(_tn)} |
| **Verification** | {_verif} |
"""
        _lbl = {"emplois_stables": "Emplois stables", "ressources_stables": "Ress. stables",
                "bfr_exploit": "BFR exploit.", "bfr_hors_exploit": "BFR hors exploit.",
                "tresorerie_active": "Treso. active", "tresorerie_passive": "Treso. passive"}
        _cats = list(_bf.keys())
        _vals = list(_bf.values())

        _fig = go.Figure(go.Bar(
            x=[_lbl.get(c, c) for c in _cats], y=_vals,
            marker_color=["#2c5282" if v >= 0 else "#c53030" for v in _vals],
            text=[fmt(v) for v in _vals], textposition="outside",
        ))
        _fig.update_layout(title="Bilan Fonctionnel", yaxis_tickformat=",",
                           template="plotly_white", height=400)

        _drill = db_query("""
            SELECT bf_categorie, compte_numero, compte_libelle,
                SUM(CASE WHEN bf_categorie IN ('emplois_stables','bfr_exploit','bfr_hors_exploit','tresorerie_active')
                    THEN debit - credit ELSE credit - debit END) AS montant
            FROM grand_livre
            WHERE entite_id = %s::uuid AND annee = %s AND bf_categorie IS NOT NULL
            GROUP BY bf_categorie, compte_numero, compte_libelle
            HAVING ABS(SUM(debit - credit)) > 0
            ORDER BY bf_categorie, ABS(SUM(debit - credit)) DESC
        """, (entite_id, annee))

        bf_tab = mo.vstack([
            mo.md(_kpi),
            mo.ui.plotly(_fig),
            mo.md("### Detail par compte"),
            mo.ui.dataframe(_drill) if not _drill.empty else mo.md("Aucun detail"),
        ])
    return (bf_tab,)


# ── SQL LIBRE (creation textarea) ───────────────────────────────

@app.cell(hide_code=True)
def _():
    sql_input = mo.ui.text_area(
        value="SELECT entite_nom, annee, COUNT(*) AS nb_ecritures\nFROM grand_livre\nGROUP BY entite_nom, annee\nORDER BY entite_nom, annee",
        label="Requete SQL (lecture seule)",
        rows=6,
        full_width=True,
    )
    return (sql_input,)


# ── SQL LIBRE (execution — cellule separee) ─────────────────────

@app.cell(hide_code=True)
def _(sql_input):
    _sql = sql_input.value.strip()
    if not _sql:
        _result = mo.md("Ecrivez une requete SQL ci-dessus.")
    else:
        try:
            _df = db_query(_sql)
            _result = mo.vstack([
                mo.md(f"**{len(_df)} lignes**"),
                mo.ui.dataframe(_df),
            ])
        except Exception as e:
            _result = mo.md(f"**Erreur SQL** : `{e}`")

    sql_tab = mo.vstack([sql_input, _result])
    return (sql_tab,)


# ── TABS (assemblage final) ─────────────────────────────────────

@app.cell(hide_code=True)
def _(bg_tab, bf_tab, crd_tab, gl_tab, sql_tab):
    mo.ui.tabs({
        "Balance Generale": bg_tab,
        "Grand Livre": gl_tab,
        "CRD": crd_tab,
        "Bilan Fonctionnel": bf_tab,
        "SQL Libre": sql_tab,
    })
    return


if __name__ == "__main__":
    app.run()
