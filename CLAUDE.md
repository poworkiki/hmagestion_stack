# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Aperçu du projet

HMA est un cabinet de gestion/expertise comptable basé en Guyane, gérant 4 structures (HMA, STIVMAT, STA, ETPA). Ce dépôt est le **point d'entrée unique** : documentation, inventaire des services, scripts d'automatisation et roadmap du stack self-hosted sur VPS Hostinger piloté par Coolify.

---

## Structure du dépôt

```
├── docs/
│   ├── stack.md                      # Architecture globale et choix techniques
│   ├── services.md                   # Inventaire des services déployés (source de vérité)
│   ├── runbooks.md                   # Procédures opérationnelles (déploiement, incidents, backups)
│   └── presentation-agent-ia-hma.md  # Présentation projet Agent IA comptable
├── scripts/
│   ├── vw-auth.sh                    # Auth OAuth Vaultwarden (source par les autres scripts)
│   ├── vw-healthcheck.sh             # Health check complet Vaultwarden
│   ├── vw-audit.sh                   # Audit du coffre Vaultwarden
│   ├── vw-backup.sh                  # Backup chiffré horodaté (rotation 30)
│   └── vw-add.sh                     # Ajout d'identifiant dans Vaultwarden
├── backups/                          # Dossier gitignored pour backups locaux
├── hardening.sh                      # Script de durcissement VPS (Fail2ban, SSH, UFW)
├── .env                              # Variables d'environnement (gitignored)
└── .specify/                         # Templates Spec-Kit (constitution non initialisée)
```

---

## Architecture globale

```
Utilisateurs → HTTPS → Traefik (SSL Let's Encrypt) → Coolify → Conteneurs Docker
                                    ↓
                          VPS Hostinger (Ubuntu 24.04)
                          Wildcard DNS *.hma.business
```

**Projets Coolify** : `hma-monitoring` (Uptime Kuma, Vaultwarden) · `hma-apps` (services métier). Tout nouveau service métier va dans `hma-apps`.

**Bases de données** : chaque service applicatif a sa propre instance PostgreSQL dédiée. Instance Supabase Cloud séparée pour ETL Pennylane (eu-west-3).

**Qdrant** : base vectorielle pour le RAG comptable. Accès interne uniquement (réseau Docker), protégé par API key.

**Infrastructure multi-VPS** :
- VPS principal (187.124.150.82) : Coolify HMA, tous les services métier
- VPS secondaire (168.231.69.226) : anciens services en cours de migration

Inventaire complet des services et de leur statut : `docs/services.md`

---

## Commandes utiles

### Variables d'environnement

Le `.env` contient des mots de passe avec caractères spéciaux (`$`, `!`, `#`). **Ne jamais utiliser `source .env`**. Extraire les variables ainsi :

```bash
VAULTWARDEN_URL=$(grep '^VAULTWARDEN_URL=' .env | cut -d= -f2-)
COOLIFY_API_TOKEN=$(grep '^COOLIFY_API_TOKEN=' .env | cut -d= -f2-)
```

Variables requises dans `.env` :
```
VAULTWARDEN_URL=https://vault.hma.business
VAULTWARDEN_CLIENT_ID=...
VAULTWARDEN_CLIENT_SECRET=...
COOLIFY_API_TOKEN=...
```

### Scripts Vaultwarden (API OAuth 2.0)

Tous les scripts chargent automatiquement le `.env` à la racine.

```bash
./scripts/vw-healthcheck.sh                              # Health check complet (HTTP, API, OAuth, Admin)
./scripts/vw-audit.sh                                     # Audit du coffre (éléments, stats, sécurité)
./scripts/vw-backup.sh [dossier_destination]              # Backup chiffré horodaté (rotation 30 derniers)
./scripts/vw-add.sh "Nom" "user" "pass" "https://url"    # Ajouter un identifiant
source scripts/vw-auth.sh                                 # Obtenir un token OAuth (utilisé par les autres scripts)
```

### Hardening VPS

```bash
sudo ./hardening.sh    # Fail2ban, SSH hardening, sysctl, UFW — à exécuter sur le VPS
```

### API Coolify

```bash
curl -s "https://coolify.hma.business/api/v1/services" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"

curl -s -X POST "https://coolify.hma.business/api/v1/services/{uuid}/start" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"
```

### API Pennylane (4 structures)

Tokens stockés dans Vaultwarden. Endpoint de base : `https://app.pennylane.com/api/external/v2`

```bash
curl -s "https://app.pennylane.com/api/external/v2/trial_balance?period_start=2025-01-01&period_end=2025-12-31" \
  -H "Authorization: Bearer $PENNYLANE_TOKEN"
```

Endpoints principaux : `/trial_balance`, `/ledger_entries`, `/ledger_accounts`, `/supplier_invoices`, `/customer_invoices`, `/suppliers`, `/customers`, `/journals`, `/categories`. Détails dans `docs/presentation-agent-ia-hma.md`.

### Accès SSH

```bash
ssh root@187.124.150.82                    # VPS HMA principal (clé id_ed25519)
ssh kiki@168.231.69.226                    # VPS secondaire (config ~/.ssh/config)
```

### Qdrant (KB interne)

Accès uniquement via réseau Docker interne (pas de port exposé).
```bash
# Depuis le VPS HMA :
APIKEY=$(docker inspect qdrant-obq4zyz8jnml2csbd0r0syq4 --format '{{range .Config.Env}}{{println .}}{{end}}' | grep QDRANT__SERVICE__API_KEY | cut -d= -f2)
IP=$(docker inspect qdrant-obq4zyz8jnml2csbd0r0syq4 --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
curl -s -H "api-key: $APIKEY" http://$IP:6333/collections
```

---

## Règles d'édition

- Toujours écrire en **français**
- Maintenir les tableaux Markdown **alignés et lisibles**
- Mettre à jour la date "Dernière mise à jour" dans le README lors de chaque modification significative
- Les statuts de services utilisent ces émojis normalisés :
  - ✅ `Actif` · 🚧 `En cours` · ⏸️ `Suspendu` · 🔴 `Inactif` · 🧪 `Test`

---

## Conventions

### Ajouter un service dans `docs/services.md`
Toujours renseigner **tous les champs** du tableau. Utiliser `—` si non applicable.
Ajouter une entrée dans "Historique des changements" en bas du fichier.

### Commits
Préfixe conventionnel obligatoire :
```
docs: ajout du service Mattermost dans l'inventaire
infra: déploiement Odoo via Coolify
chore: mise à jour des templates d'issues
fix: correction script vw-backup
```

### Nommage
```
Coolify :  hma-[projet]-[env]     → ex: hma-crm-production
GitHub :   hma-[type]-[nom]       → ex: hma-app-crm, hma-infra-scripts
Branches : main (prod) / develop (staging) / feature/* / fix/*
```

---

## Contraintes

- NE JAMAIS committer de secrets — tout passe par `.env` (gitignored) et Vaultwarden
- Privilégier les images Docker officielles pour les services
- Interface claire et minimaliste, pas de mode sombre pour le MVP
- Les tokens API (Pennylane, OpenAI, Qdrant) sont stockés **exclusivement dans Vaultwarden** — ne jamais les stocker en base PostgreSQL en clair

---

## Tests

À la fin de chaque développement impliquant l'interface graphique :
- Tester avec playwright-skill — l'interface doit être responsive, fonctionnelle et répondre au besoin développé

---

## Context7

Utiliser **toujours** Context7 (MCP) lorsqu'il y a besoin de :
- Génération de code
- Étapes de configuration ou d'installation
- Documentation de bibliothèque / API

Utiliser automatiquement les outils MCP Context7 (`resolve-library-id` puis `query-docs`) pour obtenir la documentation à jour, sans que l'utilisateur ait à le demander.

---

## Specify (Spec-Driven Development)

Ce dépôt utilise **Specify** (spec-kit) pour le développement piloté par spécifications.
Slash commands : `/speckit.constitution`, `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.implement`, `/speckit.clarify`, `/speckit.analyze`, `/speckit.checklist`.

- Toutes les spécifications doivent être rédigées en **français**, y compris les sections Purpose et Scenarios
- Seuls les titres de Requirements doivent rester en **anglais** avec les mots-clés `SHALL` / `MUST` pour la validation Spec-Kit

---

## Structures Pennylane

4 structures connectées via API (tokens en lecture seule dans Vaultwarden) :

| Structure | Activité | Token Vaultwarden |
|---|---|---|
| HMA | Holding | `Pennylane API — HMA` |
| STIVMAT | Transport de personnes | `Pennylane API — STIVMAT` |
| STA | Transport de personnes | `Pennylane API — STA` |
| ETPA | Transformation de produits agricoles | `Pennylane API — ETPA` |

Token sandbox : `Pennylane API Sandbox` (CLAUDE_SANDBOX)

---

## Projet en cours : Agent IA comptable

Voir `docs/presentation-agent-ia-hma.md` pour la présentation complète.

**Architecture multi-agents** (5 agents, orchestrés par n8n) :

```
Utilisateur → Directeur de Mission → Expert(s) → Réviseur Qualité → Synthèse → Utilisateur
```

| Agent | Rôle | Sources |
|---|---|---|
| Directeur de Mission | Route, délègue, synthétise | Appel des 4 autres agents |
| Expert-Comptable Senior | Chiffres + Social (paie, CC, LODEOM social) | Pennylane API, Supabase SQL, Qdrant KB |
| Juriste Senior | Droit fiscal, sociétés, contrats, travail | Qdrant KB (manuels, réglementation) |
| Analyste Financier Senior | SIG, ratios, simulations, recommandations | Supabase vues matérialisées, Pennylane API |
| Réviseur Qualité | Vérifie calculs, croise sources, score confiance | Supabase SQL, Qdrant KB, Pennylane API |

**Mémoire structurée** (3 niveaux par agent) :
- **Long terme** (Qdrant) : outputs passés indexés par similarité — 4 collections `agent_mem_*`
- **Court terme** (Supabase `agent_session`) : contexte session partagé entre agents
- **Procédurale** (Supabase `agent_feedback`) : scoring + few-shot injection

**Données** :
- **pcg_analytique** : mapping des 1 412 comptes PCG (SIG, CR, Bilan, Bilan fonctionnel, V/F)
- **fec_ecriture** : écritures comptables normalisées FEC (Art. A.47 A-1 LPF)
- **kb_pcg_analytique** : collection Qdrant pour le RAG comptable
- **Vues matérialisées** : mv_balance_generale, mv_sig, mv_compte_resultat, mv_bilan, mv_bilan_fonctionnel, mv_resultat_differentiel, mv_budget_vs_realise
