"""
Deploy le workflow Sync Pennylane v2 dans n8n.
Usage: python3 scripts/deploy-n8n-workflow.py
Requires: VAULTWARDEN_URL, VAULTWARDEN_CLIENT_ID, VAULTWARDEN_CLIENT_SECRET in .env
"""
import json, hashlib, subprocess, os, sys

def load_env():
    env = {}
    with open('.env', 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env

def vw_auth(env):
    hostname = subprocess.run(['hostname'], capture_output=True, text=True).stdout.strip()
    device_id = 'hma-cli-' + hashlib.md5(hostname.encode()).hexdigest()
    resp = subprocess.run(['curl', '-s', '-X', 'POST',
        f'{env["VAULTWARDEN_URL"]}/identity/connect/token',
        '-H', 'Content-Type: application/x-www-form-urlencoded',
        '-d', 'grant_type=client_credentials',
        '-d', f'client_id={env["VAULTWARDEN_CLIENT_ID"]}',
        '-d', f'client_secret={env["VAULTWARDEN_CLIENT_SECRET"]}',
        '-d', 'scope=api',
        '-d', f'deviceIdentifier={device_id}',
        '-d', 'deviceType=14',
        '-d', 'deviceName=HMA-CLI'], capture_output=True, text=True)
    return json.loads(resp.stdout)['access_token']

def vw_get_secrets(env, vw_token):
    resp = subprocess.run(['curl', '-s', f'{env["VAULTWARDEN_URL"]}/api/ciphers',
        '-H', f'Authorization: Bearer {vw_token}'], capture_output=True, text=True)
    return json.loads(resp.stdout).get('data', [])

def n8n_api(method, path, n8n_key, data=None):
    args = ['curl', '-s', '-X', method,
        f'https://n8n.hma.business/api/v1{path}',
        '-H', f'X-N8N-API-KEY: {n8n_key}',
        '-H', 'Content-Type: application/json']
    if data:
        args.extend(['-d', json.dumps(data)])
    resp = subprocess.run(args, capture_output=True, text=True)
    return json.loads(resp.stdout) if resp.stdout else {}

def main():
    env = load_env()
    print('1. Auth Vaultwarden...')
    vw_token = vw_auth(env)
    secrets = vw_get_secrets(env, vw_token)

    # Extract secrets
    n8n_key = ''
    tokens = {}
    for item in secrets:
        name = item.get('name', '')
        pw = (item.get('login') or {}).get('password', '') or ''
        if 'n8n' in name.lower() and 'api key' in name.lower() and pw:
            n8n_key = pw
        if 'pennylane api' in name.lower() and pw and 'sandbox' not in name.lower():
            for code in ['HMA', 'STIVMAT', 'STA', 'ETPA']:
                if code in name:
                    tokens[code] = pw

    print(f'   n8n key: {len(n8n_key)} chars, tokens: {list(tokens.keys())}')

    # Get PG credential
    print('2. Get PostgreSQL credential...')
    creds = n8n_api('GET', '/credentials', n8n_key).get('data', [])
    pg_cred = None
    for c in creds:
        if c['type'] == 'postgres':
            pg_cred = {'id': c['id'], 'name': c['name']}
            break
    if not pg_cred:
        print('ERROR: No PostgreSQL credential in n8n')
        sys.exit(1)
    print(f'   PG cred: {pg_cred["name"]}')

    # Delete existing workflow(s) named "Sync Pennylane"
    print('3. Clean old workflows...')
    wfs = n8n_api('GET', '/workflows', n8n_key).get('data', [])
    for wf in wfs:
        if 'sync pennylane' in wf.get('name', '').lower():
            n8n_api('DELETE', f'/workflows/{wf["id"]}', n8n_key)
            print(f'   Deleted: {wf["id"]} {wf["name"]}')

    # Clean stale fec_import records
    print('4. Clean stale fec_import...')
    # Will do via Supabase MCP after deploy

    # Build workflow
    print('5. Build workflow v2...')

    config_code = (
        "// Config : 4 structures avec tokens Pennylane\n"
        "const structures = [\n"
        f"  {{ code: 'HMA',     token: '{tokens['HMA']}' }},\n"
        f"  {{ code: 'STIVMAT', token: '{tokens['STIVMAT']}' }},\n"
        f"  {{ code: 'STA',     token: '{tokens['STA']}' }},\n"
        f"  {{ code: 'ETPA',    token: '{tokens['ETPA']}' }}\n"
        "];\n"
        "return structures.map(s => ({ json: s }));"
    )

    merge_code = (
        "// Fusionner Resolve IDs + token du Config\n"
        "const resolved = $input.first().json;\n"
        "const configItems = $('Config 4 structures').all();\n"
        "const configItem = configItems.find(i => i.json.code === resolved.code);\n"
        "const token = configItem ? configItem.json.token : null;\n"
        "if (!token) throw new Error('Token manquant pour ' + resolved.code);\n"
        "return [{ json: { ...resolved, token } }];"
    )

    fetch_code = (
        "// Fetch Pennylane /ledger_entry_lines + Map FEC + Hash MD5\n"
        "// Pagination par curseur (has_more + next_cursor)\n"
        "const data = $input.first().json;\n"
        "const { entite_id, exercice_id, fec_import_id, code, token } = data;\n\n"
        "if (!token) throw new Error('Token manquant pour ' + code);\n"
        "if (!entite_id) throw new Error('entite_id manquant pour ' + code);\n\n"
        "const baseUrl = 'https://app.pennylane.com/api/external/v2';\n"
        "const headers = { 'Authorization': 'Bearer ' + token, 'Accept': 'application/json' };\n"
        "const crypto = require('crypto');\n\n"
        "// 1. Pre-charger les journaux (id -> code/label)\n"
        "const journalMap = {};\n"
        "let jCursor = null;\n"
        "let jHasMore = true;\n"
        "while (jHasMore) {\n"
        "  const jUrl = jCursor\n"
        "    ? baseUrl + '/journals?limit=100&cursor=' + jCursor\n"
        "    : baseUrl + '/journals?limit=100';\n"
        "  const jResp = await this.helpers.httpRequest({ method: 'GET', url: jUrl, headers });\n"
        "  for (const j of jResp.items) {\n"
        "    journalMap[j.id] = { code: j.code, label: j.label };\n"
        "  }\n"
        "  jHasMore = jResp.has_more || false;\n"
        "  jCursor = jResp.next_cursor || null;\n"
        "}\n\n"
        "// 2. Paginer /ledger_entry_lines par curseur\n"
        "let cursor = null;\n"
        "let hasMore = true;\n"
        "let allEntries = [];\n"
        "let retryCount = 0;\n\n"
        "while (hasMore) {\n"
        "  const url = cursor\n"
        "    ? baseUrl + '/ledger_entry_lines?limit=100&cursor=' + cursor\n"
        "    : baseUrl + '/ledger_entry_lines?limit=100';\n"
        "  try {\n"
        "    const response = await this.helpers.httpRequest({ method: 'GET', url, headers });\n"
        "    for (const line of response.items) {\n"
        "      const compteNum = line.ledger_account ? line.ledger_account.number : '000';\n"
        "      const journal = journalMap[line.journal.id] || { code: 'INCONNU', label: '' };\n"
        "      const ecritureNum = line.ledger_entry ? String(line.ledger_entry.id) : '';\n\n"
        "      // Fingerprint MD5 de deduplication\n"
        "      const hashInput = entite_id + journal.code + ecritureNum + line.date + compteNum + line.debit + line.credit;\n"
        "      const hashMd5 = crypto.createHash('md5').update(hashInput).digest('hex');\n\n"
        "      allEntries.push({\n"
        "        entite_id, exercice_id, fec_import_id,\n"
        "        journal_code: journal.code,\n"
        "        journal_lib: journal.label,\n"
        "        ecriture_num: ecritureNum,\n"
        "        ecriture_date: line.date,\n"
        "        compte_num: compteNum,\n"
        "        compte_lib: line.ledger_account ? line.ledger_account.number : '',\n"
        "        comp_aux_num: null,\n"
        "        comp_aux_lib: null,\n"
        "        piece_ref: ecritureNum,\n"
        "        piece_date: line.date,\n"
        "        ecriture_lib: line.label || '',\n"
        "        debit: parseFloat(line.debit) || 0,\n"
        "        credit: parseFloat(line.credit) || 0,\n"
        "        ecriture_let: null,\n"
        "        date_let: null,\n"
        "        valid_date: null,\n"
        "        montant_devise: null, idevise: null, pcg_numero: null,\n"
        "        hash_md5: hashMd5\n"
        "      });\n"
        "    }\n"
        "    hasMore = response.has_more || false;\n"
        "    cursor = response.next_cursor || null;\n"
        "    retryCount = 0;\n"
        "  } catch (error) {\n"
        "    if ((error.statusCode === 429 || error.statusCode === 500) && retryCount < 3) {\n"
        "      retryCount++;\n"
        "      await new Promise(r => setTimeout(r, Math.pow(2, retryCount) * 1000));\n"
        "      continue;\n"
        "    }\n"
        "    throw error;\n"
        "  }\n"
        "}\n\n"
        "// Retourner par batch de 500\n"
        "const batchSize = 500;\n"
        "const batches = [];\n"
        "for (let i = 0; i < allEntries.length; i += batchSize) {\n"
        "  batches.push({ entries: allEntries.slice(i, i + batchSize),\n"
        "    nb_lignes_brut: allEntries.length, fec_import_id, entite_id, exercice_id, code });\n"
        "}\n"
        "if (batches.length === 0) {\n"
        "  return [{ json: { entries: [], nb_lignes_brut: 0, fec_import_id, entite_id, exercice_id, code } }];\n"
        "}\n"
        "return batches.map(b => ({ json: b }));"
    )

    insert_staging_query = (
        "={{ (() => {\n"
        "  const entries = $json.entries;\n"
        "  if (!entries || entries.length === 0) return 'SELECT 1;';\n"
        "  const cols = Object.keys(entries[0]);\n"
        "  const values = entries.map(e => \n"
        "    '(' + cols.map(c => {\n"
        "      const v = e[c];\n"
        "      if (v === null || v === undefined) return 'NULL';\n"
        "      if (typeof v === 'number') return v;\n"
        "      return \"'\" + String(v).replace(/'/g, \"''\") + \"'\";\n"
        "    }).join(',') + ')'\n"
        "  ).join(',\\n');\n"
        "  return `INSERT INTO _staging_fec (${cols.join(',')}) VALUES\\n${values};`;\n"
        "})() }}"
    )

    pg = {'postgres': pg_cred}

    nodes = [
        {'parameters': {}, 'id': 'trigger', 'name': 'Declenchement manuel',
         'type': 'n8n-nodes-base.manualTrigger', 'typeVersion': 1, 'position': [0, 0]},
        {'parameters': {'jsCode': config_code}, 'id': 'config',
         'name': 'Config 4 structures', 'type': 'n8n-nodes-base.code',
         'typeVersion': 2, 'position': [220, 0]},
        {'parameters': {'options': {}}, 'id': 'loop',
         'name': 'Boucle structures', 'type': 'n8n-nodes-base.splitInBatches',
         'typeVersion': 3, 'position': [440, 0]},
        {'parameters': {'operation': 'executeQuery',
         'query': "SELECT e.id AS entite_id, ex.id AS exercice_id, e.code\nFROM entite e\nJOIN exercice ex ON ex.entite_id = e.id AND ex.cloture = false\nWHERE e.code = '{{ $json.code }}'\nORDER BY ex.date_debut DESC\nLIMIT 1;"},
         'id': 'resolve', 'name': 'Resolve IDs',
         'type': 'n8n-nodes-base.postgres', 'typeVersion': 2.5,
         'position': [660, 0], 'credentials': pg},
        {'parameters': {'jsCode': merge_code}, 'id': 'merge',
         'name': 'Merge IDs + Token', 'type': 'n8n-nodes-base.code',
         'typeVersion': 2, 'position': [880, 0]},
        {'parameters': {'operation': 'executeQuery',
         'query': "INSERT INTO fec_import (entite_id, exercice_id, source, statut)\nVALUES ('{{ $json.entite_id }}', '{{ $json.exercice_id }}', 'pennylane', 'en_cours')\nRETURNING id AS fec_import_id, entite_id, exercice_id, '{{ $json.code }}' AS code, '{{ $json.token }}' AS token;"},
         'id': 'create-import', 'name': 'Create fec_import',
         'type': 'n8n-nodes-base.postgres', 'typeVersion': 2.5,
         'position': [1100, 0], 'credentials': pg},
        {'parameters': {'operation': 'executeQuery', 'query': 'TRUNCATE TABLE _staging_fec;'},
         'id': 'truncate', 'name': 'Truncate staging',
         'type': 'n8n-nodes-base.postgres', 'typeVersion': 2.5,
         'position': [1320, 0], 'credentials': pg},
        {'parameters': {'jsCode': fetch_code}, 'id': 'fetch',
         'name': 'Fetch Pennylane + Map FEC', 'type': 'n8n-nodes-base.code',
         'typeVersion': 2, 'position': [1540, 0]},
        {'parameters': {'operation': 'executeQuery', 'query': insert_staging_query},
         'id': 'insert-stg', 'name': 'Insert staging',
         'type': 'n8n-nodes-base.postgres', 'typeVersion': 2.5,
         'position': [1760, 0], 'credentials': pg},
        {'parameters': {'operation': 'executeQuery',
         'query': "INSERT INTO fec_ecriture (\n  entite_id, exercice_id, fec_import_id,\n  journal_code, journal_lib, ecriture_num, ecriture_date,\n  compte_num, compte_lib, comp_aux_num, comp_aux_lib,\n  piece_ref, piece_date, ecriture_lib,\n  debit, credit, ecriture_let, date_let, valid_date,\n  montant_devise, idevise, pcg_numero, hash_md5\n)\nSELECT\n  entite_id, exercice_id, fec_import_id,\n  journal_code, journal_lib, ecriture_num, ecriture_date,\n  compte_num, compte_lib, comp_aux_num, comp_aux_lib,\n  piece_ref, piece_date, ecriture_lib,\n  debit, credit, ecriture_let, date_let, valid_date,\n  montant_devise, idevise, pcg_numero, hash_md5\nFROM _staging_fec\nON CONFLICT (hash_md5) DO NOTHING;"},
         'id': 'upsert', 'name': 'Upsert fec_ecriture',
         'type': 'n8n-nodes-base.postgres', 'typeVersion': 2.5,
         'position': [1980, 0], 'credentials': pg},
        {'parameters': {'operation': 'executeQuery',
         'query': "UPDATE fec_ecriture\nSET pcg_numero = resolve_compte(compte_num)\nWHERE pcg_numero IS NULL\n  AND entite_id = '{{ $json.entite_id }}';"},
         'id': 'resolve-pcg', 'name': 'Resolve pcg_numero',
         'type': 'n8n-nodes-base.postgres', 'typeVersion': 2.5,
         'position': [2200, 0], 'credentials': pg},
        {'parameters': {'operation': 'executeQuery',
         'query': "UPDATE fec_import\nSET\n  nb_lignes_brut = {{ $json.nb_lignes_brut }},\n  nb_lignes_inserees = (\n    SELECT COUNT(*) FROM fec_ecriture\n    WHERE fec_import_id = '{{ $json.fec_import_id }}'\n  ),\n  duree_secondes = EXTRACT(EPOCH FROM (now() - date_import)),\n  statut = 'termine'\nWHERE id = '{{ $json.fec_import_id }}';"},
         'id': 'stats', 'name': 'MAJ stats fec_import',
         'type': 'n8n-nodes-base.postgres', 'typeVersion': 2.5,
         'position': [2420, 0], 'credentials': pg},
        {'parameters': {'operation': 'executeQuery', 'query': 'SELECT refresh_all_views();'},
         'id': 'refresh', 'name': 'Refresh vues',
         'type': 'n8n-nodes-base.postgres', 'typeVersion': 2.5,
         'position': [440, 300], 'credentials': pg}
    ]

    connections = {
        'Declenchement manuel': {'main': [[{'node': 'Config 4 structures', 'type': 'main', 'index': 0}]]},
        'Config 4 structures': {'main': [[{'node': 'Boucle structures', 'type': 'main', 'index': 0}]]},
        'Boucle structures': {'main': [
            [{'node': 'Resolve IDs', 'type': 'main', 'index': 0}],
            [{'node': 'Refresh vues', 'type': 'main', 'index': 0}]
        ]},
        'Resolve IDs': {'main': [[{'node': 'Merge IDs + Token', 'type': 'main', 'index': 0}]]},
        'Merge IDs + Token': {'main': [[{'node': 'Create fec_import', 'type': 'main', 'index': 0}]]},
        'Create fec_import': {'main': [[{'node': 'Truncate staging', 'type': 'main', 'index': 0}]]},
        'Truncate staging': {'main': [[{'node': 'Fetch Pennylane + Map FEC', 'type': 'main', 'index': 0}]]},
        'Fetch Pennylane + Map FEC': {'main': [[{'node': 'Insert staging', 'type': 'main', 'index': 0}]]},
        'Insert staging': {'main': [[{'node': 'Upsert fec_ecriture', 'type': 'main', 'index': 0}]]},
        'Upsert fec_ecriture': {'main': [[{'node': 'Resolve pcg_numero', 'type': 'main', 'index': 0}]]},
        'Resolve pcg_numero': {'main': [[{'node': 'MAJ stats fec_import', 'type': 'main', 'index': 0}]]},
        'MAJ stats fec_import': {'main': [[{'node': 'Boucle structures', 'type': 'main', 'index': 0}]]}
    }

    payload = {
        'name': 'Sync Pennylane \u2192 Supabase (4 structures FEC) v2',
        'nodes': nodes,
        'connections': connections,
        'settings': {'executionOrder': 'v1'}
    }

    print('6. Deploy to n8n...')
    result = n8n_api('POST', '/workflows', n8n_key, payload)
    if 'id' in result:
        print(f'   OK: id={result["id"]} nodes={len(result["nodes"])}')
        for n in result['nodes']:
            creds = 'PG' if n.get('credentials') else '--'
            print(f'     {n["name"]:35s} creds={creds}')
    else:
        print(f'   ERROR: {json.dumps(result)[:500]}')
        sys.exit(1)

if __name__ == '__main__':
    main()
