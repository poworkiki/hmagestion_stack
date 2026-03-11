#!/bin/bash
# === Vaultwarden Audit — Lister les éléments du coffre ===
# Liste tous les identifiants avec leurs métadonnées (sans mots de passe)
# Usage: ./scripts/vw-audit.sh
# Nécessite: curl, jq (optionnel pour le formatage)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Obtenir le token
source "$SCRIPT_DIR/vw-auth.sh"

echo ""
echo "📋 Audit du coffre Vaultwarden"
echo "=============================="

# Récupérer les données du coffre via /api/sync
SYNC_DATA=$(curl -s -X GET "${VAULTWARDEN_URL}/api/sync" \
  -H "Authorization: Bearer ${VW_ACCESS_TOKEN}" \
  -H "Content-Type: application/json")

# Vérifier si jq est disponible
if command -v jq &>/dev/null; then
  # Nombre total d'éléments
  TOTAL=$(echo "$SYNC_DATA" | jq '.ciphers | length')
  echo "📊 Total d'éléments : ${TOTAL}"
  echo ""

  # Statistiques par type
  echo "📈 Répartition par type :"
  echo "$SYNC_DATA" | jq -r '.ciphers | group_by(.type) | .[] |
    "  - Type \(.[0].type) : \(length) élément(s)"'
  echo ""

  # Lister les éléments (nom + date de modification, PAS de mots de passe)
  echo "📝 Liste des éléments :"
  echo "---"
  echo "$SYNC_DATA" | jq -r '.ciphers[] |
    "  🔐 \(.name // "Sans nom")
     Dernière modif: \(.revisionDate // "inconnue")
     ID: \(.id)
  ---"'

  # Vérifications de sécurité
  echo ""
  echo "🔒 Vérifications de sécurité :"

  # Éléments sans URI
  NO_URI=$(echo "$SYNC_DATA" | jq '[.ciphers[] | select(.login != null and (.login.uris == null or (.login.uris | length) == 0))] | length')
  if [ "$NO_URI" -gt 0 ]; then
    echo "  ⚠️  ${NO_URI} identifiant(s) sans URI configurée"
  else
    echo "  ✅ Tous les identifiants ont une URI"
  fi

  # Éléments dans la corbeille
  TRASHED=$(echo "$SYNC_DATA" | jq '[.ciphers[] | select(.deletedDate != null)] | length')
  if [ "$TRASHED" -gt 0 ]; then
    echo "  🗑️  ${TRASHED} élément(s) dans la corbeille"
  else
    echo "  ✅ Corbeille vide"
  fi

  # Dernière rotation du coffre
  echo ""
  echo "👤 Profil :"
  echo "$SYNC_DATA" | jq -r '"  Email: \(.profile.email)
  Nom: \(.profile.name)
  Premium: \(.profile.premium)
  Dernière sync: \(.profile.securityStamp)"'

else
  # Fallback sans jq — affichage brut filtré
  echo "(Installer jq pour un affichage formaté : apt install jq)"
  echo ""
  echo "$SYNC_DATA" | grep -o '"name":"[^"]*"' | sed 's/"name":"//;s/"//' | while read -r name; do
    echo "  🔐 $name"
  done
fi

echo ""
echo "✅ Audit terminé"
