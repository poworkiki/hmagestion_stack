#!/bin/bash
# === Vaultwarden OAuth 2.0 — Obtenir un token d'accès ===
# Usage: source scripts/vw-auth.sh
# Nécessite: .env chargé ou variables d'environnement définies

set -euo pipefail

# Charger .env si présent (gestion des caractères spéciaux)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [ -f "$ENV_FILE" ]; then
  while IFS='=' read -r key value; do
    # Ignorer les commentaires et lignes vides
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
    key=$(echo "$key" | xargs)
    export "$key"="$value"
  done < "$ENV_FILE"
fi

# Vérification des variables requises
: "${VAULTWARDEN_URL:?Variable VAULTWARDEN_URL manquante}"
: "${VAULTWARDEN_CLIENT_ID:?Variable VAULTWARDEN_CLIENT_ID manquante}"
: "${VAULTWARDEN_CLIENT_SECRET:?Variable VAULTWARDEN_CLIENT_SECRET manquante}"

# Identifiant unique de l'appareil (généré une fois, stable)
DEVICE_ID="hma-cli-$(hostname | md5sum | cut -c1-32 2>/dev/null || echo 'a]1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4')"

# Obtenir le token OAuth 2.0
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
  echo "❌ Échec d'authentification Vaultwarden"
  echo "$VW_TOKEN_RESPONSE"
  exit 1
fi

export VW_ACCESS_TOKEN
echo "✅ Token Vaultwarden obtenu"
