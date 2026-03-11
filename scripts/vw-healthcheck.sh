#!/bin/bash
# === Vaultwarden Health Check ===
# Vérifie que Vaultwarden est accessible et que l'API répond
# Usage: ./scripts/vw-healthcheck.sh
# Exit code: 0 = OK, 1 = KO

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [ -f "$ENV_FILE" ]; then
  while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
    key=$(echo "$key" | xargs)
    export "$key"="$value"
  done < "$ENV_FILE"
fi

: "${VAULTWARDEN_URL:?Variable VAULTWARDEN_URL manquante}"

echo "🔍 Health check Vaultwarden — ${VAULTWARDEN_URL}"
echo "---"

# 1. Vérifier que le serveur répond (HTTP)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${VAULTWARDEN_URL}/alive" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ Serveur HTTP : OK (${HTTP_CODE})"
else
  echo "❌ Serveur HTTP : KO (${HTTP_CODE})"
  exit 1
fi

# 2. Vérifier l'API Identity (endpoint de config)
API_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${VAULTWARDEN_URL}/api/config" 2>/dev/null || echo "000")
if [ "$API_CODE" = "200" ]; then
  echo "✅ API Config : OK (${API_CODE})"
else
  echo "⚠️  API Config : KO (${API_CODE})"
fi

# 3. Vérifier l'authentification OAuth 2.0
if [ -n "${VAULTWARDEN_CLIENT_ID:-}" ] && [ -n "${VAULTWARDEN_CLIENT_SECRET:-}" ]; then
  DEVICE_ID="hma-healthcheck-$(hostname | md5sum | cut -c1-32 2>/dev/null || echo 'healthcheck00000000000000000000')"
  AUTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
    -X POST "${VAULTWARDEN_URL}/identity/connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials" \
    -d "client_id=${VAULTWARDEN_CLIENT_ID}" \
    -d "client_secret=${VAULTWARDEN_CLIENT_SECRET}" \
    -d "scope=api" \
    -d "deviceIdentifier=${DEVICE_ID}" \
    -d "deviceType=14" \
    -d "deviceName=HMA-HealthCheck" 2>/dev/null || echo "000")
  if [ "$AUTH_RESPONSE" = "200" ]; then
    echo "✅ Auth OAuth 2.0 : OK"
  else
    echo "❌ Auth OAuth 2.0 : KO (${AUTH_RESPONSE})"
    exit 1
  fi
else
  echo "⏭️  Auth OAuth 2.0 : Skipped (credentials manquants)"
fi

# 4. Vérifier le panneau admin
ADMIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${VAULTWARDEN_URL}/admin" 2>/dev/null || echo "000")
if [ "$ADMIN_CODE" = "200" ] || [ "$ADMIN_CODE" = "302" ]; then
  echo "✅ Admin Panel : OK (${ADMIN_CODE})"
else
  echo "⚠️  Admin Panel : KO (${ADMIN_CODE})"
fi

echo "---"
echo "✅ Vaultwarden est opérationnel"
