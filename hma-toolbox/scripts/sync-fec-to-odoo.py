"""
Sync FEC PostgreSQL -> Odoo (import ecritures comptables)

Pipeline : fec_ecriture (PostgreSQL) -> account.move + account.move.line (Odoo XML-RPC)

Lit les ecritures FEC depuis la BDD PostgreSQL ETL (peuple par sync-pennylane.py)
et les injecte dans Odoo sous forme de pieces comptables (account.move).

Logique :
- Regroupe les lignes fec_ecriture par (ecriture_num, journal_code, ecriture_date) = 1 account.move
- Chaque ligne fec_ecriture = 1 account.move.line
- Mapping journal_code -> journal Odoo (VT-HM, AC-HM, etc.)
- Mapping compte_num -> account.account Odoo (PCG 6 chiffres)
- Deduplication par hash_md5 stocke dans le champ ref de account.move
- Mode incremental : ne traite que les ecritures non encore importees

Usage (dans le container hma-toolbox) :
    python scripts/sync-fec-to-odoo.py                     # Sync les 4 structures
    python scripts/sync-fec-to-odoo.py --structure HMA     # Sync une seule structure
    python scripts/sync-fec-to-odoo.py --dry-run            # Affiche sans ecrire dans Odoo
    python scripts/sync-fec-to-odoo.py --limit 100          # Limite le nombre d'ecritures

Env vars requises (injectees par Coolify) :
    PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DATABASE
    ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD
"""

import argparse
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from xmlrpc.client import ServerProxy

import pg8000


# === Configuration ===
BATCH_SIZE = 50  # Nombre d'account.move par batch Odoo


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


def get_odoo_conn():
    """Connexion Odoo via XML-RPC."""
    url = os.environ.get('ODOO_URL', 'https://odoo.hma.business')
    db = os.environ.get('ODOO_DB', 'HMA')
    user = os.environ.get('ODOO_USER', 'hmagestion@gmail.com')
    password = os.environ['ODOO_PASSWORD']

    common = ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, user, password, {})
    if not uid:
        raise Exception(f'Authentification Odoo echouee pour {user}@{db}')

    models = ServerProxy(f'{url}/xmlrpc/2/object')
    log(f'Connecte a Odoo {url} (uid={uid}, db={db})')
    return models, db, uid, password


# === Mapping structures -> journaux Odoo ===
STRUCTURE_JOURNAL_MAP = {
    'HMA': {'sale': 'VT-HM', 'purchase': 'AC-HM', 'general': 'OD'},
    'STIVMAT': {'sale': 'VT-SV', 'purchase': 'AC-SV', 'general': 'OD'},
    'STA': {'sale': 'VT-SA', 'purchase': 'AC-SA', 'general': 'OD'},
    'ETPA': {'sale': 'VT-EP', 'purchase': 'AC-EP', 'general': 'OD'},
}

# Mapping journal_code Pennylane -> type Odoo
JOURNAL_TYPE_MAP = {
    'VE': 'sale',       # Ventes
    'VT': 'sale',
    'AC': 'purchase',   # Achats
    'HA': 'purchase',
    'BQ': 'bank',       # Banque
    'BN': 'bank',
    'CA': 'cash',       # Caisse
    'OD': 'general',    # Operations diverses
    'AN': 'general',    # A-Nouveaux
    'SA': 'general',    # Salaires
    'IM': 'general',    # Immobilisations
}


def resolve_journal_code(pg_journal_code, structure_code):
    """Resoud le code journal Pennylane vers le code journal Odoo."""
    prefix = pg_journal_code[:2].upper()
    journal_type = JOURNAL_TYPE_MAP.get(prefix, 'general')
    structure_map = STRUCTURE_JOURNAL_MAP.get(structure_code, {})
    return structure_map.get(journal_type, 'OD')


def load_odoo_journals(models, db, uid, pwd):
    """Charge le mapping code -> id des journaux Odoo."""
    journals = models.execute_kw(db, uid, pwd,
        'account.journal', 'search_read', [[]],
        {'fields': ['code', 'id', 'type']}
    )
    return {j['code']: j for j in journals}


def load_odoo_accounts(models, db, uid, pwd):
    """Charge le mapping code -> id du plan comptable Odoo."""
    accounts = models.execute_kw(db, uid, pwd,
        'account.account', 'search_read', [[]],
        {'fields': ['code', 'id']}
    )
    # Index par code exact + par prefixe (6 premiers chiffres)
    by_code = {}
    for a in accounts:
        by_code[a['code']] = a['id']
        # Index aussi sans zeros terminaux
        stripped = a['code'].rstrip('0')
        if stripped and stripped not in by_code:
            by_code[stripped] = a['id']
    return by_code


def resolve_account(compte_num, accounts_map):
    """Resoud un numero de compte FEC vers un account.account Odoo."""
    # Essai exact
    if compte_num in accounts_map:
        return accounts_map[compte_num]
    # Essai 6 premiers chiffres
    code6 = compte_num[:6]
    if code6 in accounts_map:
        return accounts_map[code6]
    # Essai prefixes decroissants
    for length in range(len(compte_num), 2, -1):
        prefix = compte_num[:length]
        if prefix in accounts_map:
            return accounts_map[prefix]
    # Essai sans zeros terminaux
    stripped = compte_num.rstrip('0')
    if stripped in accounts_map:
        return accounts_map[stripped]
    return None


def load_existing_refs(models, db, uid, pwd, structure_code):
    """Charge les ref des account.move deja importes (pour deduplication)."""
    # On stocke le hash_md5 du premier move.line dans le champ ref du move
    # Format: FEC-{structure}-{ecriture_num}
    refs = models.execute_kw(db, uid, pwd,
        'account.move', 'search_read',
        [[('ref', '=like', f'FEC-{structure_code}-%')]],
        {'fields': ['ref'], 'limit': 0}
    )
    return {r['ref'] for r in refs}


def fetch_fec_ecritures(conn, structure_code, limit=None):
    """Lit les ecritures FEC depuis PostgreSQL pour une structure."""
    cur = conn.cursor()

    query = """
        SELECT
            fe.journal_code, fe.journal_lib,
            fe.ecriture_num, fe.ecriture_date,
            fe.compte_num, fe.compte_lib,
            fe.comp_aux_num, fe.comp_aux_lib,
            fe.piece_ref, fe.piece_date,
            fe.ecriture_lib,
            fe.debit, fe.credit,
            fe.ecriture_let, fe.date_let,
            fe.valid_date,
            fe.hash_md5
        FROM fec_ecriture fe
        JOIN entite e ON e.id = fe.entite_id
        WHERE e.code = %s
        ORDER BY fe.ecriture_date, fe.ecriture_num, fe.compte_num
    """
    params = [structure_code]

    if limit:
        query += ' LIMIT %s'
        params.append(limit)

    cur.execute(query, params)
    columns = [
        'journal_code', 'journal_lib', 'ecriture_num', 'ecriture_date',
        'compte_num', 'compte_lib', 'comp_aux_num', 'comp_aux_lib',
        'piece_ref', 'piece_date', 'ecriture_lib',
        'debit', 'credit', 'ecriture_let', 'date_let',
        'valid_date', 'hash_md5',
    ]
    rows = []
    for row in cur.fetchall():
        rows.append(dict(zip(columns, row)))
    return rows


def group_by_move(lines):
    """Regroupe les lignes FEC par piece comptable (ecriture_num + journal_code + date)."""
    moves = defaultdict(list)
    for line in lines:
        key = (line['ecriture_num'], line['journal_code'], str(line['ecriture_date']))
        moves[key].append(line)
    return moves


def create_odoo_moves(models, db, uid, pwd, moves_grouped, structure_code,
                      journals_map, accounts_map, existing_refs, dry_run=False):
    """Cree les account.move dans Odoo depuis les ecritures FEC groupees."""
    created = 0
    skipped = 0
    errors = 0
    missing_accounts = set()

    for (ecriture_num, journal_code, date_str), lines in moves_grouped.items():
        # Deduplication : verifier si deja importe
        ref = f'FEC-{structure_code}-{ecriture_num}'
        if ref in existing_refs:
            skipped += 1
            continue

        # Resoudre le journal Odoo
        odoo_journal_code = resolve_journal_code(journal_code, structure_code)
        if odoo_journal_code not in journals_map:
            log(f'  WARN: journal {odoo_journal_code} non trouve dans Odoo, fallback OD')
            odoo_journal_code = 'OD'
        journal = journals_map.get(odoo_journal_code)
        if not journal:
            errors += 1
            continue

        # Construire les lignes
        move_lines = []
        has_error = False
        for line in lines:
            account_id = resolve_account(line['compte_num'], accounts_map)
            if not account_id:
                missing_accounts.add(line['compte_num'])
                has_error = True
                continue

            debit = float(line['debit'] or 0)
            credit = float(line['credit'] or 0)

            move_lines.append((0, 0, {
                'account_id': account_id,
                'name': line['ecriture_lib'] or line['compte_lib'] or '/',
                'debit': debit,
                'credit': credit,
            }))

        if has_error or not move_lines:
            errors += 1
            continue

        # Verifier l'equilibre debit/credit
        total_debit = sum(ml[2]['debit'] for ml in move_lines)
        total_credit = sum(ml[2]['credit'] for ml in move_lines)
        if abs(total_debit - total_credit) > 0.01:
            log(f'  WARN: ecriture {ecriture_num} desequilibree '
                f'(D={total_debit:.2f} C={total_credit:.2f}), ignoree')
            errors += 1
            continue

        if dry_run:
            log(f'  [DRY] {ref}: {len(move_lines)} lignes, '
                f'journal={odoo_journal_code}, date={date_str}')
            created += 1
            continue

        # Creer le account.move dans Odoo
        try:
            move_vals = {
                'journal_id': journal['id'],
                'date': date_str,
                'ref': ref,
                'move_type': 'entry',
                'line_ids': move_lines,
            }
            move_id = models.execute_kw(db, uid, pwd,
                'account.move', 'create', [move_vals]
            )
            created += 1
            existing_refs.add(ref)

            if created % 50 == 0:
                log(f'  ... {created} ecritures creees')

        except Exception as e:
            err = str(e)[:150]
            log(f'  ERR ecriture {ecriture_num}: {err}')
            errors += 1

    return created, skipped, errors, missing_accounts


def sync_structure(structure_code, pg_conn, odoo_conn, dry_run=False, limit=None):
    """Synchronise une structure complete."""
    models, db, uid, pwd = odoo_conn

    log(f'=== Sync {structure_code} ===')

    # 1. Charger les references Odoo
    log(f'  Chargement des journaux et comptes Odoo...')
    journals_map = load_odoo_journals(models, db, uid, pwd)
    accounts_map = load_odoo_accounts(models, db, uid, pwd)
    log(f'  {len(journals_map)} journaux, {len(accounts_map)} comptes charges')

    # 2. Charger les ecritures deja importees
    existing_refs = load_existing_refs(models, db, uid, pwd, structure_code)
    log(f'  {len(existing_refs)} ecritures deja importees dans Odoo')

    # 3. Lire les ecritures FEC depuis PostgreSQL
    log(f'  Lecture des ecritures FEC depuis PostgreSQL...')
    lines = fetch_fec_ecritures(pg_conn, structure_code, limit=limit)
    log(f'  {len(lines)} lignes FEC lues')

    if not lines:
        log(f'  Rien a synchroniser pour {structure_code}')
        return

    # 4. Grouper par piece comptable
    moves_grouped = group_by_move(lines)
    log(f'  {len(moves_grouped)} pieces comptables a traiter')

    # 5. Creer dans Odoo
    created, skipped, errors, missing = create_odoo_moves(
        models, db, uid, pwd, moves_grouped, structure_code,
        journals_map, accounts_map, existing_refs, dry_run=dry_run
    )

    log(f'  Resultat {structure_code}: '
        f'{created} creees, {skipped} existantes, {errors} erreurs')

    if missing:
        log(f'  COMPTES MANQUANTS dans Odoo ({len(missing)}):')
        for compte in sorted(missing)[:20]:
            log(f'    {compte}')
        if len(missing) > 20:
            log(f'    ... et {len(missing) - 20} autres')


def main():
    parser = argparse.ArgumentParser(description='Sync FEC PostgreSQL -> Odoo')
    parser.add_argument('--structure', type=str, help='Code structure (HMA, STIVMAT, STA, ETPA)')
    parser.add_argument('--dry-run', action='store_true', help='Affiche sans ecrire')
    parser.add_argument('--limit', type=int, help='Limite le nombre de lignes FEC lues')
    args = parser.parse_args()

    structures = [args.structure] if args.structure else ['HMA', 'STIVMAT', 'STA', 'ETPA']

    log('Connexion PostgreSQL...')
    pg_conn = get_pg_conn()

    log('Connexion Odoo...')
    odoo_conn = get_odoo_conn()

    start = time.time()
    for code in structures:
        sync_structure(code, pg_conn, odoo_conn, dry_run=args.dry_run, limit=args.limit)
        if code != structures[-1]:
            time.sleep(2)

    elapsed = time.time() - start
    log(f'Termine en {elapsed:.1f}s')

    pg_conn.close()


if __name__ == '__main__':
    main()
