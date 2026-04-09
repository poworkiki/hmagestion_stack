"""
Sync Pennylane -> PostgreSQL (4 structures FEC)

ETL : fetch /ledger_entry_lines, staging, upsert idempotent, resolve pcg, refresh vues.
Optimisations : count check, sync_metadata, refresh conditionnel, planification par endpoint.

Usage (dans le container hma-toolbox) :
    python scripts/sync-pennylane.py                             # Sync les 4 structures
    python scripts/sync-pennylane.py --structure HMA             # Sync une seule structure
    python scripts/sync-pennylane.py --full                      # Force full fetch
    python scripts/sync-pennylane.py --endpoints journals        # Sync uniquement les journaux
    python scripts/sync-pennylane.py --skip-refresh              # Sync sans refresh des vues
    python scripts/sync-pennylane.py --force-refresh             # Force le refresh meme sans changement

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

# Endpoints et leurs frequences recommandees (en heures)
ENDPOINT_CONFIG = {
    'ledger_entry_lines': {'freq_hours': 2, 'priority': 1},
    'journals':           {'freq_hours': 24, 'priority': 2},
    'ledger_accounts':    {'freq_hours': 168, 'priority': 3},  # 1x/semaine
}


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


def pennylane_count(token, endpoint, params=None):
    """Fetch une seule page avec limit=1 pour obtenir le count total (si dispo)."""
    p = dict(params or {})
    p['limit'] = 1
    data = pennylane_fetch(token, endpoint, p)
    # Pennylane retourne parfois total_count ou pagination.total
    total = data.get('total_count') or data.get('pagination', {}).get('total')
    items_count = len(data.get('items', []))
    has_more = data.get('has_more', False)
    return total, has_more, items_count


def ensure_sync_metadata(cursor, entite_id, code, endpoint):
    """Cree ou recupere l'entree sync_metadata pour structure+endpoint."""
    cursor.execute(
        "SELECT id, last_sync_at, row_count_local, row_count_remote, status "
        "FROM sync_metadata WHERE structure_code = %s AND endpoint = %s",
        (code, endpoint)
    )
    row = cursor.fetchone()
    if row:
        return {
            'id': str(row[0]),
            'last_sync_at': row[1],
            'row_count_local': row[2],
            'row_count_remote': row[3],
            'status': row[4],
        }

    cursor.execute(
        "INSERT INTO sync_metadata (entite_id, structure_code, endpoint, status) "
        "VALUES (%s, %s, %s, 'pending') RETURNING id",
        (entite_id, code, endpoint)
    )
    return {
        'id': str(cursor.fetchone()[0]),
        'last_sync_at': None,
        'row_count_local': 0,
        'row_count_remote': None,
        'status': 'pending',
    }


def update_sync_metadata(cursor, meta_id, **kwargs):
    """Met a jour les champs sync_metadata."""
    sets = []
    vals = []
    for k, v in kwargs.items():
        sets.append(f'{k} = %s')
        vals.append(v)
    vals.append(meta_id)
    cursor.execute(f"UPDATE sync_metadata SET {', '.join(sets)} WHERE id = %s", vals)


def count_check(cursor, conn, code, token, entite_id, meta):
    """Compare le count local vs remote pour decider si un sync est necessaire."""
    # Count local
    cursor.execute(
        "SELECT COUNT(*) FROM fec_ecriture WHERE entite_id = %s",
        (entite_id,)
    )
    local_count = cursor.fetchone()[0]

    # Count remote (essai via l'API — pas toujours dispo)
    remote_total, has_more, _ = pennylane_count(token, '/ledger_entry_lines')

    if remote_total is not None:
        log(f'  Count check: local={local_count}, remote={remote_total}')
        update_sync_metadata(cursor, meta['id'],
                             row_count_local=local_count,
                             row_count_remote=remote_total)
        if local_count == remote_total:
            return True  # skip
    else:
        log(f'  Count check: local={local_count}, remote=inconnu (pas de total_count)')
        update_sync_metadata(cursor, meta['id'], row_count_local=local_count)
        # Si l'API ne retourne pas de total, verifier via has_more avec une seule page
        if not has_more and local_count > 0:
            # Pas de donnees supplementaires et on a deja des donnees
            log(f'  API retourne 0 ou 1 item sans has_more, delta sync recommande')

    return False  # ne pas skip


def sync_structure(conn, code, token, full_fetch=False, skip_refresh=False):
    """Sync complete d'une structure : count check -> fetch -> staging -> upsert -> resolve."""
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

    # 2. Ensure sync_metadata
    meta = ensure_sync_metadata(cursor, entite_id, code, 'ledger_entry_lines')
    update_sync_metadata(cursor, meta['id'], status='running')

    # 3. Count check (sauf full fetch)
    if not full_fetch:
        try:
            should_skip = count_check(cursor, conn, code, token, entite_id, meta)
            if should_skip:
                log(f'  Count identique, skip sync (utiliser --full pour forcer)')
                update_sync_metadata(cursor, meta['id'], status='skipped',
                                     last_sync_at=datetime.now())
                return {'code': code, 'nb_lignes': 0, 'status': 'skipped_count_match'}
        except Exception as e:
            log(f'  Count check echoue ({e}), on continue avec le delta sync')

    # 4. Delta sync : date du dernier import termine
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

    # 5. Pre-charger les journaux
    log(f'  Fetch journaux...')
    journals_raw = pennylane_fetch_all(token, '/journals')
    journal_map = {j['id']: {'code': j.get('code', '?'), 'label': j.get('label', '')} for j in journals_raw}
    log(f'  {len(journal_map)} journaux')

    # 6. Fetch ledger_entry_lines
    params = {}
    if updated_since:
        params['updated_since'] = updated_since

    log(f'  Fetch /ledger_entry_lines...')
    lines = pennylane_fetch_all(token, '/ledger_entry_lines', params)
    log(f'  {len(lines)} lignes recuperees')

    if not lines:
        log(f'  Aucune nouvelle ligne')
        update_sync_metadata(cursor, meta['id'], status='done',
                             last_sync_at=datetime.now(), sync_duration_s=round(time.time() - t0, 1))
        return {'code': code, 'nb_lignes': 0, 'status': 'no_new_data'}

    # 7. Create fec_import
    cursor.execute(
        "INSERT INTO fec_import (entite_id, exercice_id, source, statut, nb_lignes_brut) "
        "VALUES (%s, %s, 'pennylane', 'en_cours', %s) RETURNING id",
        (entite_id, exercice_id, len(lines))
    )
    import_id = str(cursor.fetchone()[0])

    # 8. Truncate staging
    cursor.execute("TRUNCATE TABLE _staging_fec")

    # 9. Map + Insert staging
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
            line_id = str(line.get('id', ''))  # ID unique de la ligne (anti-doublon)

            hash_input = f'{entite_id}{line_id}{journal["code"]}{ecriture_num}{line.get("date", "")}{compte_num}{line.get("debit", 0)}{line.get("credit", 0)}'
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

    # 10. Upsert idempotent
    log(f'  Upsert staging -> fec_ecriture...')
    cursor.execute(
        f"INSERT INTO fec_ecriture ({', '.join(cols)}) "
        f"SELECT {', '.join(cols)} FROM _staging_fec "
        "ON CONFLICT (hash_md5) DO NOTHING"
    )

    # 11. Resolve pcg_numero
    log(f'  Resolve pcg_numero...')
    cursor.execute(
        "UPDATE fec_ecriture SET pcg_numero = resolve_compte(compte_num) "
        "WHERE pcg_numero IS NULL AND entite_id = %s",
        (entite_id,)
    )

    # 12. MAJ stats
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

    # 13. MAJ sync_metadata
    cursor.execute(
        "SELECT COUNT(*) FROM fec_ecriture WHERE entite_id = %s", (entite_id,)
    )
    total_local = cursor.fetchone()[0]

    update_sync_metadata(cursor, meta['id'],
                         status='done',
                         last_sync_at=datetime.now(),
                         row_count_local=total_local,
                         sync_duration_s=duree)

    log(f'  {code} OK: {stats[0]} brut, {stats[1]} inserees, {duree}s')

    return {
        'code': code,
        'nb_lignes': len(lines),
        'nb_inserees': stats[1],
        'duree': duree,
        'status': 'ok',
        'data_changed': stats[1] > 0,
    }


def refresh_conditional(conn):
    """Refresh conditionnel des vues : uniquement si des donnees ont change."""
    cursor = conn.cursor()

    # Verifier si la fonction existe (migration peut ne pas etre passee)
    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'refresh_views_if_needed')"
    )
    has_func = cursor.fetchone()[0]

    if has_func:
        log('Refresh conditionnel des vues...')
        cursor.execute('SELECT * FROM refresh_views_if_needed()')
        result = cursor.fetchone()
        refreshed, reason = result[0], result[1]
        if refreshed:
            log(f'  Vues rafraichies ({reason})')
        else:
            log(f'  Refresh skip ({reason})')
        return refreshed
    else:
        # Fallback : refresh classique
        log('Refresh vues materialisees (fallback classique)...')
        cursor.execute('SELECT refresh_all_views();')
        log('  Vues rafraichies')
        return True


def main():
    parser = argparse.ArgumentParser(description='Sync Pennylane -> PostgreSQL')
    parser.add_argument('--structure', '-s', help='Sync une seule structure (HMA, STIVMAT, STA, ETPA)')
    parser.add_argument('--full', action='store_true', help='Force full fetch (pas de delta)')
    parser.add_argument('--skip-refresh', action='store_true', help='Ne pas rafraichir les vues')
    parser.add_argument('--force-refresh', action='store_true', help='Forcer le refresh meme sans changement')
    parser.add_argument('--endpoints', nargs='+',
                        choices=['ledger_entry_lines', 'journals', 'ledger_accounts'],
                        help='Filtrer les endpoints a syncer')
    args = parser.parse_args()

    tokens = get_tokens()
    if not tokens:
        log('ERREUR: aucun token Pennylane dans les env vars (PENNYLANE_TOKEN_*)')
        sys.exit(1)
    log(f'Tokens: {list(tokens.keys())}')

    log('Connexion PostgreSQL...')
    conn = get_pg_conn()
    log('Connecte')

    # Verifier que sync_metadata existe, sinon creer
    cursor = conn.cursor()
    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'sync_metadata')"
    )
    if not cursor.fetchone()[0]:
        log('Table sync_metadata absente, creation...')
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_metadata (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                entite_id UUID NOT NULL REFERENCES entite(id),
                structure_code TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                last_sync_at TIMESTAMPTZ,
                last_refresh_at TIMESTAMPTZ,
                row_count_local INTEGER DEFAULT 0,
                row_count_remote INTEGER,
                last_cursor TEXT,
                sync_duration_s NUMERIC(8,1),
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                UNIQUE(structure_code, endpoint)
            )
        """)
        log('Table sync_metadata creee')

    structures = [args.structure.upper()] if args.structure else ['HMA', 'STIVMAT', 'STA', 'ETPA']
    results = []

    # Filtrer les endpoints si specifie
    active_endpoints = args.endpoints or ['ledger_entry_lines']

    for i, code in enumerate(structures):
        if code not in tokens:
            log(f'Token manquant pour {code}, skip')
            continue

        if i > 0:
            log(f'Pause {PAUSE_BETWEEN_STRUCTURES}s...')
            time.sleep(PAUSE_BETWEEN_STRUCTURES)

        # Pour l'instant, seul ledger_entry_lines est implemente
        if 'ledger_entry_lines' in active_endpoints:
            try:
                result = sync_structure(conn, code, tokens[code], full_fetch=args.full)
                results.append(result)
            except Exception as e:
                log(f'  ERREUR {code}: {e}')
                import traceback
                traceback.print_exc()
                results.append({'code': code, 'nb_lignes': 0, 'status': f'error: {e}'})

                # Marquer l'erreur dans sync_metadata
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE sync_metadata SET status = 'error', error_message = %s "
                        "WHERE structure_code = %s AND endpoint = 'ledger_entry_lines'",
                        (str(e)[:500], code)
                    )
                except Exception:
                    pass

    # Refresh des vues
    data_changed = any(r.get('data_changed') or r.get('status') == 'ok' for r in results)

    if args.skip_refresh:
        log('Refresh skip (--skip-refresh)')
    elif args.force_refresh:
        log('Refresh force (--force-refresh)...')
        cursor = conn.cursor()
        cursor.execute('SELECT refresh_all_views();')
        log('Vues rafraichies')
    elif data_changed:
        refresh_conditional(conn)
    else:
        log('Aucun changement, refresh skip')

    conn.close()

    log('\n=== Resume ===')
    total = 0
    for r in results:
        total += r.get('nb_lignes', 0)
        status = r['status']
        nb = r.get('nb_lignes', 0)
        ins = r.get('nb_inserees', '?')
        log(f'  {r["code"]}: {nb} lignes, {ins} inserees, status={status}')
    log(f'  Total: {total} lignes')

    # Exit code non-zero si toutes les structures sont en erreur
    if results and all(r['status'].startswith('error') for r in results):
        sys.exit(1)


if __name__ == '__main__':
    main()
