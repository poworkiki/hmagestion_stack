#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crée 3 dashboards Superset : GL + BG (3 approches)
  Dashboard 1 — Pivot Table + Drill to Detail
  Dashboard 2 — Cross-filter Balance ↔ Grand Livre
  Dashboard 3 — Vue combinée + Drill By
"""
import json, os, sys, urllib.request, urllib.error

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://superset.hma.business'

# Dataset IDs
DS_BG_DISPLAY = 13     # v_bg_display
DS_BG_MENSUELLE = 14   # v_bg_mensuelle
DS_GL_DISPLAY = 15     # v_gl_display
DS_GL_BG_COMBINED = 16 # v_gl_bg_combined


def load_env():
    env = {}
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    return env


class SupersetAPI:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.jwt = None
        self.csrf = None
        self.cookies = {}
        self._login(username, password)

    def _login(self, username, password):
        import http.cookiejar
        self.cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        # Login
        data = json.dumps({"username": username, "password": password, "provider": "db"}).encode()
        req = urllib.request.Request(f'{self.base_url}/api/v1/security/login',
                                     data=data, headers={'Content-Type': 'application/json'})
        resp = opener.open(req)
        self.jwt = json.loads(resp.read()).get('access_token')
        # CSRF
        req = urllib.request.Request(f'{self.base_url}/api/v1/security/csrf_token/',
                                     headers={'Authorization': f'Bearer {self.jwt}'})
        resp = opener.open(req)
        self.csrf = json.loads(resp.read()).get('result')
        self.opener = opener
        print(f'  Auth OK (JWT: {self.jwt[:20]}...)')

    def post(self, endpoint, payload):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f'{self.base_url}{endpoint}', data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.jwt}',
                'X-CSRFToken': self.csrf,
                'Referer': f'{self.base_url}/',
            })
        try:
            resp = self.opener.open(req)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:500]
            print(f'  ERROR {e.code}: {body}')
            return {}

    def put(self, endpoint, payload):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f'{self.base_url}{endpoint}', data=data, method='PUT',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.jwt}',
                'X-CSRFToken': self.csrf,
                'Referer': f'{self.base_url}/',
            })
        try:
            resp = self.opener.open(req)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:500]
            print(f'  ERROR {e.code}: {body}')
            return {}

    def create_chart(self, name, viz_type, datasource_id, params):
        payload = {
            "slice_name": name,
            "viz_type": viz_type,
            "datasource_id": datasource_id,
            "datasource_type": "table",
            "params": json.dumps(params),
        }
        result = self.post('/api/v1/chart/', payload)
        chart_id = result.get('id')
        print(f'  Chart "{name}" → id={chart_id}')
        return chart_id

    def create_dashboard(self, title, slug, charts, layout_type='grid'):
        # Create dashboard
        payload = {"dashboard_title": title, "slug": slug, "published": True}
        result = self.post('/api/v1/dashboard/', payload)
        dash_id = result.get('id')
        print(f'  Dashboard "{title}" → id={dash_id}')

        if not dash_id or not charts:
            return dash_id

        # Build position JSON
        position = {"DASHBOARD_VERSION_KEY": "v2"}
        root_children = []

        for i, chart_id in enumerate(charts):
            if chart_id is None:
                continue
            row_id = f"ROW-gl-{i}"
            chart_key = f"CHART-gl-{i}"
            row_children = [chart_key]

            position[row_id] = {
                "type": "ROW", "id": row_id,
                "children": row_children,
                "meta": {"background": "BACKGROUND_TRANSPARENT"}
            }
            position[chart_key] = {
                "type": "CHART", "id": chart_key,
                "children": [],
                "meta": {
                    "width": 12, "height": 60,
                    "chartId": chart_id,
                    "sliceName": f"chart-{chart_id}",
                }
            }
            root_children.append(row_id)

        position["ROOT_ID"] = {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]}
        position["GRID_ID"] = {"type": "GRID", "id": "GRID_ID", "children": root_children}
        position["HEADER_ID"] = {"type": "HEADER", "id": "HEADER_ID",
                                  "meta": {"text": title}}

        # Update dashboard with layout
        self.put(f'/api/v1/dashboard/{dash_id}', {
            "position_json": json.dumps(position),
            "json_metadata": json.dumps({
                "chart_configuration": {},
                "cross_filters_enabled": True,
                "native_filter_configuration": [
                    {
                        "id": "NATIVE_FILTER_ENT",
                        "name": "Entreprise",
                        "filterType": "filter_select",
                        "targets": [{"column": {"name": "entite_nom"}, "datasetId": charts[0] if charts else datasource_id}],
                        "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
                        "controlValues": {"enableEmptyFilter": False, "multiSelect": True},
                    },
                    {
                        "id": "NATIVE_FILTER_ANNEE",
                        "name": "Année",
                        "filterType": "filter_select",
                        "targets": [{"column": {"name": "annee"}, "datasetId": charts[0] if charts else datasource_id}],
                        "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
                        "controlValues": {"enableEmptyFilter": False, "multiSelect": False},
                    },
                ],
            }),
        })

        return dash_id


def create_dashboard_1(api):
    """Dashboard 1 — Pivot Table + Drill to Detail"""
    print('\n=== Dashboard 1 : Pivot + Drill to Detail ===')

    # Chart : Pivot Table BG mensuelle
    c1 = api.create_chart("BG — Pivot par mois", "pivot_table_v2", DS_BG_MENSUELLE, {
        "groupbyColumns": ["mois_label"],
        "groupbyRows": ["classe", "compte_numero", "compte_libelle"],
        "metrics": [
            {"label": "Débit", "expressionType": "SQL", "sqlExpression": "SUM(total_debit)"},
            {"label": "Crédit", "expressionType": "SQL", "sqlExpression": "SUM(total_credit)"},
            {"label": "Solde Débiteur", "expressionType": "SQL", "sqlExpression": "SUM(GREATEST(total_debit - total_credit, 0))"},
            {"label": "Solde Créditeur", "expressionType": "SQL", "sqlExpression": "SUM(GREATEST(total_credit - total_debit, 0))"},
        ],
        "adhoc_filters": [
            {"clause": "WHERE", "comparator": "2026", "expressionType": "SIMPLE",
             "operator": "==", "subject": "annee"},
        ],
        "valueFormat": ",.2f",
        "colTotals": True,
        "rowTotals": True,
        "transposePivot": False,
        "combineMetric": False,
        "rowOrder": "key_a_to_z",
        "colOrder": "key_a_to_z",
    })

    # Chart : Table BG annuelle (résumé)
    c2 = api.create_chart("BG — Résumé annuel", "table", DS_BG_DISPLAY, {
        "groupby": ["classe", "compte_numero", "compte_libelle"],
        "metrics": [
            {"label": "Débit", "expressionType": "SQL", "sqlExpression": "SUM(total_debit)"},
            {"label": "Crédit", "expressionType": "SQL", "sqlExpression": "SUM(total_credit)"},
            {"label": "Solde Débiteur", "expressionType": "SQL", "sqlExpression": "SUM(solde_debiteur)"},
            {"label": "Solde Créditeur", "expressionType": "SQL", "sqlExpression": "SUM(solde_crediteur)"},
        ],
        "adhoc_filters": [
            {"clause": "WHERE", "comparator": "2026", "expressionType": "SIMPLE",
             "operator": "==", "subject": "annee"},
        ],
        "order_by_cols": [["classe", True], ["compte_numero", True]],
        "row_limit": 500,
        "include_time": False,
    })

    dash_id = api.create_dashboard(
        "1 — BG Pivot + Drill to Detail",
        "bg-pivot-drill",
        [c1, c2])

    return dash_id


def create_dashboard_2(api):
    """Dashboard 2 — Cross-filter Balance ↔ Grand Livre"""
    print('\n=== Dashboard 2 : Cross-filter BG ↔ GL ===')

    # Chart 1 : Balance Générale (table cliquable → émet cross-filter)
    c1 = api.create_chart("Balance Générale (cliquer pour filtrer)", "table", DS_BG_DISPLAY, {
        "groupby": ["classe", "compte_numero", "compte_libelle"],
        "metrics": [
            {"label": "Débit", "expressionType": "SQL", "sqlExpression": "SUM(total_debit)"},
            {"label": "Crédit", "expressionType": "SQL", "sqlExpression": "SUM(total_credit)"},
            {"label": "SD", "expressionType": "SQL", "sqlExpression": "SUM(solde_debiteur)"},
            {"label": "SC", "expressionType": "SQL", "sqlExpression": "SUM(solde_crediteur)"},
        ],
        "adhoc_filters": [
            {"clause": "WHERE", "comparator": "2026", "expressionType": "SIMPLE",
             "operator": "==", "subject": "annee"},
        ],
        "emit_filter": True,
        "row_limit": 500,
        "order_by_cols": [["classe", True], ["compte_numero", True]],
        "table_timestamp_format": "smart_date",
        "conditional_formatting": [
            {"column": "SD", "colorScheme": "#ACE1C4", "operator": ">", "targetValue": 0},
            {"column": "SC", "colorScheme": "#FDE380", "operator": ">", "targetValue": 0},
        ],
    })

    # Chart 2 : Grand Livre détail (reçoit le cross-filter)
    c2 = api.create_chart("Grand Livre — détail écritures", "table", DS_GL_DISPLAY, {
        "groupby": [],
        "all_columns": [
            "ecriture_date", "journal_code", "ecriture_num",
            "compte_numero", "compte_libelle",
            "ecriture_lib", "debit", "credit", "solde_cumule",
            "type_ecriture", "piece_ref",
        ],
        "adhoc_filters": [
            {"clause": "WHERE", "comparator": "2026", "expressionType": "SIMPLE",
             "operator": "==", "subject": "annee"},
        ],
        "order_by_cols": [["ecriture_date", True], ["ecriture_num", True]],
        "row_limit": 200,
        "table_timestamp_format": "%d/%m/%Y",
        "emit_filter": False,
    })

    dash_id = api.create_dashboard(
        "2 — BG ↔ GL Cross-filter",
        "bg-gl-crossfilter",
        [c1, c2])

    return dash_id


def create_dashboard_3(api):
    """Dashboard 3 — Vue combinée + Drill By"""
    print('\n=== Dashboard 3 : Vue combinée + Drill By ===')

    # Chart 1 : Table agrégée par compte (drill by vers écritures)
    c1 = api.create_chart("BG+GL — Drill By compte → écritures", "table", DS_GL_BG_COMBINED, {
        "groupby": ["classe", "compte_numero", "compte_libelle"],
        "metrics": [
            {"label": "Débit", "expressionType": "SQL", "sqlExpression": "SUM(debit)"},
            {"label": "Crédit", "expressionType": "SQL", "sqlExpression": "SUM(credit)"},
            {"label": "SD", "expressionType": "SQL", "sqlExpression": "GREATEST(SUM(debit) - SUM(credit), 0)"},
            {"label": "SC", "expressionType": "SQL", "sqlExpression": "GREATEST(SUM(credit) - SUM(debit), 0)"},
            {"label": "Nb écritures", "expressionType": "SQL", "sqlExpression": "COUNT(*)"},
        ],
        "adhoc_filters": [
            {"clause": "WHERE", "comparator": "2026", "expressionType": "SIMPLE",
             "operator": "==", "subject": "annee"},
        ],
        "row_limit": 500,
        "order_by_cols": [["classe", True], ["compte_numero", True]],
        "emit_filter": True,
    })

    # Chart 2 : Barres par classe comptable
    c2 = api.create_chart("Répartition par classe", "echarts_timeseries_bar", DS_GL_BG_COMBINED, {
        "x_axis": "classe",
        "metrics": [
            {"label": "Débit", "expressionType": "SQL", "sqlExpression": "SUM(debit)"},
            {"label": "Crédit", "expressionType": "SQL", "sqlExpression": "SUM(credit)"},
        ],
        "groupby": [],
        "adhoc_filters": [
            {"clause": "WHERE", "comparator": "2026", "expressionType": "SIMPLE",
             "operator": "==", "subject": "annee"},
            {"clause": "WHERE", "comparator": "true", "expressionType": "SIMPLE",
             "operator": "!=", "subject": "is_a_nouveau"},
        ],
        "show_legend": True,
        "y_axis_format": ",.0f",
        "rich_tooltip": True,
    })

    # Chart 3 : Evolution mensuelle
    c3 = api.create_chart("Evolution mensuelle débit/crédit", "echarts_timeseries_bar", DS_GL_BG_COMBINED, {
        "x_axis": "mois_label",
        "metrics": [
            {"label": "Débit", "expressionType": "SQL", "sqlExpression": "SUM(debit)"},
            {"label": "Crédit", "expressionType": "SQL", "sqlExpression": "SUM(credit)"},
        ],
        "groupby": [],
        "adhoc_filters": [
            {"clause": "WHERE", "comparator": "2026", "expressionType": "SIMPLE",
             "operator": "==", "subject": "annee"},
            {"clause": "WHERE", "comparator": "true", "expressionType": "SIMPLE",
             "operator": "!=", "subject": "is_a_nouveau"},
        ],
        "show_legend": True,
        "y_axis_format": ",.0f",
    })

    dash_id = api.create_dashboard(
        "3 — BG+GL Drill By",
        "bg-gl-drillby",
        [c1, c2, c3])

    return dash_id


def main():
    env = load_env()
    password = env.get('SUPERSET_ADMIN_PASSWORD')
    if not password:
        print('SUPERSET_ADMIN_PASSWORD manquant dans .env')
        sys.exit(1)

    print('Auth Superset...')
    api = SupersetAPI(BASE, 'admin', password)

    d1 = create_dashboard_1(api)
    d2 = create_dashboard_2(api)
    d3 = create_dashboard_3(api)

    print(f'\n=== TERMINÉ ===')
    print(f'  Dashboard 1 (Pivot+Drill) : {BASE}/superset/dashboard/bg-pivot-drill/')
    print(f'  Dashboard 2 (Cross-filter) : {BASE}/superset/dashboard/bg-gl-crossfilter/')
    print(f'  Dashboard 3 (Drill By)     : {BASE}/superset/dashboard/bg-gl-drillby/')


if __name__ == '__main__':
    main()
