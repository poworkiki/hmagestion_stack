#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync Pennylane → grand_livre + balance_generale (PostgreSQL HMA)

Import DIRECT sans transformation FEC :
  /ledger_entry_lines → table grand_livre (enrichi PCG + calendrier)
  Puis REFRESH MATERIALIZED VIEW balance_generale

Usage:
    python3 scripts/sync-pennylane-gl.py                      # Sync les 4 structures
    python3 scripts/sync-pennylane-gl.py --structure ETPA      # Une seule structure
    python3 scripts/sync-pennylane-gl.py --full                # Force re-sync complet
    python3 scripts/sync-pennylane-gl.py --skip-refresh        # Sans refresh MV
"""
import json, os, sys, time, argparse, re
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# === Configuration ===
PL_BASE = 'https://app.pennylane.com/api/external/v2'
STRUCTURES = ['HMA', 'STIVMAT', 'STA', 'ETPA']
PAUSE_BETWEEN_STRUCTURES = 5
PAUSE_ON_429 = 30
MAX_RETRIES = 5
LIMIT_PER_PAGE = 100
BATCH_SIZE = 200


def log(msg):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}')


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


def get_db_conn(env):
    """Connexion PostgreSQL HMA via HMA_DB_URL ou Vaultwarden."""
    import pg8000

    db_url = env.get('HMA_DB_URL')
    if db_url:
        m = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
        if m:
            user, pw, host, port, db = m.groups()
            conn = pg8000.connect(user=user, password=pw, host=host, port=int(port), database=db)
            conn.autocommit = True
            return conn

    # Fallback : Vaultwarden
    script_dir = os.path.dirname(os.path.abspath(__file__))
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

    for c in ciphers:
        d = session.decrypt_cipher(c)
        if 'postgresql hma' in d['name'].lower() and 'standalone' in d['name'].lower():
            uri = d['uris'][0] if d['uris'] else ''
            if '://' in uri:
                host_part = uri.split('://')[1].split('/')[0]
                host, port = host_part.rsplit(':', 1) if ':' in host_part else (host_part, '5432')
            conn = pg8000.connect(user='postgres', password=d['password'],
                                  host=host, port=int(port), database='postgres')
            conn.autocommit = True
            return conn

    raise Exception('Impossible de se connecter a PostgreSQL HMA')


def get_tokens(env):
    """Récupère les tokens Pennylane depuis .env ou Vaultwarden."""
    tokens = {}
    # Essayer .env d'abord
    for code in STRUCTURES:
        key = f'PENNYLANE_TOKEN_{code}'
        if env.get(key):
            tokens[code] = env[key]

    if tokens:
        return tokens

    # Fallback : Vaultwarden
    script_dir = os.path.dirname(os.path.abspath(__file__))
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

    for c in ciphers:
        d = session.decrypt_cipher(c)
        name = d['name']
        pw = d['password']
        if 'pennylane api' in name.lower() and pw and 'sandbox' not in name.lower():
            for code in STRUCTURES:
                if code in name:
                    tokens[code] = pw

    return tokens


def pl_fetch(token, endpoint, params=None):
    """Fetch une page de l'API Pennylane avec retry sur 429."""
    import urllib.request, urllib.error

    if params is None:
        params = {}
    qs = '&'.join(f'{k}={v}' for k, v in params.items())
    url = f'{PL_BASE}{endpoint}?{qs}' if qs else f'{PL_BASE}{endpoint}'

    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(url, headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
        })
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = PAUSE_ON_429 * (attempt + 1)
                log(f'  429 rate limit, pause {wait}s (retry {attempt + 1}/{MAX_RETRIES})')
                time.sleep(wait)
                continue
            elif e.code == 401:
                raise Exception(f'Token invalide (401)')
            else:
                body = e.read().decode()[:200]
                raise Exception(f'HTTP {e.code}: {body}')

    raise Exception(f'Rate limit persistant apres {MAX_RETRIES} retries')


def pl_fetch_all(token, endpoint, params=None):
    """Pagination curseur : fetch toutes les pages."""
    all_items = []
    cursor = None
    page = 0

    while True:
        p = dict(params or {})
        p['limit'] = str(LIMIT_PER_PAGE)
        if cursor:
            p['cursor'] = cursor

        data = pl_fetch(token, endpoint, p)
        items = data.get('items', [])
        all_items.extend(items)
        page += 1

        has_more = data.get('has_more', False)
        cursor = data.get('next_cursor')

        log(f'  page {page}: {len(items)} items (total: {len(all_items)}, has_more: {has_more})')

        if not has_more or not cursor:
            break

        time.sleep(0.25)

    return all_items


def load_reference_data(cursor):
    """Charge les données de référence depuis PostgreSQL pour l'enrichissement."""
    # Entités
    cursor.execute("SELECT id, code, nom FROM entite")
    entites = {row[1]: {'id': str(row[0]), 'nom': row[2]} for row in cursor.fetchall()}

    # Exercices (ouverts)
    cursor.execute("""
        SELECT ex.id, e.code, ex.label, ex.date_debut, ex.date_fin
        FROM exercice ex JOIN entite e ON e.id = ex.entite_id
        WHERE ex.cloture = false
        ORDER BY ex.date_debut DESC
    """)
    exercices = {}
    for row in cursor.fetchall():
        code = row[1]
        if code not in exercices:  # Prendre le plus récent
            exercices[code] = {'id': str(row[0]), 'label': row[2],
                               'debut': row[3], 'fin': row[4]}

    # PCG analytique
    cursor.execute("""
        SELECT numero, libelle, classe,
               sig_solde, sig_signe, cr_rubrique, cr_signe,
               bilan_poste, bilan_section, bf_categorie, nature_defaut,
               crd_ordre, crd_categorie, crd_rubrique, crd_signe
        FROM pcg_analytique
    """)
    pcg = {}
    for row in cursor.fetchall():
        pcg[row[0]] = {
            'libelle': row[1], 'classe': row[2],
            'sig_solde': row[3], 'sig_signe': row[4],
            'cr_rubrique': row[5], 'cr_signe': row[6],
            'bilan_poste': row[7], 'bilan_section': row[8],
            'bf_categorie': row[9], 'nature_defaut': row[10],
            'crd_ordre': row[11], 'crd_categorie': row[12],
            'crd_rubrique': row[13], 'crd_signe': row[14],
        }

    # dim_calendrier
    cursor.execute("""
        SELECT date_jour, annee, trimestre, mois, mois_label, mois_nom,
               semaine, debut_mois
        FROM dim_calendrier
    """)
    cal = {}
    for row in cursor.fetchall():
        cal[row[0]] = {
            'annee': row[1], 'trimestre': row[2], 'mois': row[3],
            'mois_label': row[4], 'mois_nom': row[5],
            'semaine': row[6], 'debut_mois': row[7],
        }

    return entites, exercices, pcg, cal


def resolve_pcg_numero(compte_num, pcg):
    """Résolution du numéro PCG : essaie exact, puis tronque progressivement."""
    if not compte_num:
        return None
    # Exact
    if compte_num in pcg:
        return compte_num
    # Tronquer de droite
    for length in range(len(compte_num) - 1, 2, -1):
        candidate = compte_num[:length]
        if candidate in pcg:
            return candidate
    return None


def sync_structure(code, token, cursor, entites, exercices, pcg, cal, full_sync=False):
    """Sync une structure Pennylane → grand_livre."""
    log(f'=== Sync {code} ===')

    if code not in entites:
        log(f'  Entite {code} non trouvee en base, skip')
        return 0
    if code not in exercices:
        log(f'  Exercice ouvert non trouve pour {code}, skip')
        return 0

    entite = entites[code]
    exercice = exercices[code]

    # 1. Fetch journaux
    log(f'  Fetch /journals...')
    journals_raw = pl_fetch_all(token, '/journals')
    journal_map = {j['id']: {'code': j.get('code', '?'), 'label': j.get('label', '')}
                   for j in journals_raw}
    log(f'  {len(journal_map)} journaux')

    # 2. Count check — compare local vs remote
    if not full_sync:
        cursor.execute("SELECT COUNT(*) FROM grand_livre WHERE entite_id = %s",
                       (entite['id'],))
        local_count = cursor.fetchone()[0]

        # Fetch remote count (1 page, check total)
        remote_data = pl_fetch(token, '/ledger_entry_lines', {'limit': '1'})
        # Pennylane ne donne pas le total, on doit paginer pour compter
        # On skip le count check si pas de full_sync
        log(f'  Local: {local_count} lignes')

    # 3. Fetch toutes les lignes
    log(f'  Fetch /ledger_entry_lines...')
    lines = pl_fetch_all(token, '/ledger_entry_lines')
    log(f'  {len(lines)} lignes récupérées')

    if not lines:
        log(f'  Aucune ligne, skip')
        return 0

    # 4. Enrichir et insérer
    if full_sync:
        cursor.execute("DELETE FROM grand_livre WHERE entite_id = %s", (entite['id'],))
        log(f'  Purge grand_livre pour {code} (full sync)')

    inserted = 0
    skipped = 0

    for i in range(0, len(lines), BATCH_SIZE):
        batch = lines[i:i + BATCH_SIZE]
        values_list = []

        for line in batch:
            pl_line_id = line.get('id')
            if not pl_line_id:
                skipped += 1
                continue

            pl_entry_id = line.get('ledger_entry', {}).get('id') if line.get('ledger_entry') else None
            date_str = line.get('date')
            if not date_str:
                skipped += 1
                continue

            # Parse date
            from datetime import date as date_type
            try:
                d = date_type.fromisoformat(date_str)
            except (ValueError, TypeError):
                skipped += 1
                continue

            # Calendrier
            c = cal.get(d)
            if not c:
                skipped += 1
                continue

            # Compte
            compte_brut = line.get('ledger_account', {}).get('number', '') if line.get('ledger_account') else ''
            pcg_numero = resolve_pcg_numero(compte_brut, pcg)
            p = pcg.get(pcg_numero, {}) if pcg_numero else {}

            # Journal
            journal_id = line.get('journal', {}).get('id') if line.get('journal') else None
            journal = journal_map.get(journal_id, {'code': 'INCONNU', 'label': ''})

            ecriture_num = str(pl_entry_id) if pl_entry_id else ''
            debit = float(line.get('debit', 0))
            credit = float(line.get('credit', 0))
            label = line.get('label', '')
            is_a_nouveau = journal['code'] in ('AN', 'OD-AN', 'RAN')

            classe = p.get('classe')
            if classe is None and pcg_numero:
                try:
                    classe = int(pcg_numero[0])
                except (ValueError, IndexError):
                    classe = None

            values_list.append((
                pl_line_id, pl_entry_id,
                entite['id'], exercice['id'], entite['nom'], exercice['label'],
                date_str, c['annee'], c['trimestre'], c['mois'],
                c['mois_label'], c['mois_nom'], c['semaine'], c['debut_mois'],
                journal['code'], journal['label'], ecriture_num,
                pcg_numero, p.get('libelle', compte_brut), classe,
                None, None,  # comp_aux_num, comp_aux_lib
                ecriture_num, date_str, label,
                debit, credit,
                None, None,  # ecriture_let, date_let
                p.get('sig_solde'), p.get('sig_signe'),
                p.get('cr_rubrique'), p.get('cr_signe'),
                p.get('bilan_poste'), p.get('bilan_section'),
                p.get('bf_categorie'), p.get('nature_defaut'),
                p.get('crd_ordre'), p.get('crd_categorie'),
                p.get('crd_rubrique'), p.get('crd_signe'),
                is_a_nouveau,
            ))

        if values_list:
            placeholders = ', '.join(['%s'] * 42)
            sql = f"""
                INSERT INTO grand_livre (
                    pennylane_line_id, pennylane_entry_id,
                    entite_id, exercice_id, entite_nom, exercice_label,
                    ecriture_date, annee, trimestre, mois,
                    mois_label, mois_nom, semaine, debut_mois,
                    journal_code, journal_lib, ecriture_num,
                    compte_numero, compte_libelle, classe,
                    comp_aux_num, comp_aux_lib,
                    piece_ref, piece_date, ecriture_lib,
                    debit, credit,
                    ecriture_let, date_let,
                    sig_solde, sig_signe,
                    cr_rubrique, cr_signe,
                    bilan_poste, bilan_section,
                    bf_categorie, nature_defaut,
                    crd_ordre, crd_categorie,
                    crd_rubrique, crd_signe,
                    is_a_nouveau
                ) VALUES ({placeholders})
                ON CONFLICT (entite_id, pennylane_line_id) DO UPDATE SET
                    debit = EXCLUDED.debit,
                    credit = EXCLUDED.credit,
                    ecriture_lib = EXCLUDED.ecriture_lib,
                    compte_numero = EXCLUDED.compte_numero,
                    compte_libelle = EXCLUDED.compte_libelle,
                    classe = EXCLUDED.classe,
                    sig_solde = EXCLUDED.sig_solde,
                    sig_signe = EXCLUDED.sig_signe,
                    cr_rubrique = EXCLUDED.cr_rubrique,
                    cr_signe = EXCLUDED.cr_signe,
                    bilan_poste = EXCLUDED.bilan_poste,
                    bilan_section = EXCLUDED.bilan_section,
                    bf_categorie = EXCLUDED.bf_categorie,
                    nature_defaut = EXCLUDED.nature_defaut,
                    crd_ordre = EXCLUDED.crd_ordre,
                    crd_categorie = EXCLUDED.crd_categorie,
                    crd_rubrique = EXCLUDED.crd_rubrique,
                    crd_signe = EXCLUDED.crd_signe,
                    updated_at = now()
            """
            for vals in values_list:
                cursor.execute(sql, vals)
                inserted += 1

        batch_num = i // BATCH_SIZE + 1
        log(f'  batch {batch_num}: {min(i + BATCH_SIZE, len(lines))}/{len(lines)} '
            f'(insérés: {inserted}, skippés: {skipped})')

    # 5. Reconciliation : supprimer les lignes qui n'existent plus dans Pennylane
    fetched_ids = [line.get('id') for line in lines if line.get('id')]
    if fetched_ids:
        cursor.execute("CREATE TEMP TABLE IF NOT EXISTS _sync_ids (pl_id BIGINT PRIMARY KEY)")
        cursor.execute("TRUNCATE _sync_ids")
        for b in range(0, len(fetched_ids), 500):
            batch_ids = fetched_ids[b:b + 500]
            values = ','.join([f'({pid})' for pid in batch_ids])
            cursor.execute(f"INSERT INTO _sync_ids (pl_id) VALUES {values} ON CONFLICT DO NOTHING")

        cursor.execute(
            "DELETE FROM grand_livre WHERE entite_id = %s "
            "AND pennylane_line_id NOT IN (SELECT pl_id FROM _sync_ids)",
            (entite['id'],)
        )
        deleted = cursor.rowcount
        cursor.execute("DROP TABLE IF EXISTS _sync_ids")

        if deleted > 0:
            log(f'  Réconciliation: {deleted} lignes supprimées (absentes de Pennylane)')

    log(f'  {code}: {inserted} insérés, {skipped} skippés')
    return inserted


def main():
    parser = argparse.ArgumentParser(description='Sync Pennylane → grand_livre + balance_generale')
    parser.add_argument('--structure', '-s', help='Sync une seule structure')
    parser.add_argument('--full', action='store_true', help='Force re-sync complet (purge + re-import)')
    parser.add_argument('--skip-refresh', action='store_true', help='Ne pas refresh balance_generale')
    args = parser.parse_args()

    env = load_env()

    # Connexion DB
    log('Connexion PostgreSQL HMA...')
    try:
        import pg8000
    except ImportError:
        log('ERREUR: pip install pg8000')
        sys.exit(1)

    conn = get_db_conn(env)
    cursor = conn.cursor()
    log('Connecté')

    # Vérifier que la table grand_livre existe
    cursor.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'grand_livre'
    """)
    if not cursor.fetchone():
        log('ERREUR: table grand_livre inexistante. Exécuter sql/01-schema/011-grand-livre.sql d\'abord.')
        sys.exit(1)

    # Tokens
    log('Récupération tokens Pennylane...')
    tokens = get_tokens(env)
    log(f'Tokens: {list(tokens.keys())}')

    # Données de référence
    log('Chargement données de référence (entités, exercices, PCG, calendrier)...')
    entites, exercices, pcg, cal = load_reference_data(cursor)
    log(f'  {len(entites)} entités, {len(exercices)} exercices, {len(pcg)} comptes PCG, {len(cal)} jours calendrier')

    # Sync
    structures = [args.structure.upper()] if args.structure else STRUCTURES
    total_inserted = 0

    for i, code in enumerate(structures):
        if code not in tokens:
            log(f'{code}: token manquant, skip')
            continue

        if i > 0:
            log(f'Pause {PAUSE_BETWEEN_STRUCTURES}s...')
            time.sleep(PAUSE_BETWEEN_STRUCTURES)

        try:
            n = sync_structure(code, tokens[code], cursor, entites, exercices,
                               pcg, cal, full_sync=args.full)
            total_inserted += n
        except Exception as e:
            log(f'ERREUR {code}: {e}')
            import traceback
            traceback.print_exc()

    # Refresh MV
    if not args.skip_refresh and total_inserted > 0:
        log('Refresh balance_generale...')
        try:
            cursor.execute("REFRESH MATERIALIZED VIEW balance_generale")
            log('balance_generale rafraîchie')
        except Exception as e:
            log(f'ERREUR refresh: {e}')
    elif total_inserted == 0:
        log('Aucune donnée insérée, skip refresh')

    # Résumé
    log(f'\n=== Résumé ===')
    cursor.execute("""
        SELECT entite_nom, COUNT(*), MIN(ecriture_date), MAX(ecriture_date)
        FROM grand_livre
        GROUP BY entite_nom ORDER BY entite_nom
    """)
    for row in cursor.fetchall():
        log(f'  {row[0]}: {row[1]} lignes ({row[2]} → {row[3]})')

    cursor.close()
    conn.close()
    log('Terminé')


if __name__ == '__main__':
    main()
