# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo>=0.13.0",
#     "altair>=5.4.1",
#     "pandas>=2.2.0",
#     "psycopg2-binary>=2.9.10",
# ]
# ///

import marimo

__generated_with = "0.13.0"
app = marimo.App(
    width="full",
    app_title="HMA — Exploration Comptable",
    css_file="custom.css",
)

with app.setup:
    import marimo as mo
    import os
    import psycopg2
    import psycopg2.extras
    import pandas as pd
    import altair as alt
    from datetime import datetime, timezone, timedelta

    TZ_GUYANE = timezone(timedelta(hours=-3))
    JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    MOIS_FR = ["", "janvier", "fevrier", "mars", "avril", "mai", "juin",
               "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]
    GROUPE_LABEL = "Groupe (consolide)"


# ── UTILS ───────────────────────────────────────────────────────

@app.function
def db_query(sql, params=None):
    """Execute une requete SQL et retourne un DataFrame pandas."""
    _DB_URL = os.environ.get("HMA_DB_URL", "")
    with psycopg2.connect(_DB_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return pd.DataFrame(rows) if rows else pd.DataFrame()


@app.function
def fmt(v):
    """Format montant : 1 000 000 €"""
    if v is None:
        return "0 €"
    n = float(v)
    if n == 0:
        return "0 €"
    sign = "-" if n < 0 else ""
    parts = f"{abs(n):,.0f}".replace(",", " ")
    return f"{sign}{parts} €"


@app.function
def delta_pct(current, previous):
    """Calcule la variation en pourcentage entre 2 periodes."""
    if previous is None or previous == 0:
        return None
    return (float(current) - float(previous)) / abs(float(previous))


@app.function
def kpi_stat(label, current, previous=None, higher_is_better=True):
    """Cree un mo.stat avec comparaison a la periode precedente."""
    d = delta_pct(current, previous)
    if d is None:
        return mo.stat(
            label=label,
            value=fmt(current),
            bordered=True,
        )
    is_good = (d >= 0) if higher_is_better else (d <= 0)
    return mo.stat(
        label=label,
        value=fmt(current),
        caption=f"{d:+.1%} vs N-1",
        direction="increase" if is_good else "decrease",
        bordered=True,
    )


# ── TITRE ───────────────────────────────────────────────────────

@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
        # Exploration Comptable — HMA

        Notebook reactif connecte a PostgreSQL HMA. Utilisez la sidebar pour
        selectionner une structure et un exercice. Les donnees se mettent a jour
        automatiquement sur tous les onglets.
        """
    )
    return


# ── CHARGEMENT DES OPTIONS (cellule separee, pas d'UI) ──────────

@app.cell(hide_code=True)
def _():
    _df_entites = db_query("SELECT id, code, nom FROM entite ORDER BY nom")
    _df_annees = db_query("SELECT DISTINCT annee FROM balance_generale ORDER BY annee DESC")

    entite_map = {row["nom"]: str(row["id"]) for _, row in _df_entites.iterrows()}
    annee_list = [int(a) for a in _df_annees["annee"].tolist()] if not _df_annees.empty else [2026]
    return (annee_list, entite_map)


# ── FILTRES + SIDEBAR (dans la meme cellule) ────────────────────

@app.cell(hide_code=True)
def _(annee_list, entite_map):
    _structure_options = [GROUPE_LABEL] + list(entite_map.keys())
    filtre_structure = mo.ui.dropdown(
        options=_structure_options,
        value=GROUPE_LABEL,
        label="Structure",
        full_width=True,
    )
    filtre_annee = mo.ui.dropdown(
        options=[str(a) for a in annee_list],
        value=str(annee_list[0]) if annee_list else "2026",
        label="Exercice",
        full_width=True,
    )
    filtre_trimestre = mo.ui.dropdown(
        options=["Annee", "T1", "T2", "T3", "T4"],
        value="Annee",
        label="Periode",
        full_width=True,
    )
    filtre_mois = mo.ui.dropdown(
        options=[
            "Tous",
            "Jan", "Fev", "Mar", "Avr", "Mai", "Jun",
            "Jul", "Aou", "Sep", "Oct", "Nov", "Dec",
        ],
        value="Tous",
        label="Mois",
        full_width=True,
    )

    _now = datetime.now(TZ_GUYANE)
    _date_str = f"{JOURS_FR[_now.weekday()]} {_now.day} {MOIS_FR[_now.month]} {_now.year}"
    _heure_str = _now.strftime("%H:%M")

    mo.sidebar(
        [
            mo.md("# HMA"),
            mo.md("**Exploration Comptable**"),
            mo.md("---"),
            mo.md("### Filtres"),
            filtre_structure,
            filtre_annee,
            filtre_trimestre,
            filtre_mois,
            mo.md("---"),
            mo.md(
                f"<div style='font-size:0.8rem; color:#6c757d; line-height:1.4;'>"
                f"📅 <strong>{_date_str}</strong><br>"
                f"🕐 {_heure_str} (heure Guyane)"
                f"</div>"
            ),
            mo.md("---"),
            mo.md("### Legende"),
            mo.md(
                "- **Solde** = montant net\n"
                "- **N-1** = exercice precedent\n"
                "- **CRD** = Compte de Resultat Differentiel\n"
                "- **BF** = Bilan Fonctionnel"
            ),
            mo.md("---"),
            mo.md("_Source : PostgreSQL HMA_"),
        ],
        footer=mo.md("**HMA** · Marimo · Gestion Guyane"),
    )
    return (filtre_annee, filtre_mois, filtre_structure, filtre_trimestre)


# ── FILTRES (lecture des valeurs — cellule separee) ─────────────

@app.cell(hide_code=True)
def _(entite_map, filtre_annee, filtre_mois, filtre_structure, filtre_trimestre):
    _val = filtre_structure.value or GROUPE_LABEL
    is_groupe = (_val == GROUPE_LABEL)
    entite_id = None if is_groupe else entite_map.get(_val, "")
    entite_nom = "Groupe" if is_groupe else _val
    annee = int(filtre_annee.value)
    annee_prev = annee - 1
    trimestre = filtre_trimestre.value
    trim_num = None if trimestre == "Annee" else int(trimestre[1:])

    _mois_map = {
        "Tous": None, "Jan": 1, "Fev": 2, "Mar": 3, "Avr": 4, "Mai": 5, "Jun": 6,
        "Jul": 7, "Aou": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }
    mois_num = _mois_map.get(filtre_mois.value)
    return (annee, annee_prev, entite_id, entite_nom, is_groupe, mois_num, trim_num, trimestre)


# ── PAGE 1 : VUE D'ENSEMBLE (KPI + trends) ──────────────────────

@app.cell(hide_code=True)
def _(annee, annee_prev, entite_id, trim_num):
    _clauses = ["annee = %s"]
    _base_n = [annee]
    _base_p = [annee_prev]
    if entite_id:
        _clauses.insert(0, "entite_id = %s::uuid")
        _base_n.insert(0, entite_id)
        _base_p.insert(0, entite_id)
    if trim_num:
        _clauses.append("trimestre = %s")
        _base_n.append(trim_num)
        _base_p.append(trim_num)
    _where = " AND ".join(_clauses)

    _df_n = db_query(f"""
        SELECT
            SUM(ca) AS ca,
            SUM(mcv) AS mcv,
            SUM(charges_variables) AS cv,
            SUM(charges_fixes) AS cf,
            SUM(resultat_exploitation) AS res_exp,
            SUM(resultat_net) AS res_net,
            SUM(caf) AS caf
        FROM v_crd
        WHERE {_where}
    """, tuple(_base_n))

    _df_p = db_query(f"""
        SELECT
            SUM(ca) AS ca,
            SUM(mcv) AS mcv,
            SUM(resultat_net) AS res_net,
            SUM(caf) AS caf
        FROM v_crd
        WHERE {_where}
    """, tuple(_base_p))

    kpi_data = {
        "ca_n": float(_df_n.iloc[0]["ca"] or 0) if not _df_n.empty else 0,
        "mcv_n": float(_df_n.iloc[0]["mcv"] or 0) if not _df_n.empty else 0,
        "cv_n": float(_df_n.iloc[0]["cv"] or 0) if not _df_n.empty else 0,
        "cf_n": float(_df_n.iloc[0]["cf"] or 0) if not _df_n.empty else 0,
        "res_exp_n": float(_df_n.iloc[0]["res_exp"] or 0) if not _df_n.empty else 0,
        "res_net_n": float(_df_n.iloc[0]["res_net"] or 0) if not _df_n.empty else 0,
        "caf_n": float(_df_n.iloc[0]["caf"] or 0) if not _df_n.empty else 0,
        "ca_p": float(_df_p.iloc[0]["ca"] or 0) if not _df_p.empty else 0,
        "mcv_p": float(_df_p.iloc[0]["mcv"] or 0) if not _df_p.empty else 0,
        "res_net_p": float(_df_p.iloc[0]["res_net"] or 0) if not _df_p.empty else 0,
        "caf_p": float(_df_p.iloc[0]["caf"] or 0) if not _df_p.empty else 0,
    }
    return (kpi_data,)


@app.cell(hide_code=True)
def _(annee, entite_id):
    _clauses = ["annee = %s", "NOT is_a_nouveau"]
    _params = [annee]
    if entite_id:
        _clauses.insert(0, "entite_id = %s::uuid")
        _params.insert(0, entite_id)
    _df_dr = db_query(
        f"SELECT MAX(ecriture_date) AS d FROM grand_livre WHERE {' AND '.join(_clauses)}",
        tuple(_params),
    )
    if _df_dr.empty or _df_dr.iloc[0]["d"] is None:
        date_ref = None
        date_ref_str = ""
    else:
        date_ref = _df_dr.iloc[0]["d"]
        date_ref_str = date_ref.strftime("%d/%m/%Y")
    return (date_ref, date_ref_str)


@app.cell(hide_code=True)
def _(date_ref_str, kpi_data):
    def _stat_ytd(label, cur, prev, higher=True):
        d = delta_pct(cur, prev)
        caption = f"YTD au {date_ref_str}" if date_ref_str else None
        if d is not None:
            caption = f"{caption} · {d:+.1%} vs N-1" if caption else f"{d:+.1%} vs N-1"
            is_good = (d >= 0) if higher else (d <= 0)
            return mo.stat(
                label=label, value=fmt(cur), caption=caption,
                direction="increase" if is_good else "decrease", bordered=True,
            )
        return mo.stat(label=label, value=fmt(cur), caption=caption, bordered=True)

    if kpi_data["ca_n"] == 0 and kpi_data["res_net_n"] == 0:
        kpi_row = mo.callout(
            "Aucune donnee pour cette selection (structure/exercice/periode).",
            kind="warn",
        )
    else:
        kpi_row = mo.hstack(
            [
                _stat_ytd("Chiffre d'affaires", kpi_data["ca_n"], kpi_data["ca_p"]),
                _stat_ytd("Marge sur cout variable", kpi_data["mcv_n"], kpi_data["mcv_p"]),
                _stat_ytd("Resultat net", kpi_data["res_net_n"], kpi_data["res_net_p"]),
                _stat_ytd("CAF", kpi_data["caf_n"], kpi_data["caf_p"]),
            ],
            widths="equal",
            gap=1,
        )
    return (kpi_row,)


# ── PAGE 1 : Waterfall CRD (Altair) ─────────────────────────────

@app.cell(hide_code=True)
def _(kpi_data):
    _steps = [
        {"label": "CA", "delta": kpi_data["ca_n"], "type": "total"},
        {"label": "- Ch. var.", "delta": -kpi_data["cv_n"], "type": "neg"},
        {"label": "MCV", "delta": 0, "type": "total"},
        {"label": "- Ch. fixes", "delta": -kpi_data["cf_n"], "type": "neg"},
        {"label": "Res. exploit.", "delta": 0, "type": "total"},
    ]

    _cum = 0
    _rows = []
    for i, s in enumerate(_steps):
        if s["type"] == "total":
            if s["label"] == "CA":
                _cum = kpi_data["ca_n"]
                _rows.append({"step": i, "label": s["label"], "start": 0, "end": _cum, "type": "total"})
            elif s["label"] == "MCV":
                _cum = kpi_data["mcv_n"]
                _rows.append({"step": i, "label": s["label"], "start": 0, "end": _cum, "type": "total"})
            elif s["label"] == "Res. exploit.":
                _cum = kpi_data["res_exp_n"]
                _rows.append({"step": i, "label": s["label"], "start": 0, "end": _cum, "type": "total"})
        else:
            _new = _cum + s["delta"]
            _rows.append({
                "step": i, "label": s["label"],
                "start": min(_cum, _new), "end": max(_cum, _new),
                "type": "neg",
            })
            _cum = _new

    _df_wf = pd.DataFrame(_rows)

    if _df_wf.empty or kpi_data["ca_n"] == 0:
        waterfall = mo.md("_Pas de donnees pour le waterfall._")
    else:
        _chart = (
            alt.Chart(_df_wf)
            .mark_bar(size=50)
            .encode(
                x=alt.X("label:N", sort=None, title="", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("start:Q", title="Montant (€)", axis=alt.Axis(format=",.0f")),
                y2="end:Q",
                color=alt.Color(
                    "type:N",
                    scale=alt.Scale(
                        domain=["total", "neg"],
                        range=["#3182ce", "#e53e3e"],
                    ),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("label:N", title="Etape"),
                    alt.Tooltip("start:Q", title="Debut", format=",.0f"),
                    alt.Tooltip("end:Q", title="Fin", format=",.0f"),
                ],
            )
            .properties(
                title="Formation du resultat d'exploitation",
                height=320,
                width="container",
            )
        )
        waterfall = mo.ui.altair_chart(_chart)
    return (waterfall,)


# ── PAGE 1 : Evolution mensuelle (Altair) ───────────────────────

@app.cell(hide_code=True)
def _(annee, entite_id):
    _clauses = ["annee = %s", "NOT is_a_nouveau", "classe IN (6, 7)"]
    _params = [annee]
    if entite_id:
        _clauses.insert(0, "entite_id = %s::uuid")
        _params.insert(0, entite_id)
    _df_mensuel = db_query(f"""
        SELECT mois, mois_label,
            SUM(CASE WHEN classe = 7 THEN credit - debit ELSE 0 END) AS produits,
            SUM(CASE WHEN classe = 6 THEN debit - credit ELSE 0 END) AS charges,
            SUM(CASE WHEN classe = 7 THEN credit - debit ELSE 0 END)
              - SUM(CASE WHEN classe = 6 THEN debit - credit ELSE 0 END) AS resultat
        FROM grand_livre
        WHERE {' AND '.join(_clauses)}
        GROUP BY mois, mois_label
        ORDER BY mois
    """, tuple(_params))

    if _df_mensuel.empty:
        evolution_chart = mo.md("_Pas de donnees mensuelles._")
    else:
        _long = _df_mensuel.melt(
            id_vars=["mois", "mois_label"],
            value_vars=["produits", "charges", "resultat"],
            var_name="type",
            value_name="montant",
        )
        _long["montant"] = _long["montant"].astype(float)

        _chart = (
            alt.Chart(_long)
            .mark_line(point=True, strokeWidth=2)
            .encode(
                x=alt.X("mois:O", title="Mois"),
                y=alt.Y("montant:Q", title="Montant (€)", axis=alt.Axis(format=",.0f")),
                color=alt.Color(
                    "type:N",
                    scale=alt.Scale(
                        domain=["produits", "charges", "resultat"],
                        range=["#38a169", "#e53e3e", "#3182ce"],
                    ),
                    legend=alt.Legend(title="", orient="top"),
                ),
                tooltip=[
                    alt.Tooltip("mois_label:N", title="Mois"),
                    alt.Tooltip("type:N", title="Type"),
                    alt.Tooltip("montant:Q", title="Montant", format=",.0f"),
                ],
            )
            .properties(
                title="Evolution mensuelle (produits / charges / resultat)",
                height=320,
                width="container",
            )
        )
        evolution_chart = mo.ui.altair_chart(_chart)
    return (evolution_chart,)


# ── PAGE 1 : Assemblage ─────────────────────────────────────────

@app.cell(hide_code=True)
def _(evolution_chart, kpi_row, waterfall):
    overview_tab = mo.vstack(
        [
            mo.md("### Indicateurs cles"),
            kpi_row,
            mo.md("### Formation du resultat"),
            waterfall,
            mo.md("### Evolution mensuelle"),
            evolution_chart,
        ],
        gap=1,
    )
    return (overview_tab,)


# ── PAGE 2 : BALANCE GENERALE ───────────────────────────────────

@app.cell(hide_code=True)
def _(annee, entite_id, mois_num):
    _clauses = ["annee = %s"]
    _params = [annee]
    if entite_id:
        _clauses.insert(0, "entite_id = %s::uuid")
        _params.insert(0, entite_id)
    if mois_num:
        _clauses.append("mois = %s")
        _params.append(mois_num)
    _df_bg = db_query(f"""
        SELECT compte_numero, compte_libelle, classe, mois,
            solde, crd_categorie, bf_categorie
        FROM balance_generale
        WHERE {' AND '.join(_clauses)}
        ORDER BY compte_numero, mois
    """, tuple(_params))

    if _df_bg.empty:
        bg_tab = mo.callout("Aucune donnee pour cet exercice.", kind="info")
    else:
        _resume = _df_bg.groupby("classe", as_index=False).agg(
            solde=("solde", "sum"),
            nb_comptes=("compte_numero", "nunique"),
        )
        _resume["classe_label"] = "Classe " + _resume["classe"].astype(str)
        _resume["solde"] = _resume["solde"].astype(float)

        _chart_classes = (
            alt.Chart(_resume)
            .mark_bar()
            .encode(
                x=alt.X("classe_label:N", title="", sort=None),
                y=alt.Y("solde:Q", title="Solde (€)", axis=alt.Axis(format=",.0f")),
                color=alt.Color(
                    "classe_label:N",
                    scale=alt.Scale(scheme="category10"),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("classe_label:N", title="Classe"),
                    alt.Tooltip("solde:Q", title="Solde", format=",.0f"),
                    alt.Tooltip("nb_comptes:Q", title="Nb comptes"),
                ],
            )
            .properties(
                title="Solde par classe comptable",
                height=300,
                width="container",
            )
        )

        # Resume par classe (agrege)
        _bg_agg = _df_bg.groupby(
            ["compte_numero", "compte_libelle", "classe"], as_index=False
        )["solde"].sum().sort_values("compte_numero")
        _bg_agg["solde"] = _bg_agg["solde"].astype(float)

        _table = mo.ui.table(
            _bg_agg,
            selection=None,
            pagination=True,
            page_size=20,
            format_mapping={"solde": lambda v: fmt(v)},
            label=f"{len(_bg_agg)} comptes",
        )

        _csv = _bg_agg.to_csv(index=False).encode("utf-8")
        _download = mo.download(
            data=_csv,
            filename=f"balance_{annee}.csv",
            mimetype="text/csv",
            label="Telecharger CSV",
        )

        bg_tab = mo.vstack(
            [
                mo.md(
                    f"### Balance generale — {_df_bg['compte_numero'].nunique()} comptes, "
                    f"{len(_df_bg)} lignes"
                ),
                mo.ui.altair_chart(_chart_classes),
                mo.md("### Detail par compte"),
                _download,
                _table,
            ],
            gap=1,
        )
    return (bg_tab,)


# ── PAGE 3 : GRAND LIVRE (filtre compte — creation) ─────────────

@app.cell(hide_code=True)
def _():
    gl_filtre_compte = mo.ui.text(
        value="",
        label="Filtre compte (ex: 411, 60)",
        placeholder="Numero de compte...",
        full_width=True,
    )
    return (gl_filtre_compte,)


# ── PAGE 3 : GRAND LIVRE (contenu) ──────────────────────────────

@app.cell(hide_code=True)
def _(annee, entite_id, gl_filtre_compte, mois_num):
    _compte = gl_filtre_compte.value.strip()
    _clauses = ["annee = %s"]
    _params_list = [annee]
    if entite_id:
        _clauses.insert(0, "entite_id = %s::uuid")
        _params_list.insert(0, entite_id)
    if _compte:
        _clauses.append("compte_numero LIKE %s")
        _params_list.append(f"{_compte}%")
    if mois_num:
        _clauses.append("mois = %s")
        _params_list.append(mois_num)

    _df_gl = db_query(f"""
        SELECT ecriture_date, journal_code, ecriture_num,
            compte_numero, compte_libelle, piece_ref, ecriture_lib,
            debit, credit, (debit - credit) AS solde
        FROM grand_livre
        WHERE {' AND '.join(_clauses)}
        ORDER BY ecriture_date DESC, ecriture_num
        LIMIT 500
    """, tuple(_params_list))

    if _df_gl.empty:
        _content = mo.callout("Aucune ecriture pour ce filtre.", kind="info")
    else:
        _df_gl["debit"] = _df_gl["debit"].astype(float)
        _df_gl["credit"] = _df_gl["credit"].astype(float)
        _df_gl["solde"] = _df_gl["solde"].astype(float)

        _table = mo.ui.table(
            _df_gl,
            selection=None,
            pagination=True,
            page_size=25,
            format_mapping={
                "debit": lambda v: fmt(v) if v else "",
                "credit": lambda v: fmt(v) if v else "",
                "solde": lambda v: fmt(v),
            },
            label=f"{len(_df_gl)} ecritures (limite 500)",
        )

        _csv = _df_gl.to_csv(index=False).encode("utf-8")
        _download = mo.download(
            data=_csv,
            filename=f"grand_livre_{annee}.csv",
            mimetype="text/csv",
            label="Telecharger CSV",
        )

        _content = mo.vstack([_download, _table], gap=0.5)

    gl_tab = mo.vstack([gl_filtre_compte, _content], gap=1)
    return (gl_tab,)


# ── PAGE 4 : CRD DETAILLE ───────────────────────────────────────

@app.cell(hide_code=True)
def _(annee, entite_id, mois_num, trim_num):
    _clauses = ["annee = %s"]
    _params_list = [annee]
    if entite_id:
        _clauses.insert(0, "entite_id = %s::uuid")
        _params_list.insert(0, entite_id)
    if trim_num:
        _clauses.append("trimestre = %s")
        _params_list.append(trim_num)
    if mois_num:
        _clauses.append("mois = %s")
        _params_list.append(mois_num)

    _df_drill = db_query(f"""
        SELECT crd_categorie, crd_rubrique, compte_numero, compte_libelle,
            SUM(montant) AS montant
        FROM v_crd_drilldown
        WHERE {' AND '.join(_clauses)}
        GROUP BY crd_categorie, crd_rubrique, compte_numero, compte_libelle
        ORDER BY crd_categorie, ABS(SUM(montant)) DESC
    """, tuple(_params_list))

    if _df_drill.empty:
        crd_tab = mo.callout("Aucune donnee CRD.", kind="info")
    else:
        _df_drill["montant"] = _df_drill["montant"].astype(float)

        # Vue agrege par categorie
        _cat_agg = _df_drill.groupby("crd_categorie", as_index=False)["montant"].sum()
        _cat_agg = _cat_agg.sort_values("montant", key=abs, ascending=False)

        _chart_cats = (
            alt.Chart(_cat_agg)
            .mark_bar()
            .encode(
                y=alt.Y("crd_categorie:N", sort="-x", title="Categorie"),
                x=alt.X("montant:Q", title="Montant (€)", axis=alt.Axis(format=",.0f")),
                color=alt.condition(
                    alt.datum.montant > 0,
                    alt.value("#38a169"),
                    alt.value("#e53e3e"),
                ),
                tooltip=[
                    alt.Tooltip("crd_categorie:N", title="Categorie"),
                    alt.Tooltip("montant:Q", title="Montant", format=",.0f"),
                ],
            )
            .properties(
                title="Montants par categorie CRD",
                height=320,
                width="container",
            )
        )

        _table = mo.ui.table(
            _df_drill,
            selection=None,
            pagination=True,
            page_size=20,
            format_mapping={"montant": lambda v: fmt(v)},
            label=f"{len(_df_drill)} lignes",
        )

        crd_tab = mo.vstack(
            [
                mo.md("### Montants par categorie"),
                mo.ui.altair_chart(_chart_cats),
                mo.md("### Detail par compte"),
                _table,
            ],
            gap=1,
        )
    return (crd_tab,)


# ── PAGE 5 : BILAN FONCTIONNEL ──────────────────────────────────

@app.cell(hide_code=True)
def _(annee, entite_id):
    _clauses_bf = ["annee = %s"]
    _params_bf = [annee]
    if entite_id:
        _clauses_bf.insert(0, "entite_id = %s::uuid")
        _params_bf.insert(0, entite_id)
    _df_bf = db_query(f"""
        SELECT bf_categorie, SUM(montant) AS montant
        FROM v_bilan_fonctionnel
        WHERE {' AND '.join(_clauses_bf)}
        GROUP BY bf_categorie
    """, tuple(_params_bf))

    if _df_bf.empty:
        bf_tab = mo.callout("Aucune donnee Bilan Fonctionnel.", kind="info")
    else:
        _bf = {r["bf_categorie"]: float(r["montant"]) for _, r in _df_bf.iterrows()}
        _frng = _bf.get("ressources_stables", 0) - _bf.get("emplois_stables", 0)
        _bfr = _bf.get("bfr_exploit", 0) + _bf.get("bfr_hors_exploit", 0)
        _tn = _bf.get("tresorerie_active", 0) - _bf.get("tresorerie_passive", 0)
        _ecart = abs(_frng - (_bfr + _tn))
        _ok = _ecart < 1

        _kpi = mo.hstack(
            [
                mo.stat(label="FRNG", value=fmt(_frng), caption="Ressources - Emplois stables", bordered=True),
                mo.stat(label="BFR", value=fmt(_bfr), caption="Besoin en fonds de roulement", bordered=True),
                mo.stat(label="Tresorerie Nette", value=fmt(_tn), caption="Actif - Passif circulant", bordered=True),
            ],
            widths="equal",
            gap=1,
        )

        _verif = (
            mo.callout(f"✓ FRNG = BFR + TN ({fmt(_frng)} = {fmt(_bfr)} + {fmt(_tn)})", kind="success")
            if _ok else
            mo.callout(f"✗ Equilibre : ecart de {fmt(_ecart)}", kind="warn")
        )

        _labels_bf = {
            "emplois_stables": "Emplois stables",
            "ressources_stables": "Ressources stables",
            "bfr_exploit": "BFR exploitation",
            "bfr_hors_exploit": "BFR hors exploitation",
            "tresorerie_active": "Tresorerie active",
            "tresorerie_passive": "Tresorerie passive",
        }

        _df_chart = pd.DataFrame([
            {"categorie": _labels_bf.get(k, k), "montant": float(v)}
            for k, v in _bf.items()
        ])

        _chart_bf = (
            alt.Chart(_df_chart)
            .mark_bar()
            .encode(
                y=alt.Y("categorie:N", sort="-x", title=""),
                x=alt.X("montant:Q", title="Montant (€)", axis=alt.Axis(format=",.0f")),
                color=alt.condition(
                    alt.datum.montant > 0,
                    alt.value("#2c5282"),
                    alt.value("#c53030"),
                ),
                tooltip=[
                    alt.Tooltip("categorie:N", title="Categorie"),
                    alt.Tooltip("montant:Q", title="Montant", format=",.0f"),
                ],
            )
            .properties(
                title="Structure du bilan fonctionnel",
                height=280,
                width="container",
            )
        )

        _clauses_dr = ["annee = %s", "bf_categorie IS NOT NULL"]
        _params_dr = [annee]
        if entite_id:
            _clauses_dr.insert(0, "entite_id = %s::uuid")
            _params_dr.insert(0, entite_id)
        _df_drill = db_query(f"""
            SELECT bf_categorie, compte_numero, compte_libelle,
                SUM(CASE
                    WHEN bf_categorie IN ('emplois_stables','bfr_exploit','bfr_hors_exploit','tresorerie_active')
                    THEN debit - credit ELSE credit - debit END) AS montant
            FROM grand_livre
            WHERE {' AND '.join(_clauses_dr)}
            GROUP BY bf_categorie, compte_numero, compte_libelle
            HAVING ABS(SUM(debit - credit)) > 0
            ORDER BY bf_categorie, ABS(SUM(debit - credit)) DESC
        """, tuple(_params_dr))

        if _df_drill.empty:
            _drill = mo.md("_Pas de detail disponible._")
        else:
            _df_drill["montant"] = _df_drill["montant"].astype(float)
            _drill = mo.ui.table(
                _df_drill,
                selection=None,
                pagination=True,
                page_size=20,
                format_mapping={"montant": lambda v: fmt(v)},
                label=f"{len(_df_drill)} comptes",
            )

        bf_tab = mo.vstack(
            [
                mo.md("### Indicateurs de structure financiere"),
                _kpi,
                _verif,
                mo.ui.altair_chart(_chart_bf),
                mo.md("### Detail par compte"),
                _drill,
            ],
            gap=1,
        )
    return (bf_tab,)


# ── PAGE 6 : SQL LIBRE (creation textarea) ──────────────────────

@app.cell(hide_code=True)
def _():
    sql_input = mo.ui.text_area(
        value=(
            "SELECT entite_nom, annee, COUNT(*) AS nb_ecritures\n"
            "FROM grand_livre\n"
            "GROUP BY entite_nom, annee\n"
            "ORDER BY entite_nom, annee"
        ),
        label="Requete SQL (lecture seule)",
        rows=8,
        full_width=True,
    )
    return (sql_input,)


# ── PAGE 6 : SQL LIBRE (execution) ──────────────────────────────

@app.cell(hide_code=True)
def _(sql_input):
    _sql = sql_input.value.strip()
    if not _sql:
        _result = mo.callout("Ecrivez une requete SQL ci-dessus.", kind="info")
    else:
        try:
            _df = db_query(_sql)
            if _df.empty:
                _result = mo.callout("Requete executee : 0 lignes.", kind="info")
            else:
                _table = mo.ui.table(_df, selection=None, pagination=True, page_size=25)
                _csv = _df.to_csv(index=False).encode("utf-8")
                _download = mo.download(
                    data=_csv,
                    filename="query_result.csv",
                    mimetype="text/csv",
                    label="Telecharger CSV",
                )
                _result = mo.vstack([
                    mo.md(f"**{len(_df)} lignes retournees**"),
                    _download,
                    _table,
                ], gap=0.5)
        except Exception as e:
            _result = mo.callout(f"**Erreur SQL** : `{e}`", kind="danger")

    sql_tab = mo.vstack([sql_input, _result], gap=1)
    return (sql_tab,)


# ── TABS (assemblage final) ─────────────────────────────────────

@app.cell(hide_code=True)
def _(bf_tab, bg_tab, crd_tab, gl_tab, overview_tab, sql_tab):
    mo.ui.tabs(
        {
            "Vue d'ensemble": overview_tab,
            "Balance Generale": bg_tab,
            "CRD detaille": crd_tab,
            "Bilan Fonctionnel": bf_tab,
            "Grand Livre": gl_tab,
            "SQL libre": sql_tab,
        },
    )
    return


if __name__ == "__main__":
    app.run()
