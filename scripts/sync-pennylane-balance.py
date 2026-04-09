#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import trial_balance Pennylane → pennylane_balance (table de contrôle).
Compare avec le GL PostgreSQL pour détecter les écarts.

Usage:
  python3 scripts/sync-pennylane-balance.py
  python3 scripts/sync-pennylane-balance.py --structure STIVMAT
  python3 scripts/sync-pennylane-balance.py --year 2025
"""
import sys, os, json, time, hashlib, argparse
import urllib.request, urllib.error

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# --- Config ---
STRUCTURES = {
    'ETPA': 'PENNYLANE_TOKEN_ETPA',
    'HMA': 'PENNYLANE_TOKEN_HMA',
    'STA': 'PENNYLANE_TOKEN_STA',
    'STIVMAT': 'PENNYLANE_TOKEN_STIVMAT',
}
PL_BASE = 'https://app.pennylane.com/api/external/v2'

def load_env():
    env = {}
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    return env

def pl_fetch_all(token, endpoint, params=None):
    """Fetch all pages from Pennylane API."""
    if params is None: params = {}
    params['limit'] = '100'
    params['use_2026_api_changes'] = 'true'
    items = []
    cursor = None
    while True:
        p = dict(params)
        if cursor: p['cursor'] = cursor
        qs = '&'.join(f'{k}={v}' for k, v in p.items())
        url = f'{PL_BASE}{endpoint}?{qs}'
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            print(f'  HTTP {e.code}: {e.read().decode()[:200]}')
            break
        items.extend(data.get('items', []))
        if not data.get('has_more', False): break
        cursor = data.get('next_cursor')
        if not cursor: break
        time.sleep(0.25)
    return items

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--structure', type=str, help='Structure code (ETPA, HMA, STA, STIVMAT)')
    parser.add_argument('--year', type=int, default=2026, help='Année (default: 2026)')
    args = parser.parse_args()

    env = load_env()
    db_url = env.get('HMA_DB_URL')
    if not db_url:
        print('HMA_DB_URL manquant dans .env')
        sys.exit(1)

    # pg8000
    try:
        import pg8000
    except ImportError:
        print('pip install pg8000')
        sys.exit(1)

    # Parse DB URL
    import re
    m = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
    if not m:
        print(f'URL DB invalide: {db_url[:50]}...')
        sys.exit(1)
    user, password, host, port, dbname = m.groups()
    conn = pg8000.connect(user=user, password=password, host=host, port=int(port), database=dbname)
    conn.autocommit = True
    cursor = conn.cursor()

    period_start = f'{args.year}-01-01'
    period_end = f'{args.year}-12-31'

    structures = {args.structure: STRUCTURES[args.structure]} if args.structure else STRUCTURES

    for code, token_key in structures.items():
        token = env.get(token_key)
        if not token:
            print(f'  {code}: token manquant ({token_key})')
            continue

        print(f'\n=== {code} ({period_start} → {period_end}) ===')

        # Fetch trial_balance
        items = pl_fetch_all(token, '/trial_balance', {
            'period_start': period_start,
            'period_end': period_end,
        })
        print(f'  {len(items)} comptes récupérés')

        if not items:
            continue

        # Get entite_id
        cursor.execute("SELECT id FROM entite WHERE nom = %s", (code,))
        row = cursor.fetchone()
        if not row:
            print(f'  Entite {code} introuvable en base')
            continue
        entite_id = str(row[0])

        # Delete old balance for this period/entite
        cursor.execute(
            "DELETE FROM pennylane_balance WHERE entite_id = %s AND period_start = %s AND period_end = %s",
            (entite_id, period_start, period_end))

        # Insert
        inserted = 0
        for item in items:
            numero = str(item.get('number', ''))
            label = item.get('label', '')
            debits = float(item.get('debits', 0))
            credits = float(item.get('credits', 0))
            solde = credits - debits

            cursor.execute("""
                INSERT INTO pennylane_balance
                (entite_id, structure_code, period_start, period_end,
                 compte_numero, compte_libelle, total_debit, total_credit, solde)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (entite_id, period_start, period_end, compte_numero)
                DO UPDATE SET total_debit = EXCLUDED.total_debit,
                              total_credit = EXCLUDED.total_credit,
                              solde = EXCLUDED.solde,
                              compte_libelle = EXCLUDED.compte_libelle,
                              imported_at = now()
            """, (entite_id, code, period_start, period_end,
                  numero, label, debits, credits, solde))
            inserted += 1

        print(f'  {inserted} comptes importés')

    # Controle
    print('\n=== CONTROLE GL vs PENNYLANE ===')
    cursor.execute("SELECT * FROM v_controle_resume")
    cols = [d[0] for d in cursor.description]
    for row in cursor.fetchall():
        r = dict(zip(cols, row))
        print(f"  {r['structure_code']}: {r['nb_comptes']} comptes | "
              f"{r['nb_ok']} OK | {r['nb_arrondi']} arrondi | "
              f"{r['nb_ecart']} ECART | écart total: {r['ecart_total']}")

    # Detail ecarts
    cursor.execute("""
        SELECT structure_code, compte_numero, compte_libelle,
               ROUND(pl_solde::numeric, 2) AS pl, ROUND(gl_solde::numeric, 2) AS gl,
               ROUND(ecart_solde::numeric, 2) AS ecart
        FROM v_controle_balance
        WHERE statut = 'ECART'
        ORDER BY ABS(ecart_solde) DESC LIMIT 20
    """)
    ecarts = cursor.fetchall()
    if ecarts:
        print(f'\n  Top écarts:')
        for row in ecarts:
            print(f'    {row[0]} {row[1]} {row[2][:30]:<30} PL={row[3]:>12} GL={row[4]:>12} Ecart={row[5]:>12}')
    else:
        print('\n  Aucun écart détecté ✓')

    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()
