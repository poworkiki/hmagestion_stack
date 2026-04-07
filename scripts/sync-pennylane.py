"""
Sync Pennylane -> PostgreSQL HMA (4 structures FEC)

ETL incremental : fetch /ledger_entry_lines, insert via staging, upsert, resolve pcg.
Premier run = full fetch. Runs suivants = delta via updated_since.

Usage:
    python3 scripts/sync-pennylane.py                    # Sync les 4 structures
    python3 scripts/sync-pennylane.py --structure HMA    # Sync une seule structure
    python3 scripts/sync-pennylane.py --full             # Force full fetch (pas de delta)

Requires: VAULTWARDEN_URL, VAULTWARDEN_EMAIL, VAULTWARDEN_MASTER_PASSWORD in .env
          PostgreSQL password in Vaultwarden ("PostgreSQL HMA (standalone)" entry)
"""
import json, hashlib, subprocess, os, sys, time, argparse
from datetime import datetime
import pg8000

# === Configuration ===
PENNYLANE_BASE_URL = 'https://app.pennylane.com/api/external/v2'
PAUSE_BETWEEN_STRUCTURES = 5   # secondes entre chaque structure
PAUSE_ON_429 = 30              # secondes d'attente sur rate limit
MAX_RETRIES = 5
BATCH_SIZE = 500               # lignes par INSERT batch
LIMIT_PER_PAGE = 100           # max items par page API Pennylane


def log(msg):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}')


def load_env():
    env = {}
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def get_db_conn(secrets):
    """Connexion a PostgreSQL HMA standalone."""
    conn = pg8000.connect(
        host=secrets['db_host'],
        port=int(secrets['db_port']),
        database='postgres',
        user='postgres',
        password=secrets['db_pw'],
    )
    conn.autocommit = True
    return conn


def db_exec(conn, sql, params=None):
    """Execute SQL sur PostgreSQL HMA."""
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    try:
        return cursor.fetchall()
    except:
        return []


def vw_get_secrets(env):
    """Recupere les secrets via vw-crypto.py (dechiffrement client-side)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    from importlib import import_module
    # Import vw-crypto via importlib (tiret dans le nom)
    import importlib.util
    spec = importlib.util.spec_from_file_location('vw_crypto', os.path.join(script_dir, 'vw-crypto.py'))
    vw_crypto = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vw_crypto)

    session = vw_crypto.VwSession(
        base_url=env['VAULTWARDEN_URL'],
        email=env.get('VAULTWARDEN_EMAIL', 'poworkiki@gmail.com'),
        master_password=env['VAULTWARDEN_MASTER_PASSWORD'],
    )
    session.login()
    ciphers = session.fetch_ciphers(vw_crypto.ORG_ID)

    secrets = {'tokens': {}, 'db_pw': '', 'db_host': '', 'db_port': '5432'}
    for c in ciphers:
        d = session.decrypt_cipher(c)
        name = d['name']
        pw = d['password']

        # Tokens Pennylane
        if 'pennylane api' in name.lower() and pw and 'sandbox' not in name.lower():
            for code in ['HMA', 'STIVMAT', 'STA', 'ETPA']:
                if code in name:
                    secrets['tokens'][code] = pw

        # PostgreSQL HMA standalone
        if 'postgresql hma' in name.lower() and 'standalone' in name.lower() and pw:
            secrets['db_pw'] = pw
            # Extraire host:port depuis l'URI (postgresql://host:port/db)
            uri = d['uris'][0] if d['uris'] else ''
            if '://' in uri:
                host_part = uri.split('://')[1].split('/')[0]
                if ':' in host_part:
                    secrets['db_host'], secrets['db_port'] = host_part.rsplit(':', 1)
                else:
                    secrets['db_host'] = host_part

    return secrets


def pennylane_fetch(token, endpoint, params=None):
    """Fetch une page de l'API Pennylane avec retry sur 429."""
    url = f'{PENNYLANE_BASE_URL}{endpoint}'
    if params:
        url += '?' + '&'.join(f'{k}={v}' for k, v in params.items())

    for attempt in range(MAX_RETRIES):
        resp = subprocess.run(['curl', '-s', '-w', '\n%{http_code}',
            url,
            '-H', f'Authorization: Bearer {token}',
            '-H', 'Accept: application/json'], capture_output=True, text=True)

        lines = resp.stdout.strip().rsplit('\n', 1)
        body = lines[0] if len(lines) > 0 else ''
        status = int(lines[-1]) if len(lines) > 1 else 0

        if status == 200:
            return json.loads(body)
        elif status == 429:
            wait = PAUSE_ON_429 * (attempt + 1)
            log(f'  429 rate limit, pause {wait}s (retry {attempt + 1}/{MAX_RETRIES})')
            time.sleep(wait)
            continue
        elif status == 401:
            raise Exception(f'Token invalide (401)')
        else:
            raise Exception(f'HTTP {status}: {body[:200]}')

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

        log(f'  page {page}: {len(items)} items (total: {len(all_items)}, has_more: {has_more})')

        if not has_more or not cursor:
            break

    return all_items


def db_sql(query):
    """Retourne le SQL brut (pour usage via fichier ou CLI)."""
    return query


def sync_structure(code, token, full_fetch=False):
    """Sync une structure Pennylane -> Supabase."""
    log(f'=== Sync {code} ===')

    # 1. Pre-charger les journaux
    log(f'  Fetch journaux...')
    journals_raw = pennylane_fetch_all(token, '/journals')
    journal_map = {j['id']: {'code': j.get('code', '?'), 'label': j.get('label', '')} for j in journals_raw}
    log(f'  {len(journal_map)} journaux charges')

    # 2. Fetch ledger_entry_lines
    params = {}
    if not full_fetch:
        # TODO: lire la date du dernier import termine pour cette structure
        # Pour le premier run, on fait un full fetch
        pass

    log(f'  Fetch /ledger_entry_lines...')
    lines = pennylane_fetch_all(token, '/ledger_entry_lines', params)
    log(f'  {len(lines)} lignes recuperees')

    if not lines:
        log(f'  Aucune ligne, skip')
        return {'code': code, 'nb_lignes': 0, 'status': 'skip'}

    # 3. Mapper vers le format FEC
    entries = []
    for line in lines:
        compte_num = line.get('ledger_account', {}).get('number', '000') if line.get('ledger_account') else '000'
        journal_id = line.get('journal', {}).get('id')
        journal = journal_map.get(journal_id, {'code': 'INCONNU', 'label': ''})
        ecriture_num = str(line.get('ledger_entry', {}).get('id', '')) if line.get('ledger_entry') else ''

        # Fingerprint MD5 de deduplication
        hash_input = f'{code}{journal["code"]}{ecriture_num}{line.get("date", "")}{compte_num}{line.get("debit", 0)}{line.get("credit", 0)}'
        hash_md5 = hashlib.md5(hash_input.encode()).hexdigest()

        entries.append({
            'journal_code': journal['code'],
            'journal_lib': journal['label'],
            'ecriture_num': ecriture_num,
            'ecriture_date': line.get('date'),
            'compte_num': compte_num,
            'compte_lib': line.get('ledger_account', {}).get('number', '') if line.get('ledger_account') else '',
            'comp_aux_num': None,
            'comp_aux_lib': None,
            'piece_ref': ecriture_num,
            'piece_date': line.get('date'),
            'ecriture_lib': line.get('label', ''),
            'debit': float(line.get('debit', 0)),
            'credit': float(line.get('credit', 0)),
            'ecriture_let': None,
            'date_let': None,
            'valid_date': None,
            'montant_devise': None,
            'idevise': None,
            'hash_md5': hash_md5,
        })

    log(f'  {len(entries)} ecritures mappees')
    return {'code': code, 'entries': entries, 'nb_lignes': len(entries), 'status': 'ok'}


def generate_sql(code, entries):
    """Genere le SQL complet pour une structure."""
    if not entries:
        return None

    # Escape SQL values
    def sql_val(v):
        if v is None:
            return 'NULL'
        if isinstance(v, (int, float)):
            return str(v)
        return "'" + str(v).replace("'", "''") + "'"

    cols = ['entite_id', 'exercice_id', 'fec_import_id',
            'journal_code', 'journal_lib', 'ecriture_num', 'ecriture_date',
            'compte_num', 'compte_lib', 'comp_aux_num', 'comp_aux_lib',
            'piece_ref', 'piece_date', 'ecriture_lib',
            'debit', 'credit', 'ecriture_let', 'date_let', 'valid_date',
            'montant_devise', 'idevise', 'pcg_numero', 'hash_md5']

    entry_cols = ['journal_code', 'journal_lib', 'ecriture_num', 'ecriture_date',
                  'compte_num', 'compte_lib', 'comp_aux_num', 'comp_aux_lib',
                  'piece_ref', 'piece_date', 'ecriture_lib',
                  'debit', 'credit', 'ecriture_let', 'date_let', 'valid_date',
                  'montant_devise', 'idevise', 'hash_md5']

    # SQL statements
    statements = []

    # 1. Resolve IDs
    statements.append(f"""
DO $$
DECLARE
    v_entite_id UUID;
    v_exercice_id UUID;
    v_import_id UUID;
BEGIN
    -- Resolve IDs
    SELECT e.id, ex.id INTO v_entite_id, v_exercice_id
    FROM entite e
    JOIN exercice ex ON ex.entite_id = e.id AND ex.cloture = false
    WHERE e.code = '{code}'
    ORDER BY ex.date_debut DESC LIMIT 1;

    -- Create fec_import
    INSERT INTO fec_import (entite_id, exercice_id, source, statut, nb_lignes_brut)
    VALUES (v_entite_id, v_exercice_id, 'pennylane', 'en_cours', {len(entries)})
    RETURNING id INTO v_import_id;

    -- Truncate staging
    TRUNCATE TABLE _staging_fec;

    -- Insert staging (par batch)""")

    # Insert par batch
    for i in range(0, len(entries), BATCH_SIZE):
        batch = entries[i:i + BATCH_SIZE]
        values = []
        for e in batch:
            vals = [f'v_entite_id', f'v_exercice_id', f'v_import_id']
            for col in entry_cols:
                vals.append(sql_val(e.get(col)))
            # pcg_numero = NULL (sera resolu apres)
            vals.insert(-1, 'NULL')  # pcg_numero before hash_md5
            values.append(f'    ({", ".join(vals)})')

        statements.append(f"""
    INSERT INTO _staging_fec ({', '.join(cols)})
    VALUES
{chr(10).join(values)};""")

    # Upsert + resolve + stats
    statements.append(f"""
    -- Upsert idempotent staging -> fec_ecriture
    INSERT INTO fec_ecriture ({', '.join(cols)})
    SELECT {', '.join(cols)}
    FROM _staging_fec
    ON CONFLICT (hash_md5) DO NOTHING;

    -- Resolve pcg_numero
    UPDATE fec_ecriture
    SET pcg_numero = resolve_compte(compte_num)
    WHERE pcg_numero IS NULL AND entite_id = v_entite_id;

    -- MAJ stats
    UPDATE fec_import
    SET nb_lignes_inserees = (SELECT COUNT(*) FROM fec_ecriture WHERE fec_import_id = v_import_id),
        duree_secondes = EXTRACT(EPOCH FROM (now() - date_import)),
        statut = 'termine'
    WHERE id = v_import_id;

END $$;""")

    return '\n'.join(statements)


def load_to_db(conn, code, entries):
    """Charge les ecritures dans PostgreSQL HMA : staging -> upsert -> resolve -> stats."""
    cursor = conn.cursor()

    # 1. Resolve IDs
    cursor.execute(
        "SELECT e.id, ex.id FROM entite e "
        "JOIN exercice ex ON ex.entite_id = e.id AND ex.cloture = false "
        "WHERE e.code = %s ORDER BY ex.date_debut DESC LIMIT 1",
        (code,)
    )
    row = cursor.fetchone()
    if not row:
        raise Exception(f'Entite/exercice non trouve pour {code}')
    entite_id, exercice_id = str(row[0]), str(row[1])
    log(f'  IDs: entite={entite_id[:8]}..., exercice={exercice_id[:8]}...')

    # 2. Create fec_import
    cursor.execute(
        "INSERT INTO fec_import (entite_id, exercice_id, source, statut, nb_lignes_brut) "
        "VALUES (%s, %s, 'pennylane', 'en_cours', %s) RETURNING id",
        (entite_id, exercice_id, len(entries))
    )
    import_id = str(cursor.fetchone()[0])
    log(f'  fec_import cree: {import_id[:8]}...')

    # 3. Truncate staging
    cursor.execute("TRUNCATE TABLE _staging_fec")

    # 4. Insert staging par batch
    cols = ['entite_id', 'exercice_id', 'fec_import_id',
            'journal_code', 'journal_lib', 'ecriture_num', 'ecriture_date',
            'compte_num', 'compte_lib', 'comp_aux_num', 'comp_aux_lib',
            'piece_ref', 'piece_date', 'ecriture_lib',
            'debit', 'credit', 'ecriture_let', 'date_let', 'valid_date',
            'montant_devise', 'idevise', 'pcg_numero', 'hash_md5']

    placeholders = ', '.join(['%s'] * len(cols))
    insert_sql = f"INSERT INTO _staging_fec ({', '.join(cols)}) VALUES ({placeholders})"

    batch_count = 0
    for i in range(0, len(entries), BATCH_SIZE):
        batch = entries[i:i + BATCH_SIZE]
        for e in batch:
            values = [
                entite_id, exercice_id, import_id,
                e['journal_code'], e['journal_lib'], e['ecriture_num'], e['ecriture_date'],
                e['compte_num'], e['compte_lib'], e['comp_aux_num'], e['comp_aux_lib'],
                e['piece_ref'], e['piece_date'], e['ecriture_lib'],
                e['debit'], e['credit'], e['ecriture_let'], e['date_let'], e['valid_date'],
                e['montant_devise'], e['idevise'], None, e['hash_md5']  # pcg_numero=None
            ]
            cursor.execute(insert_sql, values)
        batch_count += 1
        log(f'  batch {batch_count}: {min((i + BATCH_SIZE), len(entries))}/{len(entries)} lignes en staging')

    # 5. Upsert staging -> fec_ecriture
    log(f'  Upsert idempotent staging -> fec_ecriture...')
    cursor.execute(
        f"INSERT INTO fec_ecriture ({', '.join(cols)}) "
        f"SELECT {', '.join(cols)} FROM _staging_fec "
        "ON CONFLICT (hash_md5) DO NOTHING"
    )

    # 6. Resolve pcg_numero
    log(f'  Resolve pcg_numero...')
    cursor.execute(
        "UPDATE fec_ecriture SET pcg_numero = resolve_compte(compte_num) "
        "WHERE pcg_numero IS NULL AND entite_id = %s",
        (entite_id,)
    )

    # 7. MAJ stats
    cursor.execute(
        "UPDATE fec_import SET "
        "nb_lignes_inserees = (SELECT COUNT(*) FROM fec_ecriture WHERE fec_import_id = %s), "
        "duree_secondes = EXTRACT(EPOCH FROM (now() - date_import)), "
        "statut = 'termine' "
        "WHERE id = %s",
        (import_id, import_id)
    )
    log(f'  {code} charge et termine')


def main():
    parser = argparse.ArgumentParser(description='Sync Pennylane -> PostgreSQL HMA')
    parser.add_argument('--structure', '-s', help='Sync une seule structure (HMA, STIVMAT, STA, ETPA)')
    parser.add_argument('--full', action='store_true', help='Force full fetch (pas de delta)')
    parser.add_argument('--dry-run', action='store_true', help='Genere le SQL sans executer')
    args = parser.parse_args()

    env = load_env()
    log('Auth Vaultwarden...')
    secrets = vw_get_secrets(env)
    tokens = secrets['tokens']
    log(f'Tokens: {list(tokens.keys())}')

    structures = [args.structure.upper()] if args.structure else ['HMA', 'STIVMAT', 'STA', 'ETPA']
    results = []

    # Pas de connexion directe — on genere le SQL et l'execute via MCP ou fichier
    conn = None

    for i, code in enumerate(structures):
        if code not in tokens:
            log(f'Token manquant pour {code}, skip')
            continue

        if i > 0:
            log(f'Pause {PAUSE_BETWEEN_STRUCTURES}s avant {code}...')
            time.sleep(PAUSE_BETWEEN_STRUCTURES)

        try:
            result = sync_structure(code, tokens[code], full_fetch=args.full)
            results.append(result)

            if result['status'] == 'ok' and result.get('entries'):
                sql = generate_sql(code, result['entries'])
                sql_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), f'sync_{code}.sql')
                with open(sql_file, 'w', encoding='utf-8') as f:
                    f.write(sql)
                log(f'  SQL genere: {sql_file} ({len(sql)} chars, {len(result["entries"])} ecritures)')

        except Exception as e:
            log(f'  ERREUR {code}: {e}')
            import traceback
            traceback.print_exc()
            results.append({'code': code, 'nb_lignes': 0, 'status': f'error: {e}'})

    # Refresh views sera fait via MCP apres execution du SQL

    # Resume
    log('\n=== Resume ===')
    for r in results:
        log(f'  {r["code"]}: {r["nb_lignes"]} lignes, status={r["status"]}')

    return results


if __name__ == '__main__':
    main()
