#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Superset charts — génère le query_context manquant pour que les charts
créés par API s'affichent sur les dashboards.
"""
import json, os, sys, urllib.request, urllib.error, http.cookiejar

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://superset.hma.business'

# Charts à fixer (id → dashboard)
CHARTS = {
    53: 'BG Pivot par mois',
    54: 'BG Resume annuel',
    55: 'Balance Generale (cliquer pour filtrer)',
    56: 'Grand Livre detail ecritures',
    57: 'BG+GL Drill By',
    58: 'Repartition par classe',
    59: 'Evolution mensuelle',
}


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


def main():
    env = load_env()
    pw = env.get('SUPERSET_ADMIN_PASSWORD')

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # Login
    data = json.dumps({"username": "admin", "password": pw, "provider": "db"}).encode()
    req = urllib.request.Request(f'{BASE}/api/v1/security/login',
                                 data=data, headers={'Content-Type': 'application/json'})
    resp = opener.open(req)
    jwt = json.loads(resp.read()).get('access_token')

    # CSRF
    req = urllib.request.Request(f'{BASE}/api/v1/security/csrf_token/',
                                 headers={'Authorization': f'Bearer {jwt}'})
    resp = opener.open(req)
    csrf = json.loads(resp.read()).get('result')
    print(f'Auth OK')

    for chart_id, name in CHARTS.items():
        # 1. Get chart details
        req = urllib.request.Request(f'{BASE}/api/v1/chart/{chart_id}',
                                     headers={'Authorization': f'Bearer {jwt}'})
        try:
            resp = opener.open(req)
            chart = json.loads(resp.read()).get('result', {})
        except urllib.error.HTTPError as e:
            print(f'  Chart {chart_id} ERROR: {e.code}')
            continue

        ds_id = chart.get('datasource_id')
        ds_type = chart.get('datasource_type', 'table')
        viz_type = chart.get('viz_type')
        params = json.loads(chart.get('params', '{}'))

        # 2. Build query_context based on viz_type
        if viz_type == 'pivot_table_v2':
            columns = params.get('groupbyColumns', [])
            rows = params.get('groupbyRows', [])
            metrics = params.get('metrics', [])
            filters = params.get('adhoc_filters', [])

            qc = {
                "datasource": {"id": ds_id, "type": ds_type},
                "force": False,
                "queries": [{
                    "columns": [{"sqlExpression": c, "label": c, "expressionType": "SQL"} if isinstance(c, dict) else c for c in columns + rows],
                    "metrics": metrics,
                    "filters": [],
                    "row_limit": params.get('row_limit', 10000),
                    "order_desc": True,
                }],
                "form_data": params,
                "result_format": "json",
                "result_type": "full",
            }

        elif viz_type == 'table':
            groupby = params.get('groupby', [])
            all_columns = params.get('all_columns', [])
            metrics = params.get('metrics', [])

            query = {
                "row_limit": params.get('row_limit', 200),
                "order_desc": True,
            }
            if all_columns:
                query["columns"] = all_columns
            else:
                query["columns"] = groupby
                query["metrics"] = metrics

            qc = {
                "datasource": {"id": ds_id, "type": ds_type},
                "force": False,
                "queries": [query],
                "form_data": params,
                "result_format": "json",
                "result_type": "full",
            }

        elif viz_type == 'echarts_timeseries_bar':
            qc = {
                "datasource": {"id": ds_id, "type": ds_type},
                "force": False,
                "queries": [{
                    "columns": [params.get('x_axis', '')] + params.get('groupby', []),
                    "metrics": params.get('metrics', []),
                    "row_limit": params.get('row_limit', 10000),
                    "order_desc": True,
                }],
                "form_data": params,
                "result_format": "json",
                "result_type": "full",
            }
        else:
            print(f'  Chart {chart_id} ({name}): viz_type={viz_type} non gere, skip')
            continue

        # 3. PUT query_context
        payload = {"query_context": json.dumps(qc)}
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f'{BASE}/api/v1/chart/{chart_id}', data=data, method='PUT',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {jwt}',
                'X-CSRFToken': csrf,
                'Referer': f'{BASE}/',
            })
        try:
            resp = opener.open(req)
            print(f'  Chart {chart_id} ({name}): query_context SET OK')
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            print(f'  Chart {chart_id} ({name}): ERROR {e.code} - {body}')


if __name__ == '__main__':
    main()
