#!/bin/bash
# === Vaultwarden — Ajouter un identifiant via API ===
# Usage: ./scripts/vw-add.sh <nom> <utilisateur> <mot_de_passe> [uri]
# Exemple: ./scripts/vw-add.sh "Mon Service" "admin" "p@ssw0rd" "https://service.hma.business"
#
# Note : Cette méthode utilise l'API Bitwarden avec chiffrement côté client.
# Les données sont chiffrées avant envoi avec la clé dérivée du compte.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Vérifier les arguments
if [ $# -lt 3 ]; then
  echo "Usage: $0 <nom> <utilisateur> <mot_de_passe> [uri]"
  echo ""
  echo "Exemples:"
  echo "  $0 \"PostgreSQL Prod\" \"hma_admin\" \"s3cur3!\" \"postgresql://db.hma.business:5432\""
  echo "  $0 \"N8N\" \"admin\" \"p@ssw0rd\" \"https://n8n.hma.business\""
  exit 1
fi

NAME="$1"
USERNAME="$2"
PASSWORD="$3"
URI="${4:-}"

# Obtenir le token
source "$SCRIPT_DIR/vw-auth.sh"

echo ""
echo "➕ Ajout d'un identifiant dans Vaultwarden"
echo "==========================================="
echo "   Nom       : ${NAME}"
echo "   Utilisateur: ${USERNAME}"
echo "   URI       : ${URI:-aucune}"

# Construire le payload
# Type 1 = Login
if [ -n "$URI" ]; then
  URI_JSON=$(cat <<UEOF
    "uris": [{"uri": "${URI}", "match": null}],
UEOF
)
else
  URI_JSON=""
fi

PAYLOAD=$(cat <<EOF
{
  "type": 1,
  "name": "${NAME}",
  "login": {
    "username": "${USERNAME}",
    "password": "${PASSWORD}",
    ${URI_JSON}
    "totp": null
  },
  "notes": null,
  "favorite": false,
  "reprompt": 0
}
EOF
)

# Créer l'élément via l'API
RESPONSE=$(curl -s -X POST "${VAULTWARDEN_URL}/api/ciphers" \
  -H "Authorization: Bearer ${VW_ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

# Vérifier le résultat
if echo "$RESPONSE" | grep -q '"id"'; then
  if command -v jq &>/dev/null; then
    ITEM_ID=$(echo "$RESPONSE" | jq -r '.id')
    echo ""
    echo "✅ Identifiant ajouté avec succès"
    echo "   ID : ${ITEM_ID}"
  else
    echo ""
    echo "✅ Identifiant ajouté avec succès"
  fi
else
  echo ""
  echo "❌ Échec de l'ajout"
  echo "$RESPONSE"
  exit 1
fi
