"""
Deploy le workflow Telegram -> HMAGENTS dans n8n.
Cree aussi le credential Telegram si absent.
Usage: python3 scripts/deploy-telegram-bot.py
"""
import json, subprocess, os, sys

# Import VwSession depuis vw-crypto.py (meme dossier)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
vw_crypto = import_module('vw-crypto')
VwSession = vw_crypto.VwSession
load_env = vw_crypto.load_env
ORG_ID = vw_crypto.ORG_ID


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

    # 1. Auth Vaultwarden (dechiffrement complet)
    print('1. Auth Vaultwarden...')
    vw = VwSession(
        env['VAULTWARDEN_URL'],
        env.get('VAULTWARDEN_EMAIL', 'poworkiki@gmail.com'),
        env['VAULTWARDEN_MASTER_PASSWORD']
    )
    vw.login()

    ciphers = vw.fetch_ciphers(org_id=ORG_ID)
    n8n_key = ''
    telegram_token = ''

    for cipher in ciphers:
        dec = vw.decrypt_cipher(cipher)
        name = dec['name'].lower()
        pw = dec.get('password', '')
        if 'n8n' in name and 'api' in name and 'key' in name and pw:
            n8n_key = pw
        if 'telegram' in name and 'hmagents' in name and pw:
            telegram_token = pw

    if not n8n_key:
        print('ERREUR: Cle API n8n introuvable dans Vaultwarden')
        sys.exit(1)
    if not telegram_token:
        print('ERREUR: Token Telegram HMAGENTS introuvable dans Vaultwarden')
        sys.exit(1)
    print(f'   n8n key: {len(n8n_key)} chars')
    print(f'   telegram token: {telegram_token[:15]}...')

    # 2. Chercher ou creer le credential Telegram dans n8n
    print('2. Credential Telegram dans n8n...')
    creds = n8n_api('GET', '/credentials', n8n_key).get('data', [])
    tg_cred = None
    for c in creds:
        if c.get('type') == 'telegramApi':
            tg_cred = {'id': c['id'], 'name': c['name']}
            break

    if not tg_cred:
        print('   Creation du credential Telegram...')
        cred_payload = {
            'name': 'Telegram HMAGENTS Bot',
            'type': 'telegramApi',
            'data': {'accessToken': telegram_token}
        }
        result = n8n_api('POST', '/credentials', n8n_key, cred_payload)
        if 'id' in result:
            tg_cred = {'id': result['id'], 'name': result['name']}
            print(f'   OK: id={tg_cred["id"]}')
        else:
            print(f'   ERREUR: {json.dumps(result)[:300]}')
            sys.exit(1)
    else:
        print(f'   Existant: {tg_cred["name"]} (id={tg_cred["id"]})')

    # 3. Supprimer ancien workflow Telegram si existant
    print('3. Nettoyage anciens workflows Telegram...')
    wfs = n8n_api('GET', '/workflows', n8n_key).get('data', [])
    for wf in wfs:
        wf_name = wf.get('name', '').lower()
        if 'telegram' in wf_name and 'hmagents' in wf_name:
            n8n_api('DELETE', f'/workflows/{wf["id"]}', n8n_key)
            print(f'   Supprime: {wf["id"]} {wf["name"]}')

    # 4. Construire et deployer le workflow
    print('4. Deploiement workflow...')
    tg_credential = {'telegramApi': {'id': str(tg_cred['id']), 'name': tg_cred['name']}}

    nodes = [
        {
            'parameters': {'updates': ['message'], 'additionalFields': {}},
            'name': 'Telegram Trigger',
            'type': 'n8n-nodes-base.telegramTrigger',
            'typeVersion': 1.1,
            'position': [220, 300],
            'credentials': tg_credential
        },
        {
            'parameters': {
                'jsCode': (
                    "// Parse le message Telegram\n"
                    "const msg = $input.first().json.message;\n"
                    "const text = msg.text || '';\n"
                    "const chatId = msg.chat.id;\n"
                    "const firstName = msg.from.first_name || 'Utilisateur';\n\n"
                    "// Commande /start\n"
                    "if (text === '/start') {\n"
                    "  return [{ json: { chatId, isStart: true, firstName } }];\n"
                    "}\n\n"
                    "// Detection entite\n"
                    "const entites = ['HMA', 'STIVMAT', 'STA', 'ETPA'];\n"
                    "let entite = null;\n"
                    "for (const e of entites) {\n"
                    "  if (text.toUpperCase().includes(e)) {\n"
                    "    entite = e;\n"
                    "    break;\n"
                    "  }\n"
                    "}\n\n"
                    "// Detection exercice (annee 4 chiffres)\n"
                    "const yearMatch = text.match(/\\\\b(202[0-9])\\\\b/);\n"
                    "const exercice = yearMatch ? yearMatch[1] : new Date().getFullYear().toString();\n\n"
                    "return [{ json: { question: text, entite, exercice, chatId, isStart: false, firstName } }];\n"
                )
            },
            'name': 'Parse Message',
            'type': 'n8n-nodes-base.code',
            'typeVersion': 2,
            'position': [440, 300]
        },
        {
            'parameters': {
                'conditions': {
                    'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'strict'},
                    'conditions': [{
                        'id': 'is-start',
                        'leftValue': '={{ $json.isStart }}',
                        'rightValue': True,
                        'operator': {'type': 'boolean', 'operation': 'equals', 'name': 'filter.operator.equals'}
                    }],
                    'combinator': 'and'
                }
            },
            'name': 'Is /start?',
            'type': 'n8n-nodes-base.if',
            'typeVersion': 2.2,
            'position': [660, 300]
        },
        {
            'parameters': {
                'operation': 'sendMessage',
                'chatId': '={{ $json.chatId }}',
                'text': '={{ "Salut " + $json.firstName + " !\\n\\nJe suis le bot des agents comptables HMA.\\n\\nPose-moi une question sur les 4 structures :\\n- HMA (Holding)\\n- STIVMAT (Transport)\\n- STA (Transport)\\n- ETPA (Agro-alimentaire)\\n\\nExemples :\\n- Quel est le CA de STIVMAT en 2025 ?\\n- Analyse le SIG de ETPA\\n- Montre le bilan de HMA" }}',
                'additionalFields': {}
            },
            'name': 'Welcome Message',
            'type': 'n8n-nodes-base.telegram',
            'typeVersion': 1.2,
            'position': [880, 160],
            'credentials': tg_credential
        },
        {
            'parameters': {
                'operation': 'sendMessage',
                'chatId': '={{ $json.chatId }}',
                'text': 'Analyse en cours... Les agents travaillent sur ta question.',
                'additionalFields': {}
            },
            'name': 'Typing Indicator',
            'type': 'n8n-nodes-base.telegram',
            'typeVersion': 1.2,
            'position': [880, 440],
            'credentials': tg_credential
        },
        {
            'parameters': {
                'method': 'POST',
                'url': 'https://agents.hma.business/ask',
                'sendBody': True,
                'specifyBody': 'json',
                'jsonBody': '={{ JSON.stringify({ question: $json.question, entite: $json.entite, exercice: $json.exercice }) }}',
                'options': {'timeout': 180000}
            },
            'name': 'HMAGENTS /ask',
            'type': 'n8n-nodes-base.httpRequest',
            'typeVersion': 4.2,
            'position': [1100, 440]
        },
        {
            'parameters': {
                'jsCode': (
                    "// Formater la reponse pour Telegram (max 4096 chars)\n"
                    "const input = $input.first().json;\n"
                    "const reponse = input.reponse || 'Aucune reponse des agents.';\n"
                    "const entite = input.entite || 'Toutes';\n"
                    "const exercice = input.exercice || '';\n\n"
                    "let msg = entite + ' - Exercice ' + exercice + '\\n\\n' + reponse;\n\n"
                    "// Telegram limite a 4096 caracteres\n"
                    "if (msg.length > 4000) {\n"
                    "  msg = msg.substring(0, 3997) + '...';\n"
                    "}\n\n"
                    "const chatId = $('Parse Message').first().json.chatId;\n"
                    "return [{ json: { chatId, msg } }];\n"
                )
            },
            'name': 'Format Response',
            'type': 'n8n-nodes-base.code',
            'typeVersion': 2,
            'position': [1320, 440]
        },
        {
            'parameters': {
                'operation': 'sendMessage',
                'chatId': '={{ $json.chatId }}',
                'text': '={{ $json.msg }}',
                'additionalFields': {}
            },
            'name': 'Reply Telegram',
            'type': 'n8n-nodes-base.telegram',
            'typeVersion': 1.2,
            'position': [1540, 440],
            'credentials': tg_credential
        }
    ]

    connections = {
        'Telegram Trigger': {'main': [[{'node': 'Parse Message', 'type': 'main', 'index': 0}]]},
        'Parse Message': {'main': [[{'node': 'Is /start?', 'type': 'main', 'index': 0}]]},
        'Is /start?': {'main': [
            [{'node': 'Welcome Message', 'type': 'main', 'index': 0}],
            [{'node': 'Typing Indicator', 'type': 'main', 'index': 0}]
        ]},
        'Typing Indicator': {'main': [[{'node': 'HMAGENTS /ask', 'type': 'main', 'index': 0}]]},
        'HMAGENTS /ask': {'main': [[{'node': 'Format Response', 'type': 'main', 'index': 0}]]},
        'Format Response': {'main': [[{'node': 'Reply Telegram', 'type': 'main', 'index': 0}]]}
    }

    payload = {
        'name': 'Telegram \u2192 HMAGENTS',
        'nodes': nodes,
        'connections': connections,
        'settings': {'executionOrder': 'v1'}
    }

    result = n8n_api('POST', '/workflows', n8n_key, payload)
    if 'id' in result:
        wf_id = result['id']
        print(f'   OK: workflow id={wf_id}, {len(result["nodes"])} noeuds')

        # 5. Activer le workflow
        print('5. Activation du workflow...')
        activate = n8n_api('PATCH', f'/workflows/{wf_id}', n8n_key, {'active': True})
        if activate.get('active'):
            print('   OK: workflow actif !')
        else:
            print(f'   ATTENTION: activation echouee')
            print(f'   Activer manuellement : https://n8n.hma.business/workflow/{wf_id}')
    else:
        print(f'   ERREUR: {json.dumps(result)[:500]}')
        sys.exit(1)

    print(f'\nBot Telegram pret : https://t.me/hmagents_bot')


if __name__ == '__main__':
    main()
