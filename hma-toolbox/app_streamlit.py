"""
HMA Toolbox — Streamlit Dashboard
Checks rapides, exploration GL, controles qualite, SIG/CRD express.

Usage local  : streamlit run hma-toolbox/app_streamlit.py
Usage Docker : streamlit run /app/app_streamlit.py --server.port 8501 --server.address 0.0.0.0
"""
import os
import streamlit as st
import pg8000
from streamlit_echarts import st_echarts, JsCode

st.set_page_config(
    page_title="HMA Toolbox",
    page_icon=":bar_chart:",
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

structures = ['Toutes', 'HMA', 'STIVMAT', 'STA', 'ETPA']
selected_structure = st.sidebar.selectbox("Structure", structures)

exercices_data = query_dicts(
    "SELECT DISTINCT exercice_label FROM grand_livre ORDER BY exercice_label DESC"
)
exercice_options = ['Tous'] + [r['exercice_label'] for r in exercices_data]
selected_exercice = st.sidebar.selectbox("Exercice", exercice_options)

# Build WHERE clause
def build_where():
    clauses = ["1=1"]
    if selected_structure != 'Toutes':
        clauses.append(f"entite_code = '{selected_structure}'")
    if selected_exercice != 'Tous':
        clauses.append(f"exercice_label = '{selected_exercice}'")
    return " AND ".join(clauses)

where = build_where()
where_no_an = f"{where} AND NOT is_a_nouveau"

page = st.sidebar.radio("Page", [
    "Tableau de bord",
    "SIG Express",
    "CRD Express",
    "Exploration GL",
    "Controles qualite",
    "Requete SQL",
])

st.sidebar.markdown("---")
st.sidebar.caption("HMA Gestion — Guyane")


# ==========================================
# PAGE 1 : TABLEAU DE BORD
# ==========================================
if page == "Tableau de bord":
    st.title(":bar_chart: Tableau de bord")

    # KPIs
    nb_ecritures = query_single(f"SELECT COUNT(*) FROM grand_livre WHERE {where}")
    nb_comptes = query_single(f"SELECT COUNT(DISTINCT compte_numero) FROM grand_livre WHERE {where}")
    total_debit = query_single(f"SELECT COALESCE(SUM(debit), 0) FROM grand_livre WHERE {where}")
    total_credit = query_single(f"SELECT COALESCE(SUM(credit), 0) FROM grand_livre WHERE {where}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ecritures", f"{nb_ecritures:,}")
    c2.metric("Comptes", f"{nb_comptes:,}")
    c3.metric("Total Debit", f"{total_debit:,.0f} EUR")
    c4.metric("Total Credit", f"{total_credit:,.0f} EUR")

    # Resultat par structure
    st.subheader("Resultat net par structure")
    data = query_dicts(f"""
        SELECT entite_code,
            ROUND(SUM(CASE WHEN classe = 7 THEN credit - debit ELSE 0 END)::numeric, 0) AS produits,
            ROUND(SUM(CASE WHEN classe = 6 THEN debit - credit ELSE 0 END)::numeric, 0) AS charges,
            ROUND(SUM(CASE WHEN classe = 7 THEN credit - debit ELSE 0 END)
                - SUM(CASE WHEN classe = 6 THEN debit - credit ELSE 0 END), 0) AS resultat
        FROM grand_livre WHERE {where_no_an}
        GROUP BY entite_code ORDER BY entite_code
    """)

    if data:
        codes = [d['entite_code'] for d in data]
        produits = [float(d['produits']) for d in data]
        charges = [float(d['charges']) for d in data]
        resultats = [float(d['resultat']) for d in data]

        opts = {
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"},
                        "valueFormatter": JsCode("function(v){return Math.round(v).toLocaleString()+' EUR'}")},
            "legend": {"bottom": 0},
            "grid": {"bottom": "15%", "containLabel": True},
            "xAxis": {"type": "category", "data": codes},
            "yAxis": {"type": "value"},
            "series": [
                {"name": "Produits", "type": "bar", "stack": "total", "data": produits,
                 "itemStyle": {"color": "#91cc75"}},
                {"name": "Charges", "type": "bar", "stack": "total",
                 "data": [-c for c in charges], "itemStyle": {"color": "#ee6666"}},
                {"name": "Resultat", "type": "line", "data": resultats,
                 "itemStyle": {"color": "#5470c6"}, "lineStyle": {"width": 3}},
            ],
        }
        st_echarts(options=opts, height="400px", theme="streamlit")

    # CA mensuel
    st.subheader("CA mensuel (comptes 70x)")
    ca_data = query_dicts(f"""
        SELECT mois_label, ROUND(SUM(credit - debit)::numeric, 0) AS ca
        FROM grand_livre
        WHERE {where_no_an} AND compte_numero LIKE '70%'
        GROUP BY mois_label, annee, mois
        ORDER BY annee, mois
    """)

    if ca_data:
        mois = [d['mois_label'] for d in ca_data]
        ca_vals = [float(d['ca']) for d in ca_data]

        bar_data = []
        for v in ca_vals:
            color = "#91cc75" if v >= 0 else "#ee6666"
            bar_data.append({"value": v, "itemStyle": {"color": color}})

        ca_opts = {
            "tooltip": {"trigger": "axis",
                        "valueFormatter": JsCode("function(v){return Math.round(v).toLocaleString()+' EUR'}")},
            "xAxis": {"type": "category", "data": mois, "axisLabel": {"rotate": 45}},
            "yAxis": {"type": "value"},
            "dataZoom": [{"type": "inside"}, {"type": "slider", "height": 20, "bottom": 5}],
            "grid": {"bottom": "18%", "containLabel": True},
            "series": [{"type": "bar", "data": bar_data}],
        }
        st_echarts(options=ca_opts, height="350px", theme="streamlit")

    # Sync status
    st.subheader("Etat synchronisation")
    sync = query_dicts("""
        SELECT e.code, sm.status, sm.last_sync_at, sm.row_count_local
        FROM sync_metadata sm JOIN entite e ON e.id = sm.entite_id
        WHERE sm.endpoint = 'ledger_entry_lines'
        ORDER BY e.code
    """)
    if sync:
        for s in sync:
            icon = ":white_check_mark:" if s['status'] == 'done' else ":warning:"
            st.write(f"{icon} **{s['code']}** — {s['row_count_local']} lignes — dernier sync: {s['last_sync_at']}")


# ==========================================
# PAGE 2 : SIG EXPRESS
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
                        "valueFormatter": JsCode("function(v){return Math.round(v).toLocaleString()+' EUR'}")},
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
                    st.write(f"  {r['sig_solde']}: **{float(r['montant']):,.0f} EUR**")


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
        c1.metric("CA", f"{total_ca:,.0f} EUR")
        c2.metric("MCV", f"{total_mcv:,.0f} EUR")
        c3.metric("Taux MCV", f"{taux_global}%")
        c4.metric("Resultat", f"{total_res:,.0f} EUR")

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
                        "valueFormatter": JsCode("function(v){return Math.round(v).toLocaleString()+' EUR'}")},
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
        c1.metric("Seuil de rentabilite", f"{seuil:,.0f} EUR")
        c2.metric("Point mort", f"{point_mort:.0f} jours")
        c3.metric("Marge de securite", f"{marge_secu:,.0f} EUR",
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
