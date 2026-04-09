#!/bin/bash
# === Vaultwarden — Gestion unifiée des secrets ===
#
# Wrapper autour de vw-crypto.py (déchiffrement côté client)
# Organisation cible : stack_hma
#
# Usage:
#   ./scripts/vw-secret.sh get <nom>                              # Récupère le password d'un secret par nom exact
#   ./scripts/vw-secret.sh get <nom> --field username              # Récupère un champ spécifique (username, uri, notes)
#   ./scripts/vw-secret.sh get <nom> --json                        # Retourne tout le secret en JSON
#   ./scripts/vw-secret.sh list [filtre]                           # Liste les secrets (filtre optionnel)
#   ./scripts/vw-secret.sh export <nom> <VAR_ENV>                  # Affiche: export VAR_ENV=<password> (à utiliser avec eval)
#
# Exemples:
#   ./scripts/vw-secret.sh get "n8n API Key — HMA"
#   ./scripts/vw-secret.sh get "Pennylane API — HMA" --field username
#   ./scripts/vw-secret.sh list pennylane
#   eval $(./scripts/vw-secret.sh export "n8n API Key — HMA" N8N_API_KEY)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Trouver le bon Python (avec cryptography installé)
if "/c/Program Files/Python313/python.exe" -c "import cryptography" 2>/dev/null; then
  PYTHON="/c/Program Files/Python313/python.exe"
elif python3 -c "import cryptography" 2>/dev/null; then
  PYTHON="python3"
elif python -c "import cryptography" 2>/dev/null; then
  PYTHON="python"
else
  echo "❌ Python avec le module 'cryptography' requis. Installer: pip install cryptography" >&2
  exit 1
fi

# Déléguer à vw-crypto.py
exec "$PYTHON" "$SCRIPT_DIR/vw-crypto.py" "$@"
