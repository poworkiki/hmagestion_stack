"""
HMA Toolbox — Streamlit Dashboard
Checks rapides, exploration GL, controles qualite, SIG/CRD express.

Usage local  : streamlit run hma-toolbox/app_streamlit.py
Usage Docker : streamlit run /app/app_streamlit.py --server.port 8501 --server.address 0.0.0.0
"""
import os
from datetime import datetime, timezone, timedelta
import streamlit as st
import pg8000
from streamlit_echarts import st_echarts, JsCode

# Fuseau Guyane francaise (UTC-3, pas de DST)
TZ_GUYANE = timezone(timedelta(hours=-3))
JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
MOIS_FR = ["", "janvier", "fevrier", "mars", "avril", "mai", "juin",
           "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]

def now_guyane():
    """Datetime actuelle en heure locale Guyane."""
    return datetime.now(TZ_GUYANE)

def fmt(v):
    """Format montant : 1 000 000 €"""
    if v is None:
        return "0 €"
    n = float(v)
    sign = "-" if n < 0 else ""
    parts = f"{abs(n):,.0f}".replace(",", " ")
    return f"{sign}{parts} €"

# Format JS ECharts : 1 000 000 €
JS_FMT = JsCode("function(v){return v.toLocaleString('fr-FR',{maximumFractionDigits:0})+' €'}")

st.set_page_config(
    page_title="HMA Toolbox",
    page_icon=":bar_chart:",
    initial_sidebar_state="expanded",
    layout="wide",
)

# --- DB Connection ---
@st.cache_resource
def get_conn():
    return pg8000.connect(
        host=os.environ.get('PG_HOST', 'h2dnymbgnulve0kko87nh856'),
        port=int(os.environ.get('PG_PORT', '5432')),
        database=os.environ.get('PG_DATABASE', 'postgres'),
        user=os.environ.get('PG_USER', 'postgres'),
        password=os.environ.get('PG_PASSWORD', ''),
    )

def query(sql):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return cols, rows

def query_dicts(sql):
    cols, rows = query(sql)
    return [dict(zip(cols, r)) for r in rows]

def query_single(sql):
    _, rows = query(sql)
    return rows[0][0] if rows else None


# --- Sidebar ---
st.sidebar.title(":bar_chart: HMA Toolbox")

# Exercice en cours = derniere annee presente en base
_current_year_row = query_single(
    "SELECT EXTRACT(year FROM MAX(ecriture_date))::int FROM grand_livre WHERE NOT is_a_nouveau"
)
_current_exercice = str(_current_year_row) if _current_year_row else '2026'

structures = ['Toutes', 'HMA', 'STIVMAT', 'STA', 'ETPA']
selected_structure = st.sidebar.selectbox(
    "Structure",
    structures,
    index=0,  # defaut : Toutes (Groupe)
    help="Filtrer par structure ou afficher le consolide groupe",
)

exercices_data = query_dicts(
    "SELECT DISTINCT exercice_label FROM grand_livre ORDER BY exercice_label DESC"
)
exercice_options = ['Tous'] + [r['exercice_label'] for r in exercices_data]
# Defaut : exercice en cours (2026)
_default_ex_idx = exercice_options.index(_current_exercice) if _current_exercice in exercice_options else 0
selected_exercice = st.sidebar.selectbox(
    "Exercice",
    exercice_options,
    index=_default_ex_idx,
    help="Defaut : exercice en cours (donnees YTD au jour j)",
)

# Filtre mois (defaut : Tous = YTD depuis janvier jusqu aujourd hui)
mois_options = ['Tous']
if selected_exercice != 'Tous':
    mois_data = query_dicts(f"""
        SELECT DISTINCT mois, mois_nom FROM grand_livre
        WHERE exercice_label = '{selected_exercice}'
        ORDER BY mois
    """)
    mois_options += [f"{d['mois']} - {d['mois_nom']}" for d in mois_data]
else:
    mois_data = query_dicts("SELECT DISTINCT mois, mois_nom FROM grand_livre ORDER BY mois")
    mois_options += [f"{d['mois']} - {d['mois_nom']}" for d in mois_data]
selected_mois = st.sidebar.selectbox(
    "Mois",
    mois_options,
    index=0,  # defaut : Tous (= YTD tous mois de l exercice)
    help="Defaut : tous les mois de l exercice (vue YTD)",
)

# Build WHERE clause
def build_where():
    clauses = ["1=1"]
    if selected_structure != 'Toutes':
        clauses.append(f"entite_code = '{selected_structure}'")
    if selected_exercice != 'Tous':
        clauses.append(f"exercice_label = '{selected_exercice}'")
    if selected_mois != 'Tous':
        mois_num = int(selected_mois.split(' - ')[0])
        clauses.append(f"mois = {mois_num}")
    return " AND ".join(clauses)

where = build_where()
where_no_an = f"{where} AND NOT is_a_nouveau"

page = st.sidebar.radio("Page", [
    "Tableau de bord",
    "Balance Generale",
    "Bilan Comptable",
    "Bilan Fonctionnel",
    "Balance Clients",
    "Balance Fournisseurs",
    "SIG Express",
    "CRD Express",
    "Exploration GL",
    "Controles qualite",
    "Requete SQL",
])

st.sidebar.markdown("---")

# Date et heure locale Guyane
_now = now_guyane()
_jour_fr = JOURS_FR[_now.weekday()]
_mois_fr = MOIS_FR[_now.month]
st.sidebar.markdown(
    f"""
    <div style='font-size:0.85rem; color:#6c757d; line-height:1.4;'>
    📅 <strong>{_jour_fr} {_now.day} {_mois_fr} {_now.year}</strong><br>
    🕐 {_now.strftime('%H:%M')} (heure Guyane)
    </div>
    """,
    unsafe_allow_html=True,
)
st.sidebar.markdown("")
st.sidebar.caption("HMA Gestion — Guyane")


# --- CSS : top bar sticky ---
st.markdown("""
<style>
div[data-testid="stMetric"] {
    background-color: #f0f2f6;
    border-radius: 8px;
    padding: 10px 15px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
div[data-testid="stMetric"] label {
    font-size: 0.8rem;
    color: #555;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-size: 1.3rem;
    font-weight: 700;
}
.sticky-header {
    position: sticky;
    top: 0;
    z-index: 999;
    background: white;
    padding-bottom: 5px;
    border-bottom: 1px solid #ddd;
}
</style>
""", unsafe_allow_html=True)

# --- KPI TOP BAR (sticky, toujours visible) ---
_kpi_ca = query_single(f"SELECT COALESCE(SUM(credit - debit), 0) FROM grand_livre WHERE {where_no_an} AND compte_numero LIKE '70%'")
_kpi_produits = query_single(f"SELECT COALESCE(SUM(credit - debit), 0) FROM grand_livre WHERE {where_no_an} AND classe = 7")
_kpi_charges = query_single(f"SELECT COALESCE(SUM(debit - credit), 0) FROM grand_livre WHERE {where_no_an} AND classe = 6")
_kpi_resultat_net = float(_kpi_produits or 0) - float(_kpi_charges or 0)
_kpi_nb = query_single(f"SELECT COUNT(*) FROM grand_livre WHERE {where}")

# Label filtre actif
_filtre_label = selected_structure if selected_structure != 'Toutes' else 'Groupe'
if selected_exercice != 'Tous':
    _filtre_label += f" | {selected_exercice}"
if selected_mois != 'Tous':
    _filtre_label += f" | {selected_mois}"

with st.container():
    st.caption(f"**{_filtre_label}**")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("CA", fmt(_kpi_ca))
    k2.metric("Produits", fmt(_kpi_produits))
    k3.metric("Charges", fmt(_kpi_charges))
    k4.metric("Resultat net", fmt(_kpi_resultat_net))
    k5.metric("Ecritures", f"{_kpi_nb:,}")
st.divider()


# ==========================================
# PAGE 1 : TABLEAU DE BORD (refactor 2026-04-11)
# ==========================================
if page == "Tableau de bord":
    # Recuperer la date de reference (derniere ecriture avec donnees)
    _date_ref = query_single(f"SELECT MAX(ecriture_date) FROM grand_livre WHERE {where_no_an}")
    _date_ref_str = _date_ref.strftime('%d/%m/%Y') if _date_ref else '—'

    st.subheader(f"Tableau de bord · {_filtre_label}")
    st.caption(f"Données au **{_date_ref_str}**")

    # --- KPI clés (marge + croissance) ---
    _ca = float(_kpi_ca or 0)
    _charges = float(_kpi_charges or 0)
    _resultat = float(_kpi_resultat_net or 0)
    _taux_marge = (_resultat / _ca * 100) if _ca > 0 else 0

    # CA N-1 (meme periode)
    _ca_n1 = 0
    if selected_exercice not in ('Tous',) and selected_exercice.isdigit():
        _prev_year = int(selected_exercice) - 1
        _where_n1 = f"annee = {_prev_year} AND NOT is_a_nouveau"
        if selected_structure != 'Toutes':
            _where_n1 += f" AND entite_code = '{selected_structure}'"
        if selected_mois != 'Tous':
            _mois_num = int(selected_mois.split(' - ')[0])
            _where_n1 += f" AND mois <= {_mois_num}"
        _ca_n1 = float(query_single(
            f"SELECT COALESCE(SUM(credit - debit), 0) FROM grand_livre WHERE {_where_n1} AND compte_numero LIKE '70%'"
        ) or 0)

    _delta_ca = ((_ca - _ca_n1) / _ca_n1 * 100) if _ca_n1 > 0 else None

    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Taux de marge",
        f"{_taux_marge:.1f} %",
        help="Résultat net / CA",
    )
    m2.metric(
        "CA vs N-1",
        f"{_delta_ca:+.1f} %" if _delta_ca is not None else "—",
        help=f"CA {selected_exercice if selected_exercice != 'Tous' else ''} vs année précédente",
    )
    _nb_jours = query_single(f"SELECT COUNT(DISTINCT ecriture_date) FROM grand_livre WHERE {where_no_an}")
    m3.metric(
        "Jours avec activité",
        f"{_nb_jours or 0}",
        help="Nombre de jours distincts avec écritures sur la période",
    )

    st.divider()

    # ============================================================
    # GRAPHIQUE 1 : Waterfall formation du résultat
    # ============================================================
    st.subheader("Formation du résultat")
    st.caption("CA → Charges → Résultat net")

    _wf_data = [
        {"name": "CA", "value": round(_ca, 0)},
        {"name": "Charges", "value": -round(_charges, 0)},
        {"name": "Résultat", "value": round(_resultat, 0)},
    ]

    wf_opts = {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}, "valueFormatter": JS_FMT},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
        "xAxis": {"type": "category", "data": ["CA", "Charges", "Résultat"]},
        "yAxis": {"type": "value", "axisLabel": {"formatter": JS_FMT}},
        "series": [{
            "type": "bar",
            "data": [
                {"value": round(_ca, 0), "itemStyle": {"color": "#3182ce"}},
                {"value": -round(_charges, 0), "itemStyle": {"color": "#e53e3e"}},
                {"value": round(_resultat, 0),
                 "itemStyle": {"color": "#38a169" if _resultat >= 0 else "#c53030"}},
            ],
            "label": {"show": True, "position": "top", "formatter": JS_FMT},
        }],
    }
    st_echarts(options=wf_opts, height="320px", theme="streamlit")

    # ============================================================
    # GRAPHIQUE 2 : Comparaison par structure (si pas filtré)
    # ============================================================
    if selected_structure == 'Toutes':
        st.subheader("Comparaison par structure")
        st.caption("CA vs Charges vs Résultat pour chaque structure")

        _where_struct = where_no_an.replace("1=1 AND ", "").replace("1=1", "1=1")
        data_struct = query_dicts(f"""
            SELECT entite_code,
                ROUND(SUM(CASE WHEN compte_numero LIKE '70%' THEN credit - debit ELSE 0 END)::numeric, 0) AS ca,
                ROUND(SUM(CASE WHEN classe = 6 THEN debit - credit ELSE 0 END)::numeric, 0) AS charges,
                ROUND(SUM(CASE WHEN classe = 7 THEN credit - debit ELSE 0 END)
                    - SUM(CASE WHEN classe = 6 THEN debit - credit ELSE 0 END), 0) AS resultat
            FROM grand_livre WHERE {where_no_an}
            GROUP BY entite_code ORDER BY entite_code
        """)

        if data_struct:
            codes = [d['entite_code'] for d in data_struct]
            ca_vals = [float(d['ca']) for d in data_struct]
            ch_vals = [float(d['charges']) for d in data_struct]
            res_vals = [float(d['resultat']) for d in data_struct]

            struct_opts = {
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}, "valueFormatter": JS_FMT},
                "legend": {"top": 0, "data": ["CA", "Charges", "Résultat"]},
                "grid": {"top": "15%", "bottom": "5%", "containLabel": True},
                "xAxis": {"type": "category", "data": codes},
                "yAxis": {"type": "value", "axisLabel": {"formatter": JS_FMT}},
                "series": [
                    {"name": "CA", "type": "bar", "data": ca_vals,
                     "itemStyle": {"color": "#3182ce"}},
                    {"name": "Charges", "type": "bar", "data": ch_vals,
                     "itemStyle": {"color": "#e53e3e"}},
                    {"name": "Résultat", "type": "bar", "data": res_vals,
                     "itemStyle": {"color": "#38a169"}},
                ],
            }
            st_echarts(options=struct_opts, height="350px", theme="streamlit")

    # ============================================================
    # GRAPHIQUE 3 : Évolution mensuelle CA + N-1
    # ============================================================
    st.subheader("Évolution mensuelle du CA")
    _compare_year = (selected_exercice.isdigit() and int(selected_exercice) - 1 >= 2022)
    if _compare_year:
        st.caption(f"Comparaison {selected_exercice} vs {int(selected_exercice) - 1}")
    else:
        st.caption("Sélectionne un exercice pour comparer avec l'année précédente")

    # Data N (periode actuelle)
    _where_n = where_no_an
    ca_n_data = query_dicts(f"""
        SELECT mois, mois_nom, ROUND(SUM(credit - debit)::numeric, 0) AS ca
        FROM grand_livre
        WHERE {_where_n} AND compte_numero LIKE '70%'
        GROUP BY mois, mois_nom ORDER BY mois
    """)

    if ca_n_data:
        mois_labels = [d['mois_nom'][:3] for d in ca_n_data]
        ca_n_vals = [float(d['ca']) for d in ca_n_data]

        # Données N-1 (si comparaison possible)
        ca_n1_vals = []
        if _compare_year:
            _where_prev = f"annee = {int(selected_exercice) - 1} AND NOT is_a_nouveau"
            if selected_structure != 'Toutes':
                _where_prev += f" AND entite_code = '{selected_structure}'"
            ca_prev_data = query_dicts(f"""
                SELECT mois, ROUND(SUM(credit - debit)::numeric, 0) AS ca
                FROM grand_livre
                WHERE {_where_prev} AND compte_numero LIKE '70%'
                GROUP BY mois ORDER BY mois
            """)
            _prev_map = {d['mois']: float(d['ca']) for d in ca_prev_data}
            ca_n1_vals = [_prev_map.get(d['mois'], 0) for d in ca_n_data]

        # Moyenne N
        _avg_n = sum(ca_n_vals) / len(ca_n_vals) if ca_n_vals else 0

        series = [
            {"name": f"CA {selected_exercice if selected_exercice != 'Tous' else ''}",
             "type": "bar", "data": ca_n_vals,
             "itemStyle": {"color": "#3182ce"}},
            {"name": "Moyenne", "type": "line", "data": [_avg_n] * len(mois_labels),
             "itemStyle": {"color": "#d69e2e"}, "lineStyle": {"width": 2, "type": "dashed"},
             "symbol": "none"},
        ]
        if _compare_year:
            series.insert(1, {
                "name": f"CA {int(selected_exercice) - 1}",
                "type": "line", "data": ca_n1_vals,
                "itemStyle": {"color": "#a0aec0"},
                "lineStyle": {"width": 2},
                "symbol": "circle", "symbolSize": 6,
            })

        evol_opts = {
            "tooltip": {"trigger": "axis", "valueFormatter": JS_FMT},
            "legend": {"top": 0},
            "grid": {"top": "15%", "bottom": "5%", "containLabel": True},
            "xAxis": {"type": "category", "data": mois_labels},
            "yAxis": {"type": "value", "axisLabel": {"formatter": JS_FMT}},
            "series": series,
        }
        st_echarts(options=evol_opts, height="320px", theme="streamlit")

    # ============================================================
    # GRAPHIQUE 4 : Top 5 postes de charges (Pareto)
    # ============================================================
    st.subheader("Top 10 postes de charges")
    st.caption("Où va l'argent — les 10 comptes de charges les plus importants")
    top_charges = query_dicts(f"""
        SELECT compte_numero, compte_libelle,
            ROUND(SUM(debit - credit)::numeric, 0) AS montant
        FROM grand_livre
        WHERE {where_no_an} AND classe = 6
        GROUP BY compte_numero, compte_libelle
        HAVING SUM(debit - credit) > 0
        ORDER BY SUM(debit - credit) DESC
        LIMIT 10
    """)

    if top_charges:
        labels = [f"{c['compte_numero']} {(c['compte_libelle'] or '')[:30]}" for c in top_charges]
        vals = [float(c['montant']) for c in top_charges]
        labels.reverse()
        vals.reverse()

        pareto_opts = {
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}, "valueFormatter": JS_FMT},
            "grid": {"left": "25%", "right": "10%", "containLabel": True},
            "xAxis": {"type": "value", "axisLabel": {"formatter": JS_FMT}},
            "yAxis": {"type": "category", "data": labels, "axisLabel": {"fontSize": 11}},
            "series": [{
                "type": "bar",
                "data": vals,
                "itemStyle": {"color": "#e53e3e"},
                "label": {"show": True, "position": "right", "formatter": JS_FMT},
            }],
        }
        st_echarts(options=pareto_opts, height=f"{max(350, len(labels) * 35)}px", theme="streamlit")
    else:
        st.info("Aucun compte de charge pour cette sélection.")

    # ============================================================
    # Footer : etat sync discret
    # ============================================================
    st.divider()
    with st.expander("État synchronisation Pennylane", expanded=False):
        sync = query_dicts("""
            SELECT e.code, sm.status, sm.last_sync_at, sm.row_count_local
            FROM sync_metadata sm JOIN entite e ON e.id = sm.entite_id
            WHERE sm.endpoint = 'ledger_entry_lines'
            ORDER BY e.code
        """)
        if sync:
            sync_cols = st.columns(len(sync))
            for i, s in enumerate(sync):
                icon = "✅" if s['status'] == 'done' else "⚠️"
                sync_cols[i].metric(
                    f"{icon} {s['code']}",
                    f"{s['row_count_local']} écritures",
                    help=f"Dernier sync : {s['last_sync_at']}",
                )


# ==========================================
# PAGE 2 : BALANCE GENERALE
# ==========================================
elif page == "Balance Generale":
    st.title(":ledger: Balance Generale")

    # Filtre classe
    classe_filter = st.multiselect("Filtrer par classe", [1,2,3,4,5,6,7], default=[])

    where_bg = where.replace("entite_code", "entite_nom")
    if classe_filter:
        where_bg += f" AND classe IN ({','.join(str(c) for c in classe_filter)})"

    bg_data = query_dicts(f"""
        SELECT entite_nom, annee, classe, compte_numero, compte_libelle,
            SUM(total_debit) AS total_debit, SUM(total_credit) AS total_credit,
            GREATEST(SUM(total_debit - total_credit), 0) AS solde_debiteur,
            GREATEST(SUM(total_credit - total_debit), 0) AS solde_crediteur,
            SUM(total_debit - total_credit) AS solde
        FROM balance_generale
        WHERE {where_bg}
        GROUP BY entite_nom, annee, classe, compte_numero, compte_libelle
        ORDER BY compte_numero
    """)

    if bg_data:
        # KPIs
        total_d = sum(float(d['total_debit'] or 0) for d in bg_data)
        total_c = sum(float(d['total_credit'] or 0) for d in bg_data)
        nb_comptes = len(bg_data)

        c1, c2, c3 = st.columns(3)
        c1.metric("Comptes", f"{nb_comptes}")
        c2.metric("Total Debit", fmt(total_d))
        c3.metric("Total Credit", fmt(total_c))

        # Table
        st.dataframe(bg_data, use_container_width=True, height=500)

        # Chart par classe
        st.subheader("Solde par classe")
        classe_data = {}
        for d in bg_data:
            cl = str(d['classe'])
            classe_data[cl] = classe_data.get(cl, 0) + float(d['solde'] or 0)

        classes = sorted(classe_data.keys())
        soldes_classe = [round(classe_data[c]) for c in classes]
        labels_classe = {
            '1': '1-Capitaux', '2': '2-Immo', '3': '3-Stocks',
            '4': '4-Tiers', '5': '5-Financiers', '6': '6-Charges', '7': '7-Produits'
        }

        bar_data = []
        for c, v in zip(classes, soldes_classe):
            bar_data.append({"value": v, "itemStyle": {"color": "#5470c6" if v >= 0 else "#ee6666"}})

        opts = {
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": [labels_classe.get(c, c) for c in classes]},
            "yAxis": {"type": "value"},
            "series": [{"type": "bar", "data": bar_data}],
        }
        st_echarts(options=opts, height="350px", theme="streamlit")
    else:
        st.info("Aucune donnee pour les filtres selectionnes.")


# ==========================================
# PAGE 3 : BILAN COMPTABLE
# ==========================================
elif page == "Bilan Comptable":
    st.title(":balance_scale: Bilan Comptable")

    bilan_data = query_dicts(f"""
        SELECT entite_code, annee, bilan_section, bilan_poste,
            ROUND(SUM(CASE
                WHEN compte_numero NOT LIKE '28%' AND compte_numero NOT LIKE '29%'
                 AND compte_numero NOT LIKE '39%' AND compte_numero NOT LIKE '49%'
                 AND compte_numero NOT LIKE '59%'
                THEN CASE WHEN bilan_section LIKE 'actif%' THEN debit - credit ELSE credit - debit END
                ELSE 0 END)::numeric, 0) AS brut,
            ROUND(SUM(CASE
                WHEN compte_numero LIKE '28%' OR compte_numero LIKE '29%'
                  OR compte_numero LIKE '39%' OR compte_numero LIKE '49%'
                  OR compte_numero LIKE '59%'
                THEN credit - debit ELSE 0 END)::numeric, 0) AS amort,
            ROUND(SUM(CASE
                WHEN bilan_section LIKE 'actif%' THEN debit - credit ELSE credit - debit
            END)::numeric, 0) AS net
        FROM grand_livre
        WHERE bilan_section IS NOT NULL AND classe BETWEEN 1 AND 5 AND {where}
        GROUP BY entite_code, annee, bilan_section, bilan_poste
        ORDER BY bilan_section, bilan_poste
    """)

    if bilan_data:
        # Separer actif et passif
        actif = [d for d in bilan_data if d.get('bilan_section', '').startswith('actif')]
        passif = [d for d in bilan_data if d.get('bilan_section', '').startswith('passif')]

        total_actif = sum(float(d['net'] or 0) for d in actif)
        total_passif = sum(float(d['net'] or 0) for d in passif)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Actif Net", fmt(total_actif))
        c2.metric("Total Passif", fmt(total_passif))
        c3.metric("Ecart", fmt(total_actif - total_passif))

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Actif")
            if actif:
                postes_a = [d['bilan_poste'] for d in actif]
                nets_a = [float(d['net'] or 0) for d in actif]
                opts_a = {
                    "tooltip": {"trigger": "axis"},
                    "yAxis": {"type": "category", "data": postes_a[::-1]},
                    "xAxis": {"type": "value"},
                    "grid": {"containLabel": True},
                    "series": [{"type": "bar", "data": nets_a[::-1],
                                "itemStyle": {"color": "#91cc75"}}],
                }
                st_echarts(options=opts_a, height="400px", theme="streamlit", key="bilan_actif")

        with col2:
            st.subheader("Passif")
            if passif:
                postes_p = [d['bilan_poste'] for d in passif]
                nets_p = [float(d['net'] or 0) for d in passif]
                opts_p = {
                    "tooltip": {"trigger": "axis"},
                    "yAxis": {"type": "category", "data": postes_p[::-1]},
                    "xAxis": {"type": "value"},
                    "grid": {"containLabel": True},
                    "series": [{"type": "bar", "data": nets_p[::-1],
                                "itemStyle": {"color": "#5470c6"}}],
                }
                st_echarts(options=opts_p, height="400px", theme="streamlit", key="bilan_passif")

        with st.expander("Detail complet"):
            st.dataframe(bilan_data, use_container_width=True)
    else:
        st.info("Aucune donnee bilan.")


# ==========================================
# PAGE 4 : BILAN FONCTIONNEL
# ==========================================
elif page == "Bilan Fonctionnel":
    st.title(":building_construction: Bilan Fonctionnel")

    bf_data = query_dicts(f"""
        WITH brut AS (
            SELECT entite_code, bf_categorie,
                SUM(CASE
                    WHEN bf_categorie IN ('emplois_stables','bfr_exploit','bfr_hors_exploit','tresorerie_active')
                    THEN debit - credit ELSE credit - debit
                END) AS montant
            FROM grand_livre
            WHERE bf_categorie IS NOT NULL AND {where}
              AND compte_numero NOT LIKE '28%' AND compte_numero NOT LIKE '29%'
              AND compte_numero NOT LIKE '39%' AND compte_numero NOT LIKE '49%'
              AND compte_numero NOT LIKE '59%'
            GROUP BY entite_code, bf_categorie
        ),
        amort AS (
            SELECT entite_code, 'ressources_stables' AS bf_categorie,
                SUM(credit - debit) AS montant
            FROM grand_livre
            WHERE {where} AND (compte_numero LIKE '28%' OR compte_numero LIKE '29%'
               OR compte_numero LIKE '39%' OR compte_numero LIKE '49%'
               OR compte_numero LIKE '59%')
            GROUP BY entite_code
        )
        SELECT entite_code AS entite_nom, bf_categorie, ROUND(SUM(montant)::numeric, 0) AS montant
        FROM (SELECT * FROM brut UNION ALL SELECT * FROM amort) combined
        GROUP BY entite_code, bf_categorie
        ORDER BY entite_code, bf_categorie
    """)

    if bf_data:
        # Calcul FRNG, BFR, TN
        emplois_stables = sum(float(d['montant'] or 0) for d in bf_data if d['bf_categorie'] == 'emplois_stables')
        ressources_stables = sum(float(d['montant'] or 0) for d in bf_data if d['bf_categorie'] == 'ressources_stables')
        bfr_exploit = sum(float(d['montant'] or 0) for d in bf_data if d['bf_categorie'] == 'bfr_exploit')
        bfr_hors = sum(float(d['montant'] or 0) for d in bf_data if d['bf_categorie'] == 'bfr_hors_exploit')
        treso_active = sum(float(d['montant'] or 0) for d in bf_data if d['bf_categorie'] == 'tresorerie_active')
        treso_passive = sum(float(d['montant'] or 0) for d in bf_data if d['bf_categorie'] == 'tresorerie_passive')

        frng = ressources_stables - emplois_stables
        bfr = bfr_exploit + bfr_hors
        tn = treso_active - treso_passive

        c1, c2, c3 = st.columns(3)
        c1.metric("FRNG", fmt(frng), help="Ressources stables - Emplois stables")
        c2.metric("BFR", fmt(bfr), help="BFR exploitation + BFR hors exploitation")
        c3.metric("Tresorerie Nette", fmt(tn), help="Tresorerie active - Tresorerie passive")

        # Verification : FRNG = BFR + TN
        ecart_bf = frng - bfr - tn
        if abs(ecart_bf) > 1:
            st.warning(f"Ecart d'equilibre : FRNG - BFR - TN = {fmt(ecart_bf)}")
        else:
            st.success("Equilibre verifie : FRNG = BFR + TN")

        # Chart
        categories = ['Emplois stables', 'Ressources stables', 'BFR exploit', 'BFR hors exploit', 'Treso active', 'Treso passive']
        montants = [emplois_stables, ressources_stables, bfr_exploit, bfr_hors, treso_active, treso_passive]
        colors = ['#ee6666', '#91cc75', '#fac858', '#fac858', '#73c0de', '#ee6666']

        opts = {
            "tooltip": {"trigger": "axis",
                        "valueFormatter": JS_FMT},
            "xAxis": {"type": "category", "data": categories, "axisLabel": {"rotate": 30}},
            "yAxis": {"type": "value"},
            "series": [{"type": "bar", "data": [
                {"value": round(v), "itemStyle": {"color": c}} for v, c in zip(montants, colors)
            ]}],
        }
        st_echarts(options=opts, height="400px", theme="streamlit")

        with st.expander("Detail par structure"):
            st.dataframe(bf_data, use_container_width=True)
    else:
        st.info("Aucune donnee bilan fonctionnel.")


# ==========================================
# PAGE 5 : BALANCE CLIENTS
# ==========================================
elif page == "Balance Clients":
    st.title(":bust_in_silhouette: Balance Clients")

    where_cl = "1=1"
    if selected_structure != 'Toutes':
        where_cl += f" AND entite_code = '{selected_structure}'"

    clients = query_dicts(f"""
        SELECT entite_code, client_nom, compte_numero,
            nb_ecritures, ROUND(total_debit::numeric, 2) AS total_debit,
            ROUND(total_credit::numeric, 2) AS total_credit,
            ROUND(solde::numeric, 2) AS solde,
            ROUND(solde_non_lettre::numeric, 2) AS solde_non_lettre,
            anciennete_max_jours, tranche_anciennete
        FROM v_balance_clients
        WHERE {where_cl}
        ORDER BY ABS(solde) DESC
    """)

    if clients:
        total_solde = sum(float(d['solde'] or 0) for d in clients)
        total_non_lettre = sum(float(d['solde_non_lettre'] or 0) for d in clients)
        nb_clients = len(clients)

        c1, c2, c3 = st.columns(3)
        c1.metric("Clients", f"{nb_clients}")
        c2.metric("Solde total", fmt(total_solde))
        c3.metric("Non lettre", fmt(total_non_lettre))

        st.dataframe(clients, use_container_width=True, height=400)

        # Chart anciennete
        st.subheader("Repartition par anciennete")
        tranches = {}
        for d in clients:
            t = d.get('tranche_anciennete', 'Inconnu')
            tranches[t] = tranches.get(t, 0) + float(d['solde_non_lettre'] or 0)

        if tranches:
            pie_data = [{"name": k, "value": round(abs(v))} for k, v in sorted(tranches.items()) if v != 0]
            opts = {
                "tooltip": {"trigger": "item", "formatter": JsCode("function(p){return p.name+': '+p.value.toLocaleString('fr-FR')+' € ('+p.percent+'%)'}")},
                "series": [{"type": "pie", "radius": ["40%", "70%"], "data": pie_data,
                            "itemStyle": {"borderRadius": 8, "borderColor": "#fff", "borderWidth": 2},
                            "label": {"show": True, "formatter": "{b}: {d}%"}}],
            }
            st_echarts(options=opts, height="350px", theme="streamlit")
    else:
        st.info("Aucune donnee clients.")


# ==========================================
# PAGE 6 : BALANCE FOURNISSEURS
# ==========================================
elif page == "Balance Fournisseurs":
    st.title(":package: Balance Fournisseurs")

    where_fr = "1=1"
    if selected_structure != 'Toutes':
        where_fr += f" AND entite_code = '{selected_structure}'"

    fournisseurs = query_dicts(f"""
        SELECT entite_code, fournisseur_nom, compte_numero,
            nb_ecritures, ROUND(total_debit::numeric, 2) AS total_debit,
            ROUND(total_credit::numeric, 2) AS total_credit,
            ROUND(solde::numeric, 2) AS solde,
            ROUND(solde_non_lettre::numeric, 2) AS solde_non_lettre,
            anciennete_max_jours, tranche_anciennete
        FROM v_balance_fournisseurs
        WHERE {where_fr}
        ORDER BY ABS(solde) DESC
    """)

    if fournisseurs:
        total_solde = sum(float(d['solde'] or 0) for d in fournisseurs)
        total_non_lettre = sum(float(d['solde_non_lettre'] or 0) for d in fournisseurs)
        nb_fourn = len(fournisseurs)

        c1, c2, c3 = st.columns(3)
        c1.metric("Fournisseurs", f"{nb_fourn}")
        c2.metric("Solde total", fmt(total_solde))
        c3.metric("Non lettre", fmt(total_non_lettre))

        st.dataframe(fournisseurs, use_container_width=True, height=400)

        # Top 10 fournisseurs par solde
        st.subheader("Top 10 fournisseurs")
        top10 = fournisseurs[:10]
        noms = [d['fournisseur_nom'][:30] for d in top10]
        soldes = [float(d['solde'] or 0) for d in top10]

        bar_data = [{"value": round(v), "itemStyle": {"color": "#ee6666" if v < 0 else "#91cc75"}}
                    for v in soldes]

        opts = {
            "tooltip": {"trigger": "axis"},
            "yAxis": {"type": "category", "data": noms[::-1]},
            "xAxis": {"type": "value"},
            "grid": {"containLabel": True, "left": "3%"},
            "series": [{"type": "bar", "data": bar_data[::-1]}],
        }
        st_echarts(options=opts, height="400px", theme="streamlit")
    else:
        st.info("Aucune donnee fournisseurs.")


# ==========================================
# PAGE 7 : SIG EXPRESS
# ==========================================
elif page == "SIG Express":
    st.title(":chart_with_upwards_trend: SIG Express")

    sig_data = query_dicts(f"""
        SELECT entite_code, sig_solde,
            ROUND(SUM(sig_signe * (credit - debit))::numeric, 0) AS montant
        FROM grand_livre
        WHERE {where_no_an} AND sig_solde IS NOT NULL
        GROUP BY entite_code, sig_solde
        ORDER BY entite_code, sig_solde
    """)

    if not sig_data:
        st.warning("Aucune donnee SIG pour les filtres selectionnes.")
    else:
        # Group by structure
        structs = sorted(set(d['entite_code'] for d in sig_data))
        sig_soldes = [
            'Marge commerciale', 'Production de l\'exercice', 'Valeur ajoutee',
            'EBE', 'Resultat d\'exploitation', 'RCAI',
            'Resultat exceptionnel', 'Resultat de l\'exercice', 'CAF'
        ]

        series = []
        for struct in structs:
            vals = []
            for solde in sig_soldes:
                match = [d for d in sig_data if d['entite_code'] == struct and d['sig_solde'] == solde]
                vals.append(float(match[0]['montant']) if match else 0)
            series.append({"name": struct, "type": "bar", "data": vals})

        opts = {
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"},
                        "valueFormatter": JS_FMT},
            "legend": {"bottom": 0},
            "grid": {"left": "3%", "right": "4%", "bottom": "12%", "containLabel": True},
            "yAxis": {"type": "category", "data": sig_soldes},
            "xAxis": {"type": "value"},
            "series": series,
        }
        st_echarts(options=opts, height="500px", theme="streamlit")

        # Table detail
        with st.expander("Detail par structure"):
            for struct in structs:
                st.write(f"**{struct}**")
                rows = [d for d in sig_data if d['entite_code'] == struct]
                for r in rows:
                    st.write(f"  {r['sig_solde']}: **{fmt(r['montant'])}**")


# ==========================================
# PAGE 3 : CRD EXPRESS
# ==========================================
elif page == "CRD Express":
    st.title(":chart_with_downwards_trend: CRD Express")

    crd_data = query_dicts(f"""
        SELECT entite_code, annee, trimestre,
            SUM(CASE WHEN crd_categorie = 'Chiffre d''affaires' THEN crd_signe * (credit - debit) ELSE 0 END) AS ca,
            SUM(CASE WHEN crd_categorie = 'Charges variables' THEN crd_signe * (credit - debit) ELSE 0 END) AS charges_var,
            SUM(CASE WHEN crd_categorie = 'Charges fixes exploitation' THEN crd_signe * (credit - debit) ELSE 0 END) AS charges_fixes
        FROM grand_livre
        WHERE {where_no_an} AND crd_categorie IS NOT NULL
        GROUP BY entite_code, annee, trimestre
        ORDER BY entite_code, annee, trimestre
    """)

    if not crd_data:
        st.warning("Aucune donnee CRD pour les filtres selectionnes.")
    else:
        for d in crd_data:
            d['ca'] = float(d['ca'] or 0)
            d['charges_var'] = float(d['charges_var'] or 0)
            d['charges_fixes'] = float(d['charges_fixes'] or 0)
            d['mcv'] = d['ca'] - d['charges_var']
            d['resultat'] = d['mcv'] - d['charges_fixes']
            d['taux_mcv'] = round(d['mcv'] / d['ca'] * 100, 1) if d['ca'] else 0
            d['seuil'] = round(d['charges_fixes'] / (d['taux_mcv'] / 100), 0) if d['taux_mcv'] else 0

        # KPI cards
        total_ca = sum(d['ca'] for d in crd_data)
        total_mcv = sum(d['mcv'] for d in crd_data)
        total_res = sum(d['resultat'] for d in crd_data)
        taux_global = round(total_mcv / total_ca * 100, 1) if total_ca else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("CA", fmt(total_ca))
        c2.metric("MCV", fmt(total_mcv))
        c3.metric("Taux MCV", f"{taux_global}%")
        c4.metric("Resultat", fmt(total_res))

        # Waterfall-like chart
        labels = ['CA', 'Charges var.', 'MCV', 'Charges fixes', 'Resultat']
        waterfall = [
            {"value": total_ca, "itemStyle": {"color": "#91cc75"}},
            {"value": -sum(d['charges_var'] for d in crd_data), "itemStyle": {"color": "#ee6666"}},
            {"value": total_mcv, "itemStyle": {"color": "#5470c6"}},
            {"value": -sum(d['charges_fixes'] for d in crd_data), "itemStyle": {"color": "#ee6666"}},
            {"value": total_res, "itemStyle": {"color": "#73c0de" if total_res >= 0 else "#ee6666"}},
        ]

        opts = {
            "tooltip": {"trigger": "axis",
                        "valueFormatter": JS_FMT},
            "xAxis": {"type": "category", "data": labels},
            "yAxis": {"type": "value"},
            "series": [{"type": "bar", "data": waterfall, "label": {"show": True, "position": "top",
                        "formatter": JsCode("function(p){return Math.round(p.value).toLocaleString()}")}}],
        }
        st_echarts(options=opts, height="400px", theme="streamlit")

        # Seuil de rentabilite
        total_cf = sum(d['charges_fixes'] for d in crd_data)
        seuil = round(total_cf / (taux_global / 100), 0) if taux_global else 0
        point_mort = round(seuil / total_ca * 365, 0) if total_ca else 0
        marge_secu = total_ca - seuil

        st.subheader("Seuil de rentabilite")
        c1, c2, c3 = st.columns(3)
        c1.metric("Seuil de rentabilite", fmt(seuil))
        c2.metric("Point mort", f"{point_mort:.0f} jours")
        c3.metric("Marge de securite", fmt(marge_secu),
                   delta=f"{round(marge_secu/total_ca*100,1) if total_ca else 0}%")


# ==========================================
# PAGE 4 : EXPLORATION GL
# ==========================================
elif page == "Exploration GL":
    st.title(":mag: Exploration Grand Livre")

    col1, col2 = st.columns(2)
    with col1:
        compte_filter = st.text_input("Filtre compte (ex: 70, 411, 512)", "")
    with col2:
        limit = st.slider("Nb lignes", 10, 500, 100)

    where_gl = where
    if compte_filter:
        where_gl += f" AND compte_numero LIKE '{compte_filter}%'"

    data = query_dicts(f"""
        SELECT entite_code, exercice_label, ecriture_date, journal_code,
            compte_numero, compte_libelle, ecriture_lib, debit, credit, solde,
            is_a_nouveau
        FROM grand_livre
        WHERE {where_gl}
        ORDER BY ecriture_date DESC, id DESC
        LIMIT {limit}
    """)

    if data:
        st.dataframe(data, use_container_width=True)

        # Agregation par compte
        st.subheader("Solde par compte")
        agg = query_dicts(f"""
            SELECT compte_numero, compte_libelle,
                SUM(debit) AS total_d, SUM(credit) AS total_c,
                SUM(solde) AS solde
            FROM grand_livre WHERE {where_gl}
            GROUP BY compte_numero, compte_libelle
            ORDER BY ABS(SUM(solde)) DESC LIMIT 20
        """)
        if agg:
            comptes = [f"{d['compte_numero']}" for d in agg]
            soldes = [float(d['solde']) for d in agg]

            bar_data = []
            for v in soldes:
                bar_data.append({"value": round(v, 0),
                                 "itemStyle": {"color": "#5470c6" if v >= 0 else "#ee6666"}})

            opts = {
                "tooltip": {"trigger": "axis"},
                "yAxis": {"type": "category", "data": comptes[::-1]},
                "xAxis": {"type": "value"},
                "grid": {"left": "3%", "right": "4%", "containLabel": True},
                "series": [{"type": "bar", "data": bar_data[::-1]}],
            }
            st_echarts(options=opts, height="500px", theme="streamlit")
    else:
        st.info("Aucune ecriture trouvee.")


# ==========================================
# PAGE 5 : CONTROLES QUALITE
# ==========================================
elif page == "Controles qualite":
    st.title(":shield: Controles qualite")

    # Coherence
    st.subheader("Controles de coherence")
    coherence = query_dicts("SELECT * FROM v_controles_coherence")
    for c in coherence:
        icon = ":white_check_mark:" if c['statut'] == 'OK' else ":x:"
        st.write(f"{icon} **{c['controle']}** — {c['nb_anomalies']} anomalie(s)")

    # Equilibre par exercice
    st.subheader("Equilibre D/C par structure/exercice")
    eq_data = query_dicts(f"""
        SELECT entite_code, exercice_label,
            ROUND(SUM(debit)::numeric, 2) AS total_d,
            ROUND(SUM(credit)::numeric, 2) AS total_c,
            ROUND(ABS(SUM(debit) - SUM(credit))::numeric, 2) AS ecart
        FROM grand_livre WHERE {where}
        GROUP BY entite_code, exercice_label
        ORDER BY entite_code, exercice_label
    """)
    if eq_data:
        st.dataframe(eq_data, use_container_width=True)

    # Comptes d'attente
    st.subheader("Comptes d'attente (47x, 580)")
    attente = query_dicts(f"""
        SELECT entite_code, exercice_label, compte_numero, compte_libelle,
            ROUND(SUM(solde)::numeric, 2) AS solde
        FROM grand_livre
        WHERE (compte_numero LIKE '47%' OR compte_numero = '580') AND {where}
        GROUP BY entite_code, exercice_label, compte_numero, compte_libelle
        HAVING ABS(SUM(solde)) > 0.01
        ORDER BY entite_code, exercice_label
    """)
    if attente:
        st.dataframe(attente, use_container_width=True)
    else:
        st.success("Aucun compte d'attente non solde.")

    # GL vs Pennylane
    st.subheader("Controle GL vs Pennylane")
    resume = query_dicts("SELECT * FROM v_controle_resume")
    if resume:
        st.dataframe(resume, use_container_width=True)


# ==========================================
# PAGE 6 : REQUETE SQL
# ==========================================
elif page == "Requete SQL":
    st.title(":keyboard: Requete SQL libre")
    st.caption("Lecture seule — SELECT uniquement")

    sql_input = st.text_area("SQL", value="SELECT entite_code, COUNT(*) AS nb\nFROM grand_livre\nGROUP BY entite_code\nORDER BY nb DESC", height=150)

    if st.button("Executer"):
        if sql_input.strip().upper().startswith("SELECT"):
            try:
                data = query_dicts(sql_input)
                if data:
                    st.dataframe(data, use_container_width=True)
                    st.caption(f"{len(data)} ligne(s)")
                else:
                    st.info("0 ligne retournee.")
            except Exception as e:
                st.error(f"Erreur SQL: {e}")
        else:
            st.error("Seules les requetes SELECT sont autorisees.")
