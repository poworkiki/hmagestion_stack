#!/bin/bash
# === Vaultwarden Backup — Export chiffré du coffre ===
# Exporte les données du coffre dans un fichier JSON horodaté
# Usage: ./scripts/vw-backup.sh [dossier_destination]
# Les données exportées sont chiffrées côté serveur (clé utilisateur)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${1:-$SCRIPT_DIR/../backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/vaultwarden_backup_${TIMESTAMP}.json"

# Créer le dossier de backup
mkdir -p "$BACKUP_DIR"

# Obtenir le token
source "$SCRIPT_DIR/vw-auth.sh"

echo ""
echo "💾 Backup Vaultwarden"
echo "====================="

# Export via /api/sync (contient tout le coffre, chiffré)
echo "📥 Export du coffre en cours..."
SYNC_DATA=$(curl -s -X GET "${VAULTWARDEN_URL}/api/sync" \
  -H "Authorization: Bearer ${VW_ACCESS_TOKEN}" \
  -H "Content-Type: application/json")

# Vérifier que les données sont valides
if echo "$SYNC_DATA" | grep -q '"ciphers"'; then
  echo "$SYNC_DATA" > "$BACKUP_FILE"

  # Taille du fichier
  FILE_SIZE=$(wc -c < "$BACKUP_FILE" | tr -d ' ')

  # Nombre d'éléments
  if command -v jq &>/dev/null; then
    ITEM_COUNT=$(echo "$SYNC_DATA" | jq '.ciphers | length')
    FOLDER_COUNT=$(echo "$SYNC_DATA" | jq '.folders | length')
  else
    ITEM_COUNT=$(echo "$SYNC_DATA" | grep -o '"type":' | wc -l)
    FOLDER_COUNT="?"
  fi

  echo "✅ Backup sauvegardé : ${BACKUP_FILE}"
  echo "   📊 ${ITEM_COUNT} élément(s), ${FOLDER_COUNT} dossier(s)"
  echo "   📦 Taille : ${FILE_SIZE} octets"

  # Nettoyage des anciens backups (garder les 30 derniers)
  BACKUP_COUNT=$(ls -1 "${BACKUP_DIR}"/vaultwarden_backup_*.json 2>/dev/null | wc -l)
  if [ "$BACKUP_COUNT" -gt 30 ]; then
    echo "🧹 Nettoyage des anciens backups (>30)..."
    ls -1t "${BACKUP_DIR}"/vaultwarden_backup_*.json | tail -n +31 | xargs rm -f
    echo "   Supprimé $(( BACKUP_COUNT - 30 )) ancien(s) backup(s)"
  fi
else
  echo "❌ Échec du backup — réponse API invalide"
  echo "$SYNC_DATA"
  exit 1
fi

echo ""
echo "⚠️  Note : les données sont chiffrées avec la clé utilisateur."
echo "   Le mot de passe maître est nécessaire pour les déchiffrer."
echo ""
echo "✅ Backup terminé"
