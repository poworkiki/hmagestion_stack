"""
Sync Pennylane -> PostgreSQL (4 structures FEC)

ETL : fetch /ledger_entry_lines, staging, upsert idempotent, resolve pcg, refresh vues.

Usage (dans le container hma-toolbox) :
    python scripts/sync-pennylane.py                    # Sync les 4 structures
    python scripts/sync-pennylane.py --structure HMA    # Sync une seule structure
    python scripts/sync-pennylane.py --full             # Force full fetch

Env vars requises (injectees par Coolify) :
    PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DATABASE
    PENNYLANE_TOKEN_HMA, PENNYLANE_TOKEN_STIVMAT, PENNYLANE_TOKEN_STA, PENNYLANE_TOKEN_ETPA
"""
import json, hashlib, os, sys, time, argparse
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import pg8000

# === Configuration ===
PENNYLANE_BASE_URL = 'https://app.pennylane.com/api/external/v2'
PAUSE_BETWEEN_STRUCTURES = 5
PAUSE_ON_429 = 30
MAX_RETRIES = 5
BATCH_SIZE = 500
LIMIT_PER_PAGE = 100


def log(msg):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}', flush=True)


def get_pg_conn():
    """Connexion PostgreSQL directe (reseau Docker interne)."""
    conn = pg8000.connect(
        host=os.environ.get('PG_HOST', 'postgresql_hma'),
        port=int(os.environ.get('PG_PORT', '5432')),
        database=os.environ.get('PG_DATABASE', 'postgres'),
        user=os.environ.get('PG_USER', 'postgres'),
        password=os.environ['PG_PASSWORD'],
    )
    conn.autocommit = True
    return conn


def get_tokens():
    """Recupere les tokens Pennylane depuis les env vars."""
    tokens = {}
    for code in ['HMA', 'STIVMAT', 'STA', 'ETPA']:
        key = f'PENNYLANE_TOKEN_{code}'
        if os.environ.get(key):
            tokens[code] = os.environ[key]
    return tokens


def pennylane_fetch(token, endpoint, params=None):
    """Fetch une page de l'API Pennylane avec retry sur 429."""
    url = f'{PENNYLANE_BASE_URL}{endpoint}'
    if params:
        url += '?' + '&'.join(f'{k}={v}' for k, v in params.items())

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
    }

    for attempt in range(MAX_RETRIES):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            if e.code == 429:
                wait = PAUSE_ON_429 * (attempt + 1)
                log(f'  429 rate limit, pause {wait}s (retry {attempt + 1}/{MAX_RETRIES})')
                time.sleep(wait)
                continue
            elif e.code == 401:
                raise Exception(f'Token invalide (401)')
            else:
                body = e.read().decode()[:200] if e.readable() else ''
                raise Exception(f'HTTP {e.code}: {body}')

    raise Exception(f'Rate limit persistant apres {MAX_RETRIES} retries')


def pennylane_fetch_all(token, endpoint, params=None):
    """Pagination par curseur : fetch toutes les pages."""
    all_items = []
    cursor = None
    page = 0

    while True:
        p = dict(params or {})
        p['limit'] = LIMIT_PER_PAGE
        if cursor:
            p['cursor'] = cursor

        data = pennylane_fetch(token, endpoint, p)
        items = data.get('items', [])
        all_items.extend(items)
        page += 1

        has_more = data.get('has_more', False)
        cursor = data.get('next_cursor')

        if page % 50 == 0 or not has_more:
            log(f'  page {page}: total {len(all_items)} items (has_more: {has_more})')

        if not has_more or not cursor:
            break

    return all_items


def sync_structure(conn, code, token, full_fetch=False):
    """Sync complete d'une structure : fetch -> staging -> upsert -> resolve."""
    log(f'=== Sync {code} ===')
    cursor = conn.cursor()
    t0 = time.time()

    # 1. Resolve IDs
    cursor.execute(
        "SELECT e.id, ex.id FROM entite e "
        "JOIN exercice ex ON ex.entite_id = e.id AND ex.cloture = false "
        "WHERE e.code = %s ORDER BY ex.date_debut DESC LIMIT 1",
        (code,)
    )
    row = cursor.fetchone()
    if not row:
        log(f'  Entite/exercice non trouve, skip')
        return {'code': code, 'nb_lignes': 0, 'status': 'skip'}
    entite_id, exercice_id = str(row[0]), str(row[1])

    # 2. Delta sync : date du dernier import termine
    updated_since = None
    if not full_fetch:
        cursor.execute(
            "SELECT MAX(date_import) FROM fec_import "
            "WHERE entite_id = %s AND statut = 'termine'",
            (entite_id,)
        )
        last = cursor.fetchone()
        if last and last[0]:
            updated_since = last[0].strftime('%Y-%m-%dT%H:%M:%S')
            log(f'  Delta sync depuis {updated_since}')

    # 3. Pre-charger les journaux
    log(f'  Fetch journaux...')
    journals_raw = pennylane_fetch_all(token, '/journals')
    journal_map = {j['id']: {'code': j.get('code', '?'), 'label': j.get('label', '')} for j in journals_raw}
    log(f'  {len(journal_map)} journaux')

    # 4. Fetch ledger_entry_lines
    params = {}
    if updated_since:
        params['updated_since'] = updated_since

    log(f'  Fetch /ledger_entry_lines...')
    lines = pennylane_fetch_all(token, '/ledger_entry_lines', params)
    log(f'  {len(lines)} lignes recuperees')

    if not lines:
        log(f'  Aucune nouvelle ligne')
        return {'code': code, 'nb_lignes': 0, 'status': 'skip'}

    # 5. Create fec_import
    cursor.execute(
        "INSERT INTO fec_import (entite_id, exercice_id, source, statut, nb_lignes_brut) "
        "VALUES (%s, %s, 'pennylane', 'en_cours', %s) RETURNING id",
        (entite_id, exercice_id, len(lines))
    )
    import_id = str(cursor.fetchone()[0])

    # 6. Truncate staging
    cursor.execute("TRUNCATE TABLE _staging_fec")

    # 7. Map + Insert staging
    cols = ['entite_id', 'exercice_id', 'fec_import_id',
            'journal_code', 'journal_lib', 'ecriture_num', 'ecriture_date',
            'compte_num', 'compte_lib', 'comp_aux_num', 'comp_aux_lib',
            'piece_ref', 'piece_date', 'ecriture_lib',
            'debit', 'credit', 'ecriture_let', 'date_let', 'valid_date',
            'montant_devise', 'idevise', 'pcg_numero', 'hash_md5']
    placeholders = ', '.join(['%s'] * len(cols))
    insert_sql = f"INSERT INTO _staging_fec ({', '.join(cols)}) VALUES ({placeholders})"

    batch_n = 0
    for i in range(0, len(lines), BATCH_SIZE):
        batch = lines[i:i + BATCH_SIZE]
        for line in batch:
            compte_num = (line.get('ledger_account') or {}).get('number', '000')
            journal_id = (line.get('journal') or {}).get('id')
            journal = journal_map.get(journal_id, {'code': 'INCONNU', 'label': ''})
            ecriture_num = str((line.get('ledger_entry') or {}).get('id', ''))

            hash_input = f'{entite_id}{journal["code"]}{ecriture_num}{line.get("date", "")}{compte_num}{line.get("debit", 0)}{line.get("credit", 0)}'
            hash_md5 = hashlib.md5(hash_input.encode()).hexdigest()

            values = [
                entite_id, exercice_id, import_id,
                journal['code'], journal['label'], ecriture_num, line.get('date'),
                compte_num, compte_num, None, None,
                ecriture_num, line.get('date'), line.get('label', ''),
                float(line.get('debit', 0)), float(line.get('credit', 0)),
                None, None, None, None, None, None, hash_md5
            ]
            cursor.execute(insert_sql, values)

        batch_n += 1
        log(f'  staging batch {batch_n}: {min(i + BATCH_SIZE, len(lines))}/{len(lines)}')

    # 8. Upsert idempotent
    log(f'  Upsert staging -> fec_ecriture...')
    cursor.execute(
        f"INSERT INTO fec_ecriture ({', '.join(cols)}) "
        f"SELECT {', '.join(cols)} FROM _staging_fec "
        "ON CONFLICT (hash_md5) DO NOTHING"
    )

    # 9. Resolve pcg_numero
    log(f'  Resolve pcg_numero...')
    cursor.execute(
        "UPDATE fec_ecriture SET pcg_numero = resolve_compte(compte_num) "
        "WHERE pcg_numero IS NULL AND entite_id = %s",
        (entite_id,)
    )

    # 10. MAJ stats
    duree = round(time.time() - t0, 1)
    cursor.execute(
        "UPDATE fec_import SET "
        "nb_lignes_inserees = (SELECT COUNT(*) FROM fec_ecriture WHERE fec_import_id = %s), "
        "duree_secondes = %s, statut = 'termine' WHERE id = %s",
        (import_id, duree, import_id)
    )

    # Lire les stats finales
    cursor.execute(
        "SELECT nb_lignes_brut, nb_lignes_inserees FROM fec_import WHERE id = %s",
        (import_id,)
    )
    stats = cursor.fetchone()
    log(f'  {code} OK: {stats[0]} brut, {stats[1]} inserees, {duree}s')

    return {'code': code, 'nb_lignes': len(lines), 'nb_inserees': stats[1], 'duree': duree, 'status': 'ok'}


def main():
    parser = argparse.ArgumentParser(description='Sync Pennylane -> PostgreSQL')
    parser.add_argument('--structure', '-s', help='Sync une seule structure (HMA, STIVMAT, STA, ETPA)')
    parser.add_argument('--full', action='store_true', help='Force full fetch (pas de delta)')
    args = parser.parse_args()

    tokens = get_tokens()
    if not tokens:
        log('ERREUR: aucun token Pennylane dans les env vars (PENNYLANE_TOKEN_*)')
        sys.exit(1)
    log(f'Tokens: {list(tokens.keys())}')

    log('Connexion PostgreSQL...')
    conn = get_pg_conn()
    log('Connecte')

    structures = [args.structure.upper()] if args.structure else ['HMA', 'STIVMAT', 'STA', 'ETPA']
    results = []

    for i, code in enumerate(structures):
        if code not in tokens:
            log(f'Token manquant pour {code}, skip')
            continue

        if i > 0:
            log(f'Pause {PAUSE_BETWEEN_STRUCTURES}s...')
            time.sleep(PAUSE_BETWEEN_STRUCTURES)

        try:
            result = sync_structure(conn, code, tokens[code], full_fetch=args.full)
            results.append(result)
        except Exception as e:
            log(f'  ERREUR {code}: {e}')
            import traceback
            traceback.print_exc()
            results.append({'code': code, 'nb_lignes': 0, 'status': f'error: {e}'})

    # Refresh vues materialisees
    if any(r.get('status') == 'ok' for r in results):
        log('Refresh vues materialisees...')
        cursor = conn.cursor()
        cursor.execute('SELECT refresh_all_views();')
        log('Vues rafraichies')

    conn.close()

    log('\n=== Resume ===')
    total = 0
    for r in results:
        total += r.get('nb_lignes', 0)
        log(f'  {r["code"]}: {r.get("nb_lignes", 0)} lignes, {r.get("nb_inserees", "?")} inserees, status={r["status"]}')
    log(f'  Total: {total} lignes')


if __name__ == '__main__':
    main()
