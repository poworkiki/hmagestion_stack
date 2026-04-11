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
    app_title="HMAnalytics",
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
    """Execute une requete SQL. Retourne un DataFrame pour SELECT, DF vide sinon."""
    _DB_URL = os.environ.get("HMA_DB_URL", "")
    with psycopg2.connect(_DB_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            # INSERT/UPDATE/DELETE sans RETURNING : cur.description est None
            if cur.description is None:
                return pd.DataFrame()
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
def _(annee_list):
    _default_year = str(annee_list[0]) if annee_list else "2026"
    get_years, set_years = mo.state([_default_year])
    get_months, set_months = mo.state([])
    return (get_months, get_years, set_months, set_years)


@app.cell(hide_code=True)
def _(annee_list, entite_map, get_months, get_years, set_months, set_years):
    filtre_structure = mo.ui.multiselect(
        options=list(entite_map.keys()),
        value=[],
        label="Structures (vide = Groupe)",
        full_width=True,
    )
    filtre_annee = mo.ui.multiselect(
        options=[str(a) for a in annee_list],
        value=get_years(),
        label="Exercices (multi)",
        full_width=True,
        on_change=set_years,
    )
    filtre_mois = mo.ui.multiselect(
        options=[
            "Jan", "Fev", "Mar", "Avr", "Mai", "Jun",
            "Jul", "Aou", "Sep", "Oct", "Nov", "Dec",
        ],
        value=get_months(),
        label="Mois (vide = tous)",
        full_width=True,
        on_change=set_months,
    )
    return (filtre_annee, filtre_mois, filtre_structure)


@app.cell(hide_code=True)
def _(set_months, set_years):
    _MOIS_LABELS = [
        "Jan", "Fev", "Mar", "Avr", "Mai", "Jun",
        "Jul", "Aou", "Sep", "Oct", "Nov", "Dec",
    ]

    def _activate_live(_v):
        _now = datetime.now(TZ_GUYANE)
        set_years([str(_now.year)])
        set_months([_MOIS_LABELS[_now.month - 1]])
        return True

    live_btn = mo.ui.button(
        label="🔴 Live — vue du jour",
        on_click=_activate_live,
        kind="danger",
    )
    return (live_btn,)


@app.cell(hide_code=True)
def _(filtre_annee, filtre_mois, filtre_structure, live_btn):
    _now = datetime.now(TZ_GUYANE)
    _date_str = f"{JOURS_FR[_now.weekday()]} {_now.day} {MOIS_FR[_now.month]} {_now.year}"
    _heure_str = _now.strftime("%H:%M")

    mo.sidebar(
        [
            mo.image("logo_hma.png", width=160, rounded=False),
            mo.md("<div style='text-align:center;font-weight:800;font-size:1.1rem;color:#2563eb;letter-spacing:-0.02em;margin-top:0.25rem;'>HMAnalytics</div>"),
            mo.md("---"),
            mo.md("### Filtres"),
            filtre_structure,
            filtre_annee,
            filtre_mois,
            mo.md("---"),
            live_btn,
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
        footer=mo.md("**HMA** · Gestion Guyane"),
    )
    return


# ── FILTRES (lecture des valeurs — cellule separee) ─────────────

@app.cell(hide_code=True)
def _(annee_list, entite_map, filtre_annee, filtre_mois, filtre_structure):
    _noms = filtre_structure.value or []
    is_groupe = (len(_noms) == 0)
    entite_ids = [entite_map[n] for n in _noms if n in entite_map]
    if is_groupe:
        entite_id = None
        entite_nom = "Groupe"
    elif len(_noms) == 1:
        entite_id = entite_ids[0]
        entite_nom = _noms[0]
    else:
        entite_id = entite_ids[0]
        entite_nom = " + ".join(_noms)

    _annees_raw = filtre_annee.value or []
    annees_sel = sorted([int(a) for a in _annees_raw], reverse=True)
    if not annees_sel:
        annees_sel = [annee_list[0]] if annee_list else [2026]
    _mois_map = {
        "Jan": 1, "Fev": 2, "Mar": 3, "Avr": 4, "Mai": 5, "Jun": 6,
        "Jul": 7, "Aou": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }
    mois_sel = [_mois_map[m] for m in (filtre_mois.value or []) if m in _mois_map]

    annee = annees_sel[0]
    annee_prev = annee - 1

    refresh_tick = (tuple(annees_sel), tuple(mois_sel), tuple(entite_ids))

    return (annee, annee_prev, annees_sel, entite_id, entite_ids, entite_nom, is_groupe, mois_sel, refresh_tick)


# ── PAGE 1 : VUE D'ENSEMBLE (KPI + trends) ──────────────────────

@app.function
def fetch_kpi_by_cat(annees_val, entite_ids_val, mois_val):
    """Agrege v_crd_drilldown par crd_categorie.
    annees_val : list d'entiers. entite_ids_val : list d'uuids (vide = toutes). mois_val : list d'ints 1-12.
    """
    if isinstance(annees_val, int):
        annees_val = [annees_val]
    _clauses = ["annee = ANY(%s)"]
    _p = [list(annees_val)]
    if entite_ids_val:
        _clauses.insert(0, "entite_id = ANY(%s::uuid[])")
        _p.insert(0, list(entite_ids_val))
    if mois_val:
        _clauses.append("mois = ANY(%s)")
        _p.append(list(mois_val))
    _df = db_query(f"""
        SELECT crd_categorie, SUM(montant) AS montant
        FROM v_crd_drilldown
        WHERE {' AND '.join(_clauses)}
        GROUP BY crd_categorie
    """, tuple(_p))
    _cats = {r["crd_categorie"]: float(r["montant"] or 0) for _, r in _df.iterrows()}
    ca = _cats.get("Chiffre d'affaires", 0)
    cv = _cats.get("Charges variables", 0)
    cf = _cats.get("Charges fixes exploitation", 0)
    rf = _cats.get("Resultat financier", 0)
    rex = _cats.get("Resultat exceptionnel", 0)
    is_ = _cats.get("Impot sur les societes", 0)
    mcv = ca - cv
    re_ = mcv - cf
    rcai = re_ + rf
    res_net = rcai + rex - is_
    # Charges totales : somme de toutes les sorties nettes
    charges_tot = cv + cf + is_ + max(0, -rf) + max(0, -rex)
    return {
        "ca": ca, "cv": cv, "cf": cf, "mcv": mcv,
        "rf": rf, "rex": rex, "is_": is_,
        "res_exp": re_, "rcai": rcai, "res_net": res_net,
        "charges_tot": charges_tot,
    }


@app.cell(hide_code=True)
def _(annee_prev, annees_sel, entite_ids, mois_sel, refresh_tick):
    _ = refresh_tick  # dependance pour forcer re-run sur bouton Live
    _n = fetch_kpi_by_cat(annees_sel, entite_ids, mois_sel)
    _p = fetch_kpi_by_cat([annee_prev], entite_ids, mois_sel)

    kpi_data = {
        "ca_n": _n["ca"], "mcv_n": _n["mcv"], "cv_n": _n["cv"], "cf_n": _n["cf"],
        "rf_n": _n["rf"], "rex_n": _n["rex"], "is_n": _n["is_"],
        "res_exp_n": _n["res_exp"], "res_net_n": _n["res_net"],
        "charges_tot_n": _n["charges_tot"],
        "ca_p": _p["ca"], "mcv_p": _p["mcv"],
        "res_net_p": _p["res_net"], "charges_tot_p": _p["charges_tot"],
    }
    return (kpi_data,)


@app.cell(hide_code=True)
def _(annee, annee_prev, entite_ids, refresh_tick):
    _ = refresh_tick

    def _tn_for(annee_val):
        _cl = ["annee = %s"]
        _p = [annee_val]
        if entite_ids:
            _cl.insert(0, "entite_id = ANY(%s::uuid[])")
            _p.insert(0, entite_ids)
        _df = db_query(
            f"SELECT "
            f"  SUM(CASE WHEN bf_categorie='tresorerie_active' THEN montant ELSE 0 END) "
            f"- SUM(CASE WHEN bf_categorie='tresorerie_passive' THEN montant ELSE 0 END) AS tn "
            f"FROM v_bilan_fonctionnel WHERE {' AND '.join(_cl)}",
            tuple(_p),
        )
        return float(_df.iloc[0]["tn"] or 0) if not _df.empty else 0.0

    _bf_n = {"tresorerie_active": _tn_for(annee), "tresorerie_passive": 0.0}
    _bf_p = {"tresorerie_active": _tn_for(annee_prev), "tresorerie_passive": 0.0}

    tn_overview = {
        "n": _bf_n["tresorerie_active"] - _bf_n["tresorerie_passive"],
        "p": _bf_p["tresorerie_active"] - _bf_p["tresorerie_passive"],
    }
    return (tn_overview,)


@app.cell(hide_code=True)
def _(annee, entite_ids, refresh_tick):
    _ = refresh_tick
    _clauses = ["annee = %s", "NOT is_a_nouveau"]
    _params = [annee]
    if entite_ids:
        _clauses.insert(0, "entite_id = ANY(%s::uuid[])")
        _params.insert(0, entite_ids)
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
def _(date_ref_str, kpi_data, tn_overview):
    def _stat_ytd(label, cur, prev, higher=True, caption_prefix="YTD"):
        d = delta_pct(cur, prev)
        caption = f"{caption_prefix} au {date_ref_str}" if date_ref_str else None
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
                _stat_ytd("Chiffre d'affaires",     kpi_data["ca_n"],          kpi_data["ca_p"]),
                _stat_ytd("Marge sur cout variable", kpi_data["mcv_n"],         kpi_data["mcv_p"]),
                _stat_ytd("Charges totales",        kpi_data["charges_tot_n"], kpi_data["charges_tot_p"], higher=False),
                _stat_ytd("Resultat net",           kpi_data["res_net_n"],     kpi_data["res_net_p"]),
                _stat_ytd("Tresorerie nette",       tn_overview["n"],          tn_overview["p"],
                          caption_prefix="à date"),
            ],
            widths="equal",
            gap=2,
        )
    return (kpi_row,)


# ── PAGE 1 : Donut CRD (decomposition du CA) ────────────────────

@app.cell(hide_code=True)
def _(kpi_data):
    # Donut : decomposition du CA en composantes CRD
    # Somme des tranches = CA. Chaque tranche = % du CA
    _ca = kpi_data["ca_n"]
    _items = [
        ("Charges variables",       kpi_data["cv_n"],           "#ef4444"),
        ("Charges fixes",           kpi_data["cf_n"],           "#f97316"),
    ]
    if kpi_data["rf_n"] < 0:
        _items.append(("Charges financieres", abs(kpi_data["rf_n"]), "#06b6d4"))
    if kpi_data["rex_n"] < 0:
        _items.append(("Charges exceptionnelles", abs(kpi_data["rex_n"]), "#64748b"))
    if kpi_data["is_n"] > 0:
        _items.append(("Impot sur les societes", kpi_data["is_n"], "#a855f7"))

    # Resultat net = ce qui reste du CA
    _res_net = kpi_data["res_net_n"]
    if _res_net > 0:
        _items.append(("Resultat net", _res_net, "#22c55e"))
    elif _res_net < 0:
        _items.append(("Perte nette", abs(_res_net), "#991b1b"))

    # Produits financiers / exceptionnels positifs : tranche speciale "produits hors expl."
    _produits_hors = max(0, kpi_data["rf_n"]) + max(0, kpi_data["rex_n"])
    if _produits_hors > 0:
        _items.append(("Produits hors exploitation", _produits_hors, "#8b5cf6"))

    _items = [(lib, val, col) for (lib, val, col) in _items if val > 0]

    if not _items or _ca == 0:
        charges_donut = mo.md("_Pas de donnees CRD a afficher._")
    else:
        _df = pd.DataFrame([
            {"categorie": lib, "montant": float(val), "couleur": col}
            for lib, val, col in _items
        ])
        _total = _df["montant"].sum()
        _df["pct"] = _df["montant"] / _total

        _chart = (
            alt.Chart(_df)
            .mark_arc(innerRadius=75, outerRadius=120, stroke="#fff", strokeWidth=2)
            .encode(
                theta=alt.Theta("montant:Q", stack=True),
                color=alt.Color(
                    "categorie:N",
                    scale=alt.Scale(
                        domain=_df["categorie"].tolist(),
                        range=_df["couleur"].tolist(),
                    ),
                    legend=alt.Legend(title="", orient="right"),
                ),
                tooltip=[
                    alt.Tooltip("categorie:N", title="Composante"),
                    alt.Tooltip("montant:Q", title="Montant", format=",.0f"),
                    alt.Tooltip("pct:Q", title="% du CA", format=".1%"),
                ],
            )
            .properties(
                title=f"Decomposition du CA ({fmt(_ca)})",
                height=320,
                width=320,
            )
        )
        charges_donut = _chart
    return (charges_donut,)


@app.cell(hide_code=True)
def _(kpi_data):
    # Structure du resultat : CA | Charges totales | Resultat net (horizontal bars)
    _ca = kpi_data["ca_n"]
    _charges = kpi_data["charges_tot_n"]
    _res = kpi_data["res_net_n"]

    if _ca == 0:
        structure_chart = mo.md("_Pas de donnees._")
    else:
        _df = pd.DataFrame([
            {"poste": "Chiffre d'affaires", "montant": float(_ca),      "type": "produit", "ordre": 1},
            {"poste": "Charges totales",    "montant": float(_charges), "type": "charge",  "ordre": 2},
            {"poste": "Resultat net",       "montant": float(_res),     "type": "resultat","ordre": 3},
        ])
        _chart = (
            alt.Chart(_df)
            .mark_bar(cornerRadiusEnd=4, size=45)
            .encode(
                y=alt.Y("poste:N", sort=alt.SortField("ordre"), title="",
                        axis=alt.Axis(labelFontSize=13)),
                x=alt.X("montant:Q", title="Montant (€)", axis=alt.Axis(format=",.0f")),
                color=alt.Color(
                    "type:N",
                    scale=alt.Scale(
                        domain=["produit", "charge", "resultat"],
                        range=["#22c55e", "#ef4444", "#3b82f6"],
                    ),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("poste:N",    title="Poste"),
                    alt.Tooltip("montant:Q",  title="Montant", format=",.0f"),
                ],
            )
            .properties(title="Structure du compte de resultat", height=320, width="container")
        )
        structure_chart = _chart
    return (structure_chart,)


# ── PAGE 1 : Evolution mensuelle (Altair) ───────────────────────

@app.cell(hide_code=True)
def _(annee, entite_ids, refresh_tick):
    _ = refresh_tick
    _clauses = ["annee = %s", "NOT is_a_nouveau", "classe IN (6, 7)"]
    _params = [annee]
    if entite_ids:
        _clauses.insert(0, "entite_id = ANY(%s::uuid[])")
        _params.insert(0, entite_ids)
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
        evolution_chart = _chart
    return (evolution_chart,)


# ── PAGE 1 : Assemblage ─────────────────────────────────────────

@app.cell(hide_code=True)
def _(charges_donut, evolution_chart, kpi_row, structure_chart):
    overview_tab = mo.vstack(
        [
            mo.md("### Indicateurs cles"),
            kpi_row,
            mo.md("### Structure et repartition"),
            mo.hstack(
                [charges_donut, structure_chart],
                widths="equal",
                gap=2,
                align="start",
            ),
            mo.md("### Evolution mensuelle"),
            evolution_chart,
        ],
        gap=2,
    )
    return (overview_tab,)


# ── PAGE 2 : CRD REEL (tableau + waterfall + drilldown) ─────────

@app.cell(hide_code=True)
def _(annee_prev, annees_sel, entite_ids, mois_sel, refresh_tick):
    _ = refresh_tick
    def _build(_annees):
        _k = fetch_kpi_by_cat(_annees, entite_ids, mois_sel)
        return {
            "ca":   _k["ca"],
            "cv":   _k["cv"],
            "mcv":  _k["mcv"],
            "cf":   _k["cf"],
            "re":   _k["res_exp"],
            "rf":   _k["rf"],
            "rcai": _k["rcai"],
            "rex":  _k["rex"],
            "is_":  _k["is_"],
            "rn":   _k["res_net"],
            "caf":  _k["res_net"],
        }

    crd_n = _build(annees_sel)
    crd_p = _build([annee_prev])
    return (crd_n, crd_p)


@app.cell(hide_code=True)
def _(crd_n, crd_p):
    def _evol(n, p):
        if p is None or p == 0:
            return None
        return (n - p) / abs(p)

    # Structure du CRD : ordre, libelle, reel_n, reel_p, type (total/revenu/charge), pct du CA
    _ca_n = crd_n["ca"] or 1
    _rows = [
        (1.0, "Chiffre d'affaires",           crd_n["ca"],   crd_p["ca"],   "total"),
        (2.0, "− Charges variables",          -crd_n["cv"],  -crd_p["cv"],  "charge"),
        (2.5, "= Marge sur coût variable",    crd_n["mcv"],  crd_p["mcv"],  "solde"),
        (3.0, "− Charges fixes",              -crd_n["cf"],  -crd_p["cf"],  "charge"),
        (3.5, "= Résultat d'exploitation",    crd_n["re"],   crd_p["re"],   "solde"),
        (4.0, "± Résultat financier",         crd_n["rf"],   crd_p["rf"],   "neutre"),
        (4.5, "= Résultat courant avant IS",  crd_n["rcai"], crd_p["rcai"], "solde"),
        (5.0, "± Résultat exceptionnel",      crd_n["rex"],  crd_p["rex"],  "neutre"),
        (6.0, "− Impôt sur les sociétés",     -crd_n["is_"], -crd_p["is_"], "charge"),
        (7.0, "= Résultat net",               crd_n["rn"],   crd_p["rn"],   "solde_final"),
        (8.0, "+ CAF",                        crd_n["caf"],  crd_p["caf"],  "total"),
    ]

    _tbl = pd.DataFrame([
        {
            "Ordre":    o,
            "Libellé":  lib,
            "Réel":     reel,
            "% CA":     (reel / _ca_n) if _ca_n else None,
            "N-1":      n1,
            "Évol %":   _evol(reel, n1),
            "_type":    typ,
        }
        for (o, lib, reel, n1, typ) in _rows
    ])

    def _fmt_val(v):
        if v is None or pd.isna(v):
            return ""
        return fmt(v)

    def _fmt_pct(v):
        if v is None or pd.isna(v):
            return ""
        return f"{v:+.1%}"

    _types_by_idx = _tbl["_type"].to_dict()
    _tbl_display = _tbl.drop(columns=["_type"])
    _ncols = len(_tbl_display.columns)

    def _style_row(row):
        t = _types_by_idx.get(row.name, "")
        if t == "solde_final":
            return ["background-color: #1e40af; color: white; font-weight: 700"] * _ncols
        if t == "solde":
            return ["background-color: #dbeafe; color: #1e3a8a; font-weight: 600"] * _ncols
        if t == "charge":
            return ["color: #b91c1c"] * _ncols
        return [""] * _ncols

    _styler = (
        _tbl_display
        .style
        .format({
            "Réel":   _fmt_val,
            "N-1":    _fmt_val,
            "% CA":   _fmt_pct,
            "Évol %": _fmt_pct,
            "Ordre":  lambda v: f"{v:.1f}",
        })
        .apply(_style_row, axis=1)
        .hide(axis="index")
    )
    crd_tbl_html = mo.Html(_styler.to_html())
    return (crd_tbl_html,)


@app.cell(hide_code=True)
def _(crd_n):
    # Waterfall CA → MCV → RE → RCAI → RN (Altair)
    _steps = [
        ("CA",          0,                                   crd_n["ca"],   "total"),
        ("− Ch. var.",  crd_n["mcv"],                        crd_n["ca"],   "neg"),
        ("MCV",         0,                                   crd_n["mcv"],  "total"),
        ("− Ch. fixes", crd_n["re"],                         crd_n["mcv"],  "neg"),
        ("Rés. expl.",  0,                                   crd_n["re"],   "total"),
        ("± Fin.",      min(crd_n["re"], crd_n["rcai"]),     max(crd_n["re"], crd_n["rcai"]), "pos" if crd_n["rf"] >= 0 else "neg"),
        ("RCAI",        0,                                   crd_n["rcai"], "total"),
        ("± Except.",   min(crd_n["rcai"], crd_n["rcai"] + crd_n["rex"]),   max(crd_n["rcai"], crd_n["rcai"] + crd_n["rex"]), "pos" if crd_n["rex"] >= 0 else "neg"),
        ("− IS",        crd_n["rn"],                         crd_n["rcai"] + crd_n["rex"], "neg"),
        ("Rés. net",    0,                                   crd_n["rn"],   "total"),
    ]
    _df_wf = pd.DataFrame([
        {"step": i, "label": lab, "start": float(start), "end": float(end), "type": typ}
        for i, (lab, start, end, typ) in enumerate(_steps)
    ])

    if crd_n["ca"] == 0:
        crd_waterfall = mo.md("_Pas de donnees pour le waterfall._")
    else:
        _chart = (
            alt.Chart(_df_wf)
            .mark_bar(size=40)
            .encode(
                x=alt.X("label:N", sort=None, title="", axis=alt.Axis(labelAngle=-20)),
                y=alt.Y("start:Q", title="Montant (€)", axis=alt.Axis(format=",.0f")),
                y2="end:Q",
                color=alt.Color(
                    "type:N",
                    scale=alt.Scale(
                        domain=["total", "neg", "pos"],
                        range=["#1e40af", "#dc2626", "#16a34a"],
                    ),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("label:N", title="Étape"),
                    alt.Tooltip("start:Q", title="Début", format=",.0f"),
                    alt.Tooltip("end:Q", title="Fin", format=",.0f"),
                ],
            )
            .properties(title="Formation du résultat net", height=360, width="container")
        )
        crd_waterfall = _chart
    return (crd_waterfall,)


@app.cell(hide_code=True)
def _():
    crd_drill_cat = mo.ui.dropdown(
        options=[
            "(aucun)",
            "Chiffre d'affaires",
            "Charges variables",
            "Charges fixes exploitation",
            "Resultat financier",
            "Resultat exceptionnel",
            "Impot sur les societes",
        ],
        value="(aucun)",
        label="Drilldown catégorie",
        full_width=True,
    )
    return (crd_drill_cat,)


@app.cell(hide_code=True)
def _(annees_sel, crd_drill_cat, entite_ids, mois_sel, refresh_tick):
    _ = refresh_tick
    if crd_drill_cat.value == "(aucun)":
        crd_drill = mo.md("_Sélectionnez une catégorie ci-dessus pour voir les comptes PCG détaillés._")
    else:
        _clauses = ["annee = ANY(%s)", "crd_categorie = %s"]
        _params = [list(annees_sel), crd_drill_cat.value]
        if entite_ids:
            _clauses.insert(0, "entite_id = ANY(%s::uuid[])")
            _params.insert(0, entite_ids)
        if mois_sel:
            _clauses.append("mois = ANY(%s)")
            _params.append(list(mois_sel))
        _df = db_query(f"""
            SELECT compte_numero, compte_libelle, crd_rubrique,
                   SUM(montant) AS montant
            FROM v_crd_drilldown
            WHERE {' AND '.join(_clauses)}
            GROUP BY compte_numero, compte_libelle, crd_rubrique
            ORDER BY ABS(SUM(montant)) DESC
        """, tuple(_params))
        if _df.empty:
            crd_drill = mo.callout("Aucun compte trouvé pour cette catégorie.", kind="info")
        else:
            _df["montant"] = _df["montant"].astype(float)
            crd_drill = mo.ui.table(
                _df, selection=None, pagination=True, page_size=15,
                format_mapping={"montant": lambda v: fmt(v)},
                label=f"{len(_df)} comptes · {crd_drill_cat.value}",
            )
    return (crd_drill,)


@app.cell(hide_code=True)
def _(crd_drill, crd_drill_cat, crd_tbl_html, crd_waterfall, date_ref_str):
    crd_tab = mo.vstack(
        [
            mo.md(f"### Compte de Résultat Différentiel — Réel" + (f" · au {date_ref_str}" if date_ref_str else "")),
            crd_tbl_html,
            mo.md("### Formation du résultat"),
            crd_waterfall,
            mo.md("### Drilldown par catégorie"),
            crd_drill_cat,
            crd_drill,
        ],
        gap=1,
    )
    return (crd_tab,)


# ── PAGE 3 : BILAN FONCTIONNEL (refait avec drilldown) ──────────

@app.function
def bf_fetch(annee_val, entite_ids_val):
    """entite_ids_val : liste d'uuids (vide = toutes les entites)."""
    if isinstance(entite_ids_val, str):
        entite_ids_val = [entite_ids_val]
    _clauses = ["annee = %s"]
    _params = [annee_val]
    if entite_ids_val:
        _clauses.insert(0, "entite_id = ANY(%s::uuid[])")
        _params.insert(0, list(entite_ids_val))
    _df = db_query(
        f"SELECT bf_categorie, SUM(montant) AS montant "
        f"FROM v_bilan_fonctionnel WHERE {' AND '.join(_clauses)} "
        f"GROUP BY bf_categorie",
        tuple(_params),
    )
    out = {
        "emplois_stables": 0.0, "ressources_stables": 0.0,
        "bfr_exploit": 0.0, "bfr_hors_exploit": 0.0,
        "tresorerie_active": 0.0, "tresorerie_passive": 0.0,
    }
    for _, r in _df.iterrows():
        out[r["bf_categorie"]] = float(r["montant"] or 0)
    return out


@app.cell(hide_code=True)
def _(annee, annee_prev, entite_ids, refresh_tick):
    _ = refresh_tick
    bf_n = bf_fetch(annee, entite_ids)
    bf_p = bf_fetch(annee_prev, entite_ids)
    return (bf_n, bf_p)


@app.cell(hide_code=True)
def _(bf_n, bf_p):
    frng_n = bf_n["ressources_stables"] - bf_n["emplois_stables"]
    bfr_n  = bf_n["bfr_exploit"] + bf_n["bfr_hors_exploit"]
    tn_n   = bf_n["tresorerie_active"] - bf_n["tresorerie_passive"]
    frng_p = bf_p["ressources_stables"] - bf_p["emplois_stables"]
    bfr_p  = bf_p["bfr_exploit"] + bf_p["bfr_hors_exploit"]
    tn_p   = bf_p["tresorerie_active"] - bf_p["tresorerie_passive"]

    ecart = abs(frng_n - (bfr_n + tn_n))
    equilibre_ok = ecart < 1

    def _kstat(label, cur, prev, caption_static):
        d = delta_pct(cur, prev)
        if d is None:
            return mo.stat(label=label, value=fmt(cur), caption=caption_static, bordered=True)
        return mo.stat(
            label=label, value=fmt(cur),
            caption=f"{caption_static} · {d:+.1%} vs N-1",
            direction="increase" if d >= 0 else "decrease",
            bordered=True,
        )

    bf_kpi = mo.hstack(
        [
            _kstat("FRNG", frng_n, frng_p, "Ressources − Emplois stables"),
            _kstat("BFR",  bfr_n,  bfr_p,  "Besoin en fonds de roulement"),
            _kstat("Trésorerie Nette", tn_n, tn_p, "Actif − Passif circulant"),
        ],
        widths="equal",
        gap=1,
    )

    bf_verif = (
        mo.callout(
            f"✓ Équilibre vérifié : FRNG ({fmt(frng_n)}) = BFR ({fmt(bfr_n)}) + TN ({fmt(tn_n)})",
            kind="success",
        )
        if equilibre_ok else
        mo.callout(f"✗ Déséquilibre : écart de {fmt(ecart)} entre FRNG et BFR+TN", kind="warn")
    )
    return (bf_kpi, bf_verif, bfr_n, frng_n, tn_n)


@app.cell(hide_code=True)
def _(bf_n):
    # Tableau structure EMPLOIS | RESSOURCES (format bilan classique)
    _emplois = [
        ("Emplois stables",       bf_n["emplois_stables"],  "stable"),
        ("BFR exploitation",      bf_n["bfr_exploit"],      "bfr"),
        ("BFR hors exploitation", bf_n["bfr_hors_exploit"], "bfr"),
        ("Trésorerie active",     bf_n["tresorerie_active"], "treso"),
    ]
    _ressources = [
        ("Ressources stables",    bf_n["ressources_stables"], "stable"),
        ("Trésorerie passive",    bf_n["tresorerie_passive"], "treso"),
        ("", 0, ""),
        ("", 0, ""),
    ]
    _total_e = sum(v for _, v, _ in _emplois)
    _total_r = sum(v for _, v, _ in _ressources)

    _rows = []
    for (le, ve, te), (lr, vr, tr) in zip(_emplois, _ressources):
        _rows.append({
            "Emplois": le, "Montant E": ve if le else None,
            "Ressources": lr, "Montant R": vr if lr else None,
            "_type_e": te, "_type_r": tr,
        })
    _rows.append({
        "Emplois": "TOTAL EMPLOIS", "Montant E": _total_e,
        "Ressources": "TOTAL RESSOURCES", "Montant R": _total_r,
        "_type_e": "total", "_type_r": "total",
    })
    _df = pd.DataFrame(_rows)
    _types_e = _df["_type_e"].tolist()
    _types_r = _df["_type_r"].tolist()
    _display = _df.drop(columns=["_type_e", "_type_r"])

    def _fmt_amount(v):
        if v is None or pd.isna(v):
            return ""
        return fmt(v)

    def _color_row(row):
        idx = row.name
        te, tr = _types_e[idx], _types_r[idx]
        styles = []
        for col in _display.columns:
            if col in ("Emplois", "Montant E"):
                t = te
            else:
                t = tr
            if t == "total":
                styles.append("background-color: #1e40af; color: white; font-weight: 700")
            elif t == "stable":
                styles.append("background-color: #dbeafe; color: #1e3a8a; font-weight: 600")
            elif t == "treso":
                styles.append("background-color: #fef3c7; color: #92400e")
            elif t == "bfr":
                styles.append("background-color: #f3e8ff; color: #6b21a8")
            else:
                styles.append("")
        return styles

    _styler = (
        _display.style
        .format({"Montant E": _fmt_amount, "Montant R": _fmt_amount})
        .apply(_color_row, axis=1)
        .hide(axis="index")
    )
    bf_table_html = mo.Html(_styler.to_html())
    return (bf_table_html,)


@app.cell(hide_code=True)
def _(bf_n):
    _labels = {
        "emplois_stables":   ("Emplois stables",       "emplois"),
        "bfr_exploit":       ("BFR exploitation",      "emplois"),
        "bfr_hors_exploit":  ("BFR hors exploitation", "emplois"),
        "tresorerie_active": ("Trésorerie active",     "emplois"),
        "ressources_stables":("Ressources stables",    "ressources"),
        "tresorerie_passive":("Trésorerie passive",    "ressources"),
    }
    _rows = []
    for k, (label, cote) in _labels.items():
        val = bf_n.get(k, 0)
        if val == 0:
            continue
        _rows.append({"categorie": label, "montant": float(val), "cote": cote})
    if not _rows:
        bf_chart = mo.md("_Pas de donnees._")
    else:
        _df = pd.DataFrame(_rows)
        _chart = (
            alt.Chart(_df)
            .mark_bar()
            .encode(
                y=alt.Y("cote:N", title="", axis=alt.Axis(labelAngle=0)),
                x=alt.X("montant:Q", title="Montant (€)", axis=alt.Axis(format=",.0f"), stack="zero"),
                color=alt.Color(
                    "categorie:N",
                    scale=alt.Scale(scheme="tableau10"),
                    legend=alt.Legend(title="", orient="bottom", columns=3),
                ),
                tooltip=[
                    alt.Tooltip("categorie:N", title="Catégorie"),
                    alt.Tooltip("montant:Q", title="Montant", format=",.0f"),
                ],
            )
            .properties(title="Structure fonctionnelle — Emplois vs Ressources", height=260, width="container")
        )
        bf_chart = _chart
    return (bf_chart,)


@app.cell(hide_code=True)
def _():
    bf_drill_cat = mo.ui.dropdown(
        options=[
            "(aucun)",
            "emplois_stables",
            "ressources_stables",
            "bfr_exploit",
            "bfr_hors_exploit",
            "tresorerie_active",
            "tresorerie_passive",
        ],
        value="(aucun)",
        label="Drilldown catégorie BF",
        full_width=True,
    )
    return (bf_drill_cat,)


@app.cell(hide_code=True)
def _(annee, bf_drill_cat, entite_ids, refresh_tick):
    _ = refresh_tick
    if bf_drill_cat.value == "(aucun)":
        bf_drill = mo.md("_Sélectionnez une catégorie ci-dessus pour voir les comptes PCG détaillés._")
    else:
        _is_emplois = bf_drill_cat.value in (
            "emplois_stables", "bfr_exploit", "bfr_hors_exploit", "tresorerie_active"
        )
        _sens = "debit - credit" if _is_emplois else "credit - debit"
        _clauses = ["annee = %s", "bf_categorie = %s"]
        _params = [annee, bf_drill_cat.value]
        if entite_ids:
            _clauses.insert(0, "entite_id = ANY(%s::uuid[])")
            _params.insert(0, entite_ids)
        _df = db_query(f"""
            SELECT compte_numero, compte_libelle,
                   SUM({_sens}) AS montant,
                   COUNT(*) AS nb_ecritures
            FROM grand_livre
            WHERE {' AND '.join(_clauses)}
            GROUP BY compte_numero, compte_libelle
            HAVING ABS(SUM({_sens})) > 0
            ORDER BY ABS(SUM({_sens})) DESC
        """, tuple(_params))
        if _df.empty:
            bf_drill = mo.callout("Aucun compte dans cette catégorie.", kind="info")
        else:
            _df["montant"] = _df["montant"].astype(float)
            bf_drill = mo.ui.table(
                _df, selection=None, pagination=True, page_size=15,
                format_mapping={"montant": lambda v: fmt(v)},
                label=f"{len(_df)} comptes · {bf_drill_cat.value}",
            )
    return (bf_drill,)


@app.cell(hide_code=True)
def _(bf_chart, bf_drill, bf_drill_cat, bf_kpi, bf_table_html, bf_verif, date_ref_str):
    bf_tab = mo.vstack(
        [
            mo.md(f"### Bilan Fonctionnel" + (f" · au {date_ref_str}" if date_ref_str else "")),
            bf_kpi,
            bf_verif,
            mo.md("### Structure Emplois / Ressources"),
            bf_table_html,
            bf_chart,
            mo.md("### Drilldown par catégorie"),
            bf_drill_cat,
            bf_drill,
        ],
        gap=1,
    )
    return (bf_tab,)


# ── PAGE 4 : BUDGET CRD ─────────────────────────────────────────

@app.function
def budget_get_or_create_scenario(entite_id_val, annee_val):
    """Retourne l'id du scenario 'Central {annee}' pour l'entite, le cree si absent."""
    if not entite_id_val:
        return None
    _nom = f"Central {annee_val}"
    _df = db_query(
        "SELECT id FROM budget_scenario WHERE entite_id = %s::uuid AND annee = %s AND nom = %s",
        (entite_id_val, annee_val, _nom),
    )
    if not _df.empty:
        return str(_df.iloc[0]["id"])
    # Creation
    _df = db_query(
        """INSERT INTO budget_scenario (entite_id, annee, nom, description, annee_reference)
           VALUES (%s::uuid, %s, %s, %s, %s)
           RETURNING id""",
        (entite_id_val, annee_val, _nom, "Scenario central par defaut", annee_val - 1),
    )
    _sid = str(_df.iloc[0]["id"])
    db_query(
        "INSERT INTO budget_regle_globale (scenario_id) VALUES (%s::uuid) ON CONFLICT DO NOTHING",
        (_sid,),
    )
    return _sid


@app.function
def budget_load_regle_globale(scenario_id_val):
    if not scenario_id_val:
        return (10.0, 5.0)
    _df = db_query(
        "SELECT taux_revenus, taux_charges FROM budget_regle_globale WHERE scenario_id = %s::uuid",
        (scenario_id_val,),
    )
    if _df.empty:
        return (10.0, 5.0)
    return (float(_df.iloc[0]["taux_revenus"]), float(_df.iloc[0]["taux_charges"]))


@app.cell(hide_code=True)
def _(annee, entite_id, is_groupe, refresh_tick):
    _ = refresh_tick
    if is_groupe:
        budget_scenario_id = None
        budget_taux_init = (10.0, 5.0)
    else:
        budget_scenario_id = budget_get_or_create_scenario(entite_id, annee)
        budget_taux_init = budget_load_regle_globale(budget_scenario_id)
    return (budget_scenario_id, budget_taux_init)


@app.cell(hide_code=True)
def _(budget_taux_init):
    budget_slider_revenus = mo.ui.slider(
        start=-20, stop=50, step=1,
        value=int(budget_taux_init[0]),
        label="Taux revenus (%)",
        show_value=True,
        full_width=True,
    )
    budget_slider_charges = mo.ui.slider(
        start=-20, stop=50, step=1,
        value=int(budget_taux_init[1]),
        label="Taux charges (%)",
        show_value=True,
        full_width=True,
    )
    return (budget_slider_charges, budget_slider_revenus)


@app.cell(hide_code=True)
def _(annee, annee_prev, entite_id, is_groupe, refresh_tick):
    _ = refresh_tick
    # Donnees reelles N-1 agregees par categorie CRD
    if is_groupe or not entite_id:
        budget_reel_cats = {}
    else:
        _df = db_query("""
            SELECT crd_ordre, crd_categorie, SUM(montant) AS montant
            FROM v_crd_drilldown
            WHERE entite_id = %s::uuid AND annee = %s
            GROUP BY crd_ordre, crd_categorie
            ORDER BY crd_ordre
        """, (entite_id, annee_prev))
        budget_reel_cats = {
            r["crd_categorie"]: float(r["montant"] or 0)
            for _, r in _df.iterrows()
        }
    return (budget_reel_cats,)


@app.cell(hide_code=True)
def _(budget_reel_cats, budget_slider_charges, budget_slider_revenus, is_groupe):
    # Calcul in-memory : applique le taux sur chaque categorie
    # Revenus = categorie "Chiffre d'affaires" (classe 7)
    # Charges = tout le reste (classes 6 + resultats mixtes)
    _revenus_cats = {"Chiffre d'affaires"}
    taux_rev = budget_slider_revenus.value / 100.0
    taux_chg = budget_slider_charges.value / 100.0

    ca_reel   = budget_reel_cats.get("Chiffre d'affaires", 0)
    cv_reel   = budget_reel_cats.get("Charges variables", 0)
    cf_reel   = budget_reel_cats.get("Charges fixes exploitation", 0)
    rf_reel   = budget_reel_cats.get("Resultat financier", 0)
    rex_reel  = budget_reel_cats.get("Resultat exceptionnel", 0)
    is_reel   = budget_reel_cats.get("Impot sur les societes", 0)

    # Budget projete
    ca_bdg  = ca_reel  * (1 + taux_rev)
    cv_bdg  = cv_reel  * (1 + taux_chg)
    cf_bdg  = cf_reel  * (1 + taux_chg)
    rf_bdg  = rf_reel  * (1 + taux_rev if rf_reel >= 0 else 1 + taux_chg)
    rex_bdg = rex_reel * (1 + taux_rev if rex_reel >= 0 else 1 + taux_chg)
    is_bdg  = is_reel  * (1 + taux_chg)

    # Soldes
    mcv_reel  = ca_reel - cv_reel
    mcv_bdg   = ca_bdg - cv_bdg
    re_reel   = mcv_reel - cf_reel
    re_bdg    = mcv_bdg - cf_bdg
    rcai_reel = re_reel + rf_reel
    rcai_bdg  = re_bdg  + rf_bdg
    rn_reel   = rcai_reel + rex_reel - is_reel
    rn_bdg    = rcai_bdg  + rex_bdg  - is_bdg

    budget_calc = dict(
        ca=(ca_reel, ca_bdg), cv=(cv_reel, cv_bdg), mcv=(mcv_reel, mcv_bdg),
        cf=(cf_reel, cf_bdg), re=(re_reel, re_bdg), rf=(rf_reel, rf_bdg),
        rcai=(rcai_reel, rcai_bdg), rex=(rex_reel, rex_bdg),
        is_=(is_reel, is_bdg), rn=(rn_reel, rn_bdg),
    )
    return (budget_calc,)


@app.cell(hide_code=True)
def _(budget_calc):
    def _ecart_pct(b, r):
        if r == 0:
            return None
        return (b - r) / abs(r)

    _ca_bdg = budget_calc["ca"][1] or 1
    _rows_def = [
        (1.0, "Chiffre d'affaires",            "ca",   "total"),
        (2.0, "− Charges variables",           "cv",   "charge"),
        (2.5, "= Marge sur coût variable",     "mcv",  "solde"),
        (3.0, "− Charges fixes",               "cf",   "charge"),
        (3.5, "= Résultat d'exploitation",     "re",   "solde"),
        (4.0, "± Résultat financier",          "rf",   "neutre"),
        (4.5, "= Résultat courant avant IS",   "rcai", "solde"),
        (5.0, "± Résultat exceptionnel",       "rex",  "neutre"),
        (6.0, "− Impôt sur les sociétés",      "is_",  "charge"),
        (7.0, "= Résultat net",                "rn",   "solde_final"),
    ]
    _rows = []
    for (_o, _lib, _k, _typ) in _rows_def:
        _reel, _bdg = budget_calc[_k]
        if _typ == "charge":
            _reel_aff, _bdg_aff = -_reel, -_bdg
        else:
            _reel_aff, _bdg_aff = _reel, _bdg
        _rows.append({
            "Ordre":   _o,
            "Libellé": _lib,
            "Réel N-1": _reel_aff,
            "Budget N": _bdg_aff,
            "Écart €": _bdg_aff - _reel_aff,
            "Écart %": _ecart_pct(_bdg, _reel),
            "% CA":    (_bdg_aff / _ca_bdg) if _ca_bdg else None,
            "_type":   _typ,
        })

    _tbl = pd.DataFrame(_rows)
    _types_by_idx = _tbl["_type"].to_dict()
    _display = _tbl.drop(columns=["_type"])
    _ncols = len(_display.columns)

    def _fmt_v(v):
        if v is None or pd.isna(v):
            return ""
        return fmt(v)

    def _fmt_p(v):
        if v is None or pd.isna(v):
            return ""
        return f"{v:+.1%}"

    def _style(row):
        t = _types_by_idx.get(row.name, "")
        if t == "solde_final":
            return ["background-color: #1e40af; color: white; font-weight: 700"] * _ncols
        if t == "solde":
            return ["background-color: #dbeafe; color: #1e3a8a; font-weight: 600"] * _ncols
        if t == "charge":
            return ["color: #b91c1c"] * _ncols
        return [""] * _ncols

    _styler = (
        _display.style
        .format({
            "Réel N-1": _fmt_v, "Budget N": _fmt_v, "Écart €": _fmt_v,
            "Écart %": _fmt_p, "% CA": _fmt_p,
            "Ordre":   lambda v: f"{v:.1f}",
        })
        .apply(_style, axis=1)
        .hide(axis="index")
    )
    budget_tbl_html = mo.Html(_styler.to_html())
    return (budget_tbl_html,)


@app.cell(hide_code=True)
def _(budget_calc):
    # Waterfall compare Reel N-1 vs Budget N sur les soldes cles
    _rows = []
    for _k, _lbl in [("ca", "CA"), ("mcv", "MCV"), ("re", "Rés. expl."),
                     ("rcai", "RCAI"), ("rn", "Rés. net")]:
        _reel, _bdg = budget_calc[_k]
        _rows.append({"poste": _lbl, "type": "Réel N-1", "montant": float(_reel)})
        _rows.append({"poste": _lbl, "type": "Budget N", "montant": float(_bdg)})
    _df = pd.DataFrame(_rows)

    if budget_calc["ca"][0] == 0 and budget_calc["ca"][1] == 0:
        budget_chart = mo.md("_Pas de donnees pour le graphique._")
    else:
        _chart = (
            alt.Chart(_df)
            .mark_bar()
            .encode(
                x=alt.X("poste:N", sort=["CA", "MCV", "Rés. expl.", "RCAI", "Rés. net"],
                        title="", axis=alt.Axis(labelAngle=0)),
                xOffset="type:N",
                y=alt.Y("montant:Q", title="Montant (€)", axis=alt.Axis(format=",.0f")),
                color=alt.Color(
                    "type:N",
                    scale=alt.Scale(domain=["Réel N-1", "Budget N"],
                                    range=["#94a3b8", "#1e40af"]),
                    legend=alt.Legend(title="", orient="top"),
                ),
                tooltip=[
                    alt.Tooltip("poste:N", title="Poste"),
                    alt.Tooltip("type:N", title="Type"),
                    alt.Tooltip("montant:Q", title="Montant", format=",.0f"),
                ],
            )
            .properties(title="Réel N-1 vs Budget N — Postes clés", height=340, width="container")
        )
        budget_chart = _chart
    return (budget_chart,)


@app.cell(hide_code=True)
def _(budget_scenario_id, budget_slider_charges, budget_slider_revenus):
    budget_save_btn = mo.ui.run_button(
        label="💾 Sauvegarder ces taux",
        kind="success",
        full_width=False,
    )
    return (budget_save_btn,)


@app.cell(hide_code=True)
def _(budget_save_btn, budget_scenario_id, budget_slider_charges, budget_slider_revenus):
    if budget_save_btn.value and budget_scenario_id:
        db_query(
            """UPDATE budget_regle_globale
               SET taux_revenus = %s, taux_charges = %s
               WHERE scenario_id = %s::uuid""",
            (budget_slider_revenus.value, budget_slider_charges.value, budget_scenario_id),
        )
        budget_save_msg = mo.callout(
            f"✓ Scenario sauvegarde : revenus +{budget_slider_revenus.value}%, charges +{budget_slider_charges.value}%",
            kind="success",
        )
    else:
        budget_save_msg = mo.md("")
    return (budget_save_msg,)


@app.cell(hide_code=True)
def _(
    budget_calc, budget_chart, budget_save_btn, budget_save_msg,
    budget_scenario_id, budget_slider_charges, budget_slider_revenus,
    budget_tbl_html, entite_nom, is_groupe,
):
    if is_groupe:
        budget_tab = mo.callout(
            "Le budget se calcule par **structure**, pas au niveau consolide. "
            "Selectionnez une structure specifique (STIVMAT, STA, HMA, ETPA) dans la sidebar.",
            kind="warn",
        )
    elif not budget_scenario_id:
        budget_tab = mo.callout("Scenario budget introuvable.", kind="danger")
    elif budget_calc["ca"][0] == 0:
        budget_tab = mo.callout(
            f"Aucune donnee reelle N-1 pour {entite_nom}. "
            f"Le budget se calcule sur le reel N-1 : verifiez l'annee de reference.",
            kind="info",
        )
    else:
        budget_tab = mo.vstack(
            [
                mo.md(f"### Budget CRD — {entite_nom}"),
                mo.md("Ajustez les taux de variation (applique sur le reel N-1). Le tableau et le graphique se mettent a jour automatiquement."),
                mo.hstack(
                    [budget_slider_revenus, budget_slider_charges],
                    widths="equal",
                    gap=1,
                ),
                budget_tbl_html,
                budget_chart,
                mo.hstack([budget_save_btn, budget_save_msg], justify="start", gap=1),
            ],
            gap=1,
        )
    return (budget_tab,)


# ── PAGE 5 : BUDGET TRESORERIE (DSO/DPO/DIO + mode montant) ─────

@app.function
def budget_load_treso_params(scenario_id_val):
    if not scenario_id_val:
        return ("taux_jours", 60, 45, 0, None, None)
    _df = db_query(
        """SELECT mode_projection, dso_jours, dpo_jours, dio_jours,
                  tn_cible_annuelle, bfr_cible_annuel
           FROM budget_tresorerie_parametres
           WHERE scenario_id = %s::uuid""",
        (scenario_id_val,),
    )
    if _df.empty:
        # Creation avec defauts
        db_query(
            "INSERT INTO budget_tresorerie_parametres (scenario_id) VALUES (%s::uuid) ON CONFLICT DO NOTHING",
            (scenario_id_val,),
        )
        return ("taux_jours", 60, 45, 0, None, None)
    _r = _df.iloc[0]
    return (
        _r["mode_projection"],
        int(_r["dso_jours"] or 60),
        int(_r["dpo_jours"] or 45),
        int(_r["dio_jours"] or 0),
        float(_r["tn_cible_annuelle"]) if _r["tn_cible_annuelle"] is not None else None,
        float(_r["bfr_cible_annuel"]) if _r["bfr_cible_annuel"] is not None else None,
    )


@app.cell(hide_code=True)
def _(budget_scenario_id, is_groupe):
    if is_groupe or not budget_scenario_id:
        treso_params_init = ("taux_jours", 60, 45, 0, None, None)
    else:
        treso_params_init = budget_load_treso_params(budget_scenario_id)
    return (treso_params_init,)


@app.cell(hide_code=True)
def _(treso_params_init):
    treso_slider_dso = mo.ui.slider(
        start=0, stop=180, step=1,
        value=treso_params_init[1],
        label="DSO — Délai paiement clients (jours)",
        show_value=True,
        full_width=True,
    )
    treso_slider_dpo = mo.ui.slider(
        start=0, stop=180, step=1,
        value=treso_params_init[2],
        label="DPO — Délai paiement fournisseurs (jours)",
        show_value=True,
        full_width=True,
    )
    treso_slider_dio = mo.ui.slider(
        start=0, stop=180, step=1,
        value=treso_params_init[3],
        label="DIO — Rotation stocks (jours)",
        show_value=True,
        full_width=True,
    )
    treso_input_bfr_cible = mo.ui.number(
        start=-10_000_000, stop=10_000_000, step=1000,
        value=treso_params_init[5] if treso_params_init[5] is not None else 0.0,
        label="BFR cible (€) — mode montant direct",
        full_width=True,
    )
    treso_input_tn_cible = mo.ui.number(
        start=-10_000_000, stop=10_000_000, step=1000,
        value=treso_params_init[4] if treso_params_init[4] is not None else 0.0,
        label="Trésorerie nette cible (€) — mode montant direct",
        full_width=True,
    )
    treso_mode_toggle = mo.ui.radio(
        options=["Délais (DSO/DPO/DIO)", "Montants directs"],
        value="Délais (DSO/DPO/DIO)" if treso_params_init[0] == "taux_jours" else "Montants directs",
        label="Mode de projection",
    )
    return (
        treso_input_bfr_cible, treso_input_tn_cible,
        treso_mode_toggle,
        treso_slider_dio, treso_slider_dpo, treso_slider_dso,
    )


@app.cell(hide_code=True)
def _(annee_prev, entite_id, is_groupe, refresh_tick):
    _ = refresh_tick
    # Reference N-1 : BFR et TN actuels (mono-entite pour budget)
    if is_groupe or not entite_id:
        treso_ref = {"bfr_reel": 0, "tn_reel": 0, "frng_reel": 0}
    else:
        _bf = bf_fetch(annee_prev, [entite_id])
        treso_ref = {
            "bfr_reel": _bf["bfr_exploit"] + _bf["bfr_hors_exploit"],
            "tn_reel": _bf["tresorerie_active"] - _bf["tresorerie_passive"],
            "frng_reel": _bf["ressources_stables"] - _bf["emplois_stables"],
        }
    return (treso_ref,)


@app.cell(hide_code=True)
def _(
    budget_calc, treso_input_bfr_cible, treso_input_tn_cible,
    treso_mode_toggle, treso_ref,
    treso_slider_dio, treso_slider_dpo, treso_slider_dso,
):
    # CA et achats projetes (proxy : charges variables)
    ca_ht = budget_calc["ca"][1]
    achats_ht = budget_calc["cv"][1]

    # Calcul via delais
    _tva = 1.20
    creances_calc = (ca_ht * _tva / 365.0) * treso_slider_dso.value
    dettes_calc   = (achats_ht * _tva / 365.0) * treso_slider_dpo.value
    stocks_calc   = (achats_ht / 365.0) * treso_slider_dio.value
    bfr_calcule   = creances_calc + stocks_calc - dettes_calc

    # Resultat budget vient du budget_calc
    resultat_budget = budget_calc["rn"][1]

    mode = treso_mode_toggle.value
    if mode == "Montants directs":
        bfr_budget = float(treso_input_bfr_cible.value)
        tn_budget = float(treso_input_tn_cible.value)
    else:
        bfr_budget = bfr_calcule
        # TN = FRNG_reel + Resultat_budget - BFR_budget
        tn_budget = treso_ref["frng_reel"] + resultat_budget - bfr_budget

    variation_tn = tn_budget - treso_ref["tn_reel"]

    treso_calc = {
        "ca_ht": ca_ht, "achats_ht": achats_ht,
        "creances": creances_calc, "dettes": dettes_calc, "stocks": stocks_calc,
        "bfr_calcule": bfr_calcule, "bfr_budget": bfr_budget,
        "resultat_budget": resultat_budget,
        "tn_budget": tn_budget,
        "variation_tn": variation_tn,
    }
    return (treso_calc,)


@app.cell(hide_code=True)
def _(treso_calc, treso_ref):
    def _kstat(label, cur, prev, caption):
        d = delta_pct(cur, prev)
        if d is None:
            return mo.stat(label=label, value=fmt(cur), caption=caption, bordered=True)
        return mo.stat(
            label=label, value=fmt(cur),
            caption=f"{caption} · {d:+.1%}",
            direction="increase" if d >= 0 else "decrease",
            bordered=True,
        )

    treso_kpi = mo.hstack(
        [
            mo.stat(label="FRNG réel N-1", value=fmt(treso_ref["frng_reel"]),
                    caption="Base pour projection", bordered=True),
            _kstat("BFR budget", treso_calc["bfr_budget"], treso_ref["bfr_reel"], "vs BFR réel N-1"),
            _kstat("Trésorerie nette budget", treso_calc["tn_budget"], treso_ref["tn_reel"], "vs TN réelle N-1"),
        ],
        widths="equal",
        gap=1,
    )
    return (treso_kpi,)


@app.cell(hide_code=True)
def _(treso_calc, treso_ref):
    # Chart comparatif Reel N-1 vs Budget N
    _rows = [
        {"poste": "BFR", "type": "Réel N-1", "montant": float(treso_ref["bfr_reel"])},
        {"poste": "BFR", "type": "Budget N", "montant": float(treso_calc["bfr_budget"])},
        {"poste": "Trésorerie nette", "type": "Réel N-1", "montant": float(treso_ref["tn_reel"])},
        {"poste": "Trésorerie nette", "type": "Budget N", "montant": float(treso_calc["tn_budget"])},
    ]
    _df = pd.DataFrame(_rows)

    _chart = (
        alt.Chart(_df)
        .mark_bar()
        .encode(
            x=alt.X("poste:N", sort=["BFR", "Trésorerie nette"], title="",
                    axis=alt.Axis(labelAngle=0)),
            xOffset="type:N",
            y=alt.Y("montant:Q", title="Montant (€)", axis=alt.Axis(format=",.0f")),
            color=alt.Color(
                "type:N",
                scale=alt.Scale(domain=["Réel N-1", "Budget N"],
                                range=["#94a3b8", "#1e40af"]),
                legend=alt.Legend(title="", orient="top"),
            ),
            tooltip=[
                alt.Tooltip("poste:N", title="Poste"),
                alt.Tooltip("type:N", title="Type"),
                alt.Tooltip("montant:Q", title="Montant", format=",.0f"),
            ],
        )
        .properties(title="BFR et Trésorerie — Réel N-1 vs Budget N", height=320, width="container")
    )
    treso_chart = _chart
    return (treso_chart,)


@app.cell(hide_code=True)
def _(treso_calc):
    # Tableau detaille des composants du BFR
    _rows = [
        ("Créances clients (CA × DSO / 365 × 1.20)", treso_calc["creances"]),
        ("+ Stocks (Achats × DIO / 365)",            treso_calc["stocks"]),
        ("− Dettes fournisseurs (Achats × DPO / 365 × 1.20)", -treso_calc["dettes"]),
        ("= BFR calculé via délais",                  treso_calc["bfr_calcule"]),
    ]
    _df = pd.DataFrame([{"Composant": lib, "Montant": val} for lib, val in _rows])

    def _fmt_v(v):
        if v is None or pd.isna(v):
            return ""
        return fmt(v)

    def _style(row):
        if row.name == 3:  # Total
            return ["background-color: #dbeafe; color: #1e3a8a; font-weight: 600"] * 2
        return [""] * 2

    _styler = (
        _df.style
        .format({"Montant": _fmt_v})
        .apply(_style, axis=1)
        .hide(axis="index")
    )
    treso_details_html = mo.Html(_styler.to_html())
    return (treso_details_html,)


@app.cell(hide_code=True)
def _(budget_scenario_id):
    treso_save_btn = mo.ui.run_button(
        label="💾 Sauvegarder ces paramètres trésorerie",
        kind="success",
        full_width=False,
    )
    return (treso_save_btn,)


@app.cell(hide_code=True)
def _(
    budget_scenario_id, treso_input_bfr_cible, treso_input_tn_cible,
    treso_mode_toggle, treso_save_btn,
    treso_slider_dio, treso_slider_dpo, treso_slider_dso,
):
    if treso_save_btn.value and budget_scenario_id:
        _mode_db = "taux_jours" if treso_mode_toggle.value == "Délais (DSO/DPO/DIO)" else "montant_direct"
        _bfr_cible = treso_input_bfr_cible.value if _mode_db == "montant_direct" else None
        _tn_cible  = treso_input_tn_cible.value  if _mode_db == "montant_direct" else None
        db_query(
            """UPDATE budget_tresorerie_parametres
               SET mode_projection = %s,
                   dso_jours = %s, dpo_jours = %s, dio_jours = %s,
                   bfr_cible_annuel = %s, tn_cible_annuelle = %s
               WHERE scenario_id = %s::uuid""",
            (_mode_db,
             treso_slider_dso.value, treso_slider_dpo.value, treso_slider_dio.value,
             _bfr_cible, _tn_cible, budget_scenario_id),
        )
        treso_save_msg = mo.callout(
            f"✓ Parametres sauvegardes (mode : {_mode_db})",
            kind="success",
        )
    else:
        treso_save_msg = mo.md("")
    return (treso_save_msg,)


@app.cell(hide_code=True)
def _(
    budget_scenario_id, entite_nom, is_groupe,
    treso_calc, treso_chart, treso_details_html,
    treso_input_bfr_cible, treso_input_tn_cible, treso_kpi,
    treso_mode_toggle, treso_save_btn, treso_save_msg,
    treso_slider_dio, treso_slider_dpo, treso_slider_dso,
):
    if is_groupe:
        treso_tab = mo.callout(
            "Le budget tresorerie se calcule par **structure**. "
            "Selectionnez STIVMAT, STA, HMA ou ETPA dans la sidebar.",
            kind="warn",
        )
    elif not budget_scenario_id:
        treso_tab = mo.callout("Scenario budget introuvable.", kind="danger")
    elif treso_calc["ca_ht"] == 0:
        treso_tab = mo.callout(
            f"Aucun CA budget pour {entite_nom}. Le calcul tresorerie depend du budget CRD.",
            kind="info",
        )
    else:
        treso_tab = mo.vstack(
            [
                mo.md(f"### Budget Trésorerie — {entite_nom}"),
                mo.md(
                    "**DSO** = Days Sales Outstanding (delai encaissement clients) · "
                    "**DPO** = Days Payable Outstanding (delai paiement fournisseurs) · "
                    "**DIO** = Days Inventory Outstanding (rotation stocks)"
                ),
                treso_mode_toggle,
                mo.hstack(
                    [treso_slider_dso, treso_slider_dpo, treso_slider_dio],
                    widths="equal", gap=1,
                ),
                mo.hstack(
                    [treso_input_bfr_cible, treso_input_tn_cible],
                    widths="equal", gap=1,
                ),
                treso_kpi,
                mo.md("### Décomposition du BFR calculé"),
                treso_details_html,
                treso_chart,
                mo.hstack([treso_save_btn, treso_save_msg], justify="start", gap=1),
            ],
            gap=1,
        )
    return (treso_tab,)


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
def _(bf_tab, budget_tab, crd_tab, overview_tab, sql_tab, treso_tab):
    mo.ui.tabs(
        {
            "Vue d'ensemble": overview_tab,
            "CRD Réel": crd_tab,
            "Bilan Fonctionnel": bf_tab,
            "Budget CRD": budget_tab,
            "Budget Trésorerie": treso_tab,
            "SQL libre": sql_tab,
        },
    )
    return


if __name__ == "__main__":
    app.run()
