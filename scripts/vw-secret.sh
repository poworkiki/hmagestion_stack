#!/bin/bash
# === Vaultwarden — Gestion unifiée des secrets ===
#
# Usage:
#   ./scripts/vw-secret.sh get <nom>                              # Récupère le password d'un secret par nom exact
#   ./scripts/vw-secret.sh get <nom> --field username              # Récupère un champ spécifique (username, uri, notes)
#   ./scripts/vw-secret.sh get <nom> --json                        # Retourne tout le secret en JSON
#   ./scripts/vw-secret.sh set <nom> <username> <password> [uri]   # Crée ou met à jour un secret
#   ./scripts/vw-secret.sh list [filtre]                           # Liste les secrets (filtre optionnel, insensible à la casse)
#   ./scripts/vw-secret.sh export <nom> <VAR_ENV>                  # Affiche: export VAR_ENV=<password> (à utiliser avec eval)
#
# Exemples:
#   ./scripts/vw-secret.sh get "n8n API Key — HMA"
#   ./scripts/vw-secret.sh get "Pennylane API — HMA" --field username
#   ./scripts/vw-secret.sh set "n8n API Key — HMA" "api-key" "ma-cle-secrete" "https://n8n.hma.business"
#   ./scripts/vw-secret.sh list pennylane
#   eval $(./scripts/vw-secret.sh export "n8n API Key — HMA" N8N_API_KEY)
#
# Sécurité:
#   - Les passwords ne sont JAMAIS affichés dans les logs ou messages d'erreur
#   - Le token OAuth est éphémère (durée de vie limitée par Vaultwarden)
#   - Aucun secret n'est écrit sur disque (tout reste en mémoire/stdout)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Couleurs (désactivées si stdout n'est pas un terminal) ---
if [ -t 1 ]; then
  RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; NC='\033[0m'
else
  RED=''; GREEN=''; YELLOW=''; CYAN=''; NC=''
fi

# --- Fonctions utilitaires ---

usage() {
  echo -e "${CYAN}Usage:${NC}"
  echo "  $0 get <nom> [--field username|uri|notes] [--json]"
  echo "  $0 set <nom> <username> <password> [uri]"
  echo "  $0 list [filtre]"
  echo "  $0 export <nom> <VAR_ENV>"
  exit 1
}

error() {
  echo -e "${RED}❌ $1${NC}" >&2
  exit 1
}

info() {
  echo -e "${GREEN}$1${NC}" >&2
}

# --- Authentification Vaultwarden (réutilise vw-auth.sh) ---

vw_authenticate() {
  # Charger .env
  ENV_FILE="$SCRIPT_DIR/../.env"
  if [ -f "$ENV_FILE" ]; then
    while IFS='=' read -r key value; do
      [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
      key=$(echo "$key" | xargs)
      export "$key"="$value"
    done < "$ENV_FILE"
  fi

  : "${VAULTWARDEN_URL:?Variable VAULTWARDEN_URL manquante dans .env}"
  : "${VAULTWARDEN_CLIENT_ID:?Variable VAULTWARDEN_CLIENT_ID manquante dans .env}"
  : "${VAULTWARDEN_CLIENT_SECRET:?Variable VAULTWARDEN_CLIENT_SECRET manquante dans .env}"

  DEVICE_ID="hma-cli-$(echo "$(hostname)" | md5sum | cut -c1-32 2>/dev/null || echo 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4')"

  VW_TOKEN_RESPONSE=$(curl -s -X POST "${VAULTWARDEN_URL}/identity/connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials" \
    -d "client_id=${VAULTWARDEN_CLIENT_ID}" \
    -d "client_secret=${VAULTWARDEN_CLIENT_SECRET}" \
    -d "scope=api" \
    -d "deviceIdentifier=${DEVICE_ID}" \
    -d "deviceType=14" \
    -d "deviceName=HMA-CLI")

  VW_ACCESS_TOKEN=$(echo "$VW_TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

  if [ -z "$VW_ACCESS_TOKEN" ]; then
    error "Authentification Vaultwarden échouée"
  fi
}

# --- Récupérer tous les ciphers (cache en mémoire pour la session) ---

vw_fetch_ciphers() {
  VW_CIPHERS=$(curl -s "${VAULTWARDEN_URL}/api/ciphers" \
    -H "Authorization: Bearer ${VW_ACCESS_TOKEN}")
}

# --- Commande GET ---

cmd_get() {
  local name="$1"
  shift
  local field=""
  local json_mode=false

  while [ $# -gt 0 ]; do
    case "$1" in
      --field) field="$2"; shift 2 ;;
      --json) json_mode=true; shift ;;
      *) error "Option inconnue: $1" ;;
    esac
  done

  vw_authenticate
  vw_fetch_ciphers

  local result
  result=$(echo "$VW_CIPHERS" | PYTHONUTF8=1 python3 -c "
import json, sys

data = json.load(sys.stdin)
name = sys.argv[1]
field = sys.argv[2]
json_mode = sys.argv[3] == 'true'

# Recherche exacte d'abord, puis par sous-chaine si pas de match
matches = [i for i in data.get('data', []) if i.get('name') == name]
if not matches:
    matches = [i for i in data.get('data', []) if name.lower() in i.get('name', '').lower()]
if len(matches) > 1:
    print(f'Ambiguous: {len(matches)} matches', file=sys.stderr)
    for m in matches:
        print(f'  - {m.get(\"name\")}', file=sys.stderr)
    sys.exit(1)

for item in matches:
        login = item.get('login', {}) or {}
        if json_mode:
            # Retourner tout sauf le password masqué en mode json
            out = {
                'name': item.get('name'),
                'username': login.get('username'),
                'uri': [u.get('uri', '') for u in login.get('uris', [])],
                'has_password': bool(login.get('password')),
                'notes': item.get('notes'),
            }
            print(json.dumps(out, ensure_ascii=False))
        elif field == 'username':
            print(login.get('username', ''))
        elif field == 'uri':
            uris = login.get('uris', [])
            print(uris[0].get('uri', '') if uris else '')
        elif field == 'notes':
            print(item.get('notes', '') or '')
        elif field == 'password' or field == '':
            print(login.get('password', ''))
        else:
            print('')
        sys.exit(0)

sys.exit(1)
" "$name" "${field:-password}" "$json_mode" 2>/dev/null)

  local exit_code=$?
  if [ $exit_code -ne 0 ]; then
    error "Secret '$name' introuvable dans Vaultwarden"
  fi

  echo "$result"
}

# --- Commande SET (crée ou met à jour) ---

cmd_set() {
  if [ $# -lt 3 ]; then
    error "Usage: $0 set <nom> <username> <password> [uri]"
  fi

  local name="$1"
  local username="$2"
  local password="$3"
  local uri="${4:-}"

  vw_authenticate
  vw_fetch_ciphers

  # Vérifier si le secret existe déjà
  local existing_id
  existing_id=$(echo "$VW_CIPHERS" | PYTHONUTF8=1 python3 -c "
import json, sys
data = json.load(sys.stdin)
name = sys.argv[1]
for item in data.get('data', []):
    if item.get('name') == name:
        print(item.get('id', ''))
        sys.exit(0)
sys.exit(1)
" "$name" 2>/dev/null) || true

  # Construire le payload
  local payload
  payload=$(PYTHONUTF8=1 python3 -c "
import json, sys
name, username, password, uri = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
obj = {
    'type': 1,
    'name': name,
    'login': {
        'username': username,
        'password': password,
        'totp': None
    },
    'notes': None,
    'favorite': False,
    'reprompt': 0
}
if uri:
    obj['login']['uris'] = [{'uri': uri, 'match': None}]
print(json.dumps(obj))
" "$name" "$username" "$password" "$uri")

  local response
  if [ -n "$existing_id" ]; then
    # UPDATE (PUT)
    response=$(curl -s -X PUT "${VAULTWARDEN_URL}/api/ciphers/${existing_id}" \
      -H "Authorization: Bearer ${VW_ACCESS_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$payload")
    info "✅ Secret '$name' mis à jour"
  else
    # CREATE (POST)
    response=$(curl -s -X POST "${VAULTWARDEN_URL}/api/ciphers" \
      -H "Authorization: Bearer ${VW_ACCESS_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$payload")
    info "✅ Secret '$name' créé"
  fi

  # Vérifier le résultat
  if ! echo "$response" | grep -q '"id"'; then
    error "Échec de l'opération: $(echo "$response" | head -c 200)"
  fi
}

# --- Commande LIST ---

cmd_list() {
  local filter="${1:-}"

  vw_authenticate
  vw_fetch_ciphers

  echo "$VW_CIPHERS" | PYTHONUTF8=1 PYTHONUTF8=1 python3 -c "
import json, sys

data = json.load(sys.stdin)
filtre = sys.argv[1].lower() if len(sys.argv) > 1 else ''

items = []
for item in data.get('data', []):
    name = item.get('name', '')
    if filtre and filtre not in name.lower():
        continue
    login = item.get('login', {}) or {}
    username = login.get('username', '') or ''
    uris = login.get('uris', []) or []
    uri = uris[0].get('uri', '') if uris else ''
    has_pw = 'YES' if login.get('password') else 'NO'
    items.append((name, username, uri, has_pw))

if not items:
    print('Aucun secret' + (f' pour \"{filtre}\"' if filtre else ''))
    sys.exit(0)

# Affichage tabulaire
max_name = max(len(i[0]) for i in items)
max_user = max(len(i[1]) for i in items)
header = f\"{'Nom':<{max_name}}  {'Username':<{max_user}}  {'Password':>8}  URI\"
print(header)
print('-' * len(header))
for name, user, uri, has_pw in sorted(items):
    print(f'{name:<{max_name}}  {user:<{max_user}}  {has_pw:>8}  {uri}')
print(f'\n{len(items)} secret(s)')
" "$filter"
}

# --- Commande EXPORT ---

cmd_export() {
  if [ $# -lt 2 ]; then
    error "Usage: $0 export <nom> <VAR_ENV>"
  fi

  local name="$1"
  local var_name="$2"
  local password
  password=$(cmd_get "$name")

  if [ -z "$password" ]; then
    error "Password vide pour '$name'"
  fi

  # Afficher la commande export (à utiliser avec eval)
  echo "export ${var_name}='${password}'"
}

# --- Point d'entrée ---

if [ $# -lt 1 ]; then
  usage
fi

COMMAND="$1"
shift

case "$COMMAND" in
  get)    [ $# -lt 1 ] && error "Usage: $0 get <nom> [--field ...] [--json]"; cmd_get "$@" ;;
  set)    cmd_set "$@" ;;
  list)   cmd_list "$@" ;;
  export) cmd_export "$@" ;;
  *)      error "Commande inconnue: $COMMAND"; usage ;;
esac
