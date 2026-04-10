"""
Bot Telegram HMAGENTS — mode polling (pas de webhook).
Fait le pont entre Telegram et l'API HMAGENTS /ask.

Usage:
  python3 telegram_bot.py

Env vars requises:
  TELEGRAM_BOT_TOKEN  — token du bot @hmagents_bot
  HMAGENTS_URL        — URL de l'API HMAGENTS (default: http://hmagents:8000)
"""
import os
import re
import json
import time
import logging
import urllib.request
import urllib.parse
import urllib.error

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('telegram_bot')

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
HMAGENTS_URL = os.environ.get('HMAGENTS_URL', 'http://hmagents:8000')
POLL_TIMEOUT = 30  # long polling timeout (seconds)

ENTITES = ['HMA', 'STIVMAT', 'STA', 'ETPA']

WELCOME_MSG = (
    "Salut {name} !\n\n"
    "Je suis le bot des agents comptables HMA.\n\n"
    "Pose-moi une question sur les 4 structures :\n"
    "- HMA (Holding)\n"
    "- STIVMAT (Transport)\n"
    "- STA (Transport)\n"
    "- ETPA (Agro-alimentaire)\n\n"
    "Exemples :\n"
    "- Quel est le CA de STIVMAT en 2025 ?\n"
    "- Analyse le SIG de ETPA\n"
    "- Montre le bilan de HMA"
)


def tg_api(method, data=None):
    """Appel API Telegram Bot."""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/{method}'
    if data:
        body = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=body,
                                     headers={'Content-Type': 'application/json'})
    else:
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=POLL_TIMEOUT + 10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        log.error(f'Telegram API error {e.code}: {body}')
        return {'ok': False, 'description': body}
    except Exception as e:
        log.error(f'Telegram API exception: {e}')
        return {'ok': False, 'description': str(e)}


def send_message(chat_id, text):
    """Envoie un message Telegram (tronque a 4096 chars)."""
    if len(text) > 4000:
        text = text[:3997] + '...'
    return tg_api('sendMessage', {'chat_id': chat_id, 'text': text})


def send_typing(chat_id):
    """Envoie l'indicateur 'typing'."""
    tg_api('sendChatAction', {'chat_id': chat_id, 'action': 'typing'})


def parse_message(text):
    """Extrait entite et exercice du message."""
    entite = None
    for e in ENTITES:
        if e in text.upper():
            entite = e
            break

    year_match = re.search(r'\b(202[0-9])\b', text)
    exercice = year_match.group(1) if year_match else str(time.localtime().tm_year)

    return entite, exercice


def call_hmagents(question, entite, exercice):
    """Appel POST vers HMAGENTS /ask."""
    url = f'{HMAGENTS_URL}/ask'
    payload = json.dumps({
        'question': question,
        'entite': entite,
        'exercice': exercice
    }).encode('utf-8')
    req = urllib.request.Request(url, data=payload,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('reponse', 'Aucune reponse des agents.')
    except Exception as e:
        log.error(f'HMAGENTS error: {e}')
        return f'Erreur lors de la consultation des agents : {e}'


def handle_message(message):
    """Traite un message Telegram."""
    chat_id = message['chat']['id']
    text = message.get('text', '')
    first_name = message.get('from', {}).get('first_name', 'Utilisateur')

    if not text:
        return

    # Commande /start
    if text.strip() == '/start':
        send_message(chat_id, WELCOME_MSG.format(name=first_name))
        return

    # Commande /help
    if text.strip() == '/help':
        send_message(chat_id, WELCOME_MSG.format(name=first_name))
        return

    # Question aux agents
    entite, exercice = parse_message(text)

    # Indicateur de saisie + message d'attente
    send_typing(chat_id)
    send_message(chat_id, 'Analyse en cours... Les agents travaillent sur ta question.')

    # Appel HMAGENTS
    reponse = call_hmagents(text, entite, exercice)

    # Formatage reponse
    header = f'{entite or "Toutes structures"} - Exercice {exercice}\n\n'
    send_message(chat_id, header + reponse)


def main():
    if not BOT_TOKEN:
        log.error('TELEGRAM_BOT_TOKEN non defini')
        return

    # Supprimer le webhook si present (on passe en polling)
    tg_api('deleteWebhook')
    log.info(f'Bot demarre en mode polling — {HMAGENTS_URL}')

    offset = 0
    while True:
        try:
            result = tg_api('getUpdates', {
                'offset': offset,
                'timeout': POLL_TIMEOUT,
                'allowed_updates': ['message']
            })

            if not result.get('ok'):
                log.warning(f'getUpdates failed: {result.get("description")}')
                time.sleep(5)
                continue

            for update in result.get('result', []):
                offset = update['update_id'] + 1
                if 'message' in update:
                    try:
                        handle_message(update['message'])
                    except Exception as e:
                        log.error(f'Error handling message: {e}')
                        chat_id = update['message'].get('chat', {}).get('id')
                        if chat_id:
                            send_message(chat_id, f'Erreur interne : {e}')

        except KeyboardInterrupt:
            log.info('Arret du bot')
            break
        except Exception as e:
            log.error(f'Polling error: {e}')
            time.sleep(5)


if __name__ == '__main__':
    main()
