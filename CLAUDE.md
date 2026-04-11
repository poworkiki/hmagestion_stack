# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Aperçu du projet

HMA est un cabinet de gestion/expertise comptable basé en Guyane, gérant 4 structures (HMA, STIVMAT, STA, ETPA). Ce dépôt est le **point d'entrée unique** : documentation, inventaire des services, scripts d'automatisation et roadmap du stack self-hosted sur VPS Hostinger piloté par Coolify.

---

## Architecture globale

```
Utilisateurs → HTTPS → Traefik (SSL Let's Encrypt) → Coolify → Conteneurs Docker
                                    ↓
                          VPS Hostinger (Ubuntu 24.04)
                          Wildcard DNS *.hma.business
```

**Projets Coolify** : `hma-monitoring` (Uptime Kuma, Vaultwarden) · `hma-apps` (services métier). Tout nouveau service métier va dans `hma-apps`.

**Bases de données** : chaque service applicatif a sa propre instance PostgreSQL dédiée. Base métier principale : **PostgreSQL HMA standalone** (`hma-db`) — remplace Supabase self-hosted. Instance Supabase Cloud (eu-west-3) en veille.

**Qdrant** : base vectorielle pour le RAG comptable. Exposé en HTTPS sur `qdrant.hma.business`. API key dans `.mcp.json` et Vaultwarden. Serveur MCP local (`mcp-qdrant-hma/server.py`) pour accès direct depuis Claude Code.

**Infrastructure multi-VPS** :
- VPS principal (187.124.150.82) : Coolify HMA, tous les services métier
- VPS secondaire (168.231.69.226) : anciens services en cours de migration

**Stack de visualisation / saisie** (actif) :
- **HMAnalytics** (`gestion.hma.business`) : dashboard comptable principal, notebook Marimo réactif avec 6 onglets (Vue d'ensemble, CRD Réel, Bilan Fonctionnel, Budget CRD, Budget Trésorerie, SQL libre). Voir section dédiée plus bas.
- **Streamlit** (`streamlit.hma.business`) : dashboard checks rapides (11 pages), conteneur `hma-streamlit` séparé de `hma-toolbox`
- **pgAdmin** (`pgadmin.hma.business`) : administration PostgreSQL

**Stack de visualisation / saisie** (suspendu depuis 2026-04-11, stoppé pour libérer RAM VPS) :
- ⏸️ Superset (`superset.hma.business`) — image conservée
- ⏸️ Metabase — image conservée
- ⏸️ Appsmith (`appsmith.hma.business`) — image conservée

Services supprimés (avril 2026) : Teable, Supabase self-hosted, hma-dashboard (Dash/Plotly — remplacé par HMAnalytics + Streamlit).

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
VAULTWARDEN_URL=https://vaultwarden.poworkiki.cloud
VAULTWARDEN_CLIENT_ID=...
VAULTWARDEN_CLIENT_SECRET=...
VAULTWARDEN_EMAIL=poworkiki@gmail.com
VAULTWARDEN_MASTER_PASSWORD=...
COOLIFY_API_TOKEN=...
HMA_DB_URL=postgresql://postgres:PASSWORD@h2dnymbgnulve0kko87nh856:5432/postgres
```

### Scripts Vaultwarden (déchiffrement client-side)

Tous les scripts chargent automatiquement le `.env` à la racine.
Architecture : `vw-secret.sh` (wrapper bash) → `vw-crypto.py` (PBKDF2 + RSA-OAEP + AES-CBC).
Organisation cible : `stack_hma` (ID: `f7bd1540-c6ed-45fb-8e8e-3ca9a9d9db23`).
Requiert Python avec `cryptography` installé dans le venv système.

```bash
./scripts/vw-secret.sh get "Pennylane API — ETPA"                    # Récupère le password d'un secret
./scripts/vw-secret.sh get "Pennylane API — ETPA" --field username   # Récupère un champ spécifique
./scripts/vw-secret.sh list pennylane                                # Liste les secrets filtrés
eval $(./scripts/vw-secret.sh export "Pennylane API — ETPA" TOKEN)   # Exporte en variable d'env
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
Doc officielle : `pennylane.readme.io/reference`

```bash
# Récupérer un token depuis Vaultwarden puis appeler l'API
ETPA_TOKEN=$(./scripts/vw-secret.sh get "Pennylane API — ETPA")
curl -s "https://app.pennylane.com/api/external/v2/trial_balance?period_start=2025-01-01&period_end=2025-12-31&use_2026_api_changes=true&limit=100" \
  -H "Authorization: Bearer $ETPA_TOKEN"
```

**Pagination curseur** (obligatoire depuis 2026) : `cursor` + `limit` (max 100, sauf `/ledger_accounts` max 1000). Boucler tant que `has_more == true`.

Endpoints principaux : `/trial_balance`, `/ledger_entries`, `/ledger_entry_lines`, `/ledger_accounts`, `/supplier_invoices`, `/customer_invoices`, `/suppliers`, `/customers`, `/journals`, `/categories`, `/fiscal_years`, `/me`.
Contrat API détaillé : `specs/001-agent-ia-comptable/contracts/pennylane-api.md`

**Skill d'analyse** : `/pennylane-analyse` (`.claude/commands/pennylane-analyse.md`) — analyse comptable experte d'une structure via l'API Pennylane. Rapports sauvegardés dans `hma_holding/<STRUCTURE>/`.

### Qdrant (KB interne + MCP)

Accès HTTPS : `qdrant.hma.business`. API key dans Vaultwarden et `.mcp.json`.

```bash
# Lister les collections
curl -s -H "api-key: $QDRANT_API_KEY" https://qdrant.hma.business:443/collections
```

Serveur MCP local pour Claude Code (configuré dans `.mcp.json`) :
- `mcp-qdrant-hma/server.py` — FastMCP + OpenAI embeddings + Qdrant client
- Expose la KB comptable (18 000+ chunks) comme outils natifs

### Scripts PCG analytique

```bash
python3 scripts/generate-pcg-seed.py    # Génère sql/02-data/001-pcg-analytique-seed.sql
python3 scripts/generate-pcg-qdrant.py  # Génère les embeddings et alimente Qdrant kb_pcg_analytique
```

Source : Pennylane API `/ledger_accounts` (1 412 comptes) → mapping analytique Python (SIG, CR, Bilan, BF, V/F) → SQL seed.
Le mapping Python dans `generate-pcg-seed.py` est la **source de vérité unique** pour la classification des comptes.
`generate-pcg-qdrant.py` dérive la collection Qdrant `kb_pcg_analytique` à partir des mêmes données (embeddings OpenAI `text-embedding-3-small`).

### SQL PostgreSQL HMA

Exécuter les scripts dans l'ordre numérique par dossier :
```bash
# 1. Schéma
psql $HMA_DB_URL -f sql/01-schema/001-entite.sql
psql $HMA_DB_URL -f sql/01-schema/002-exercice.sql
psql $HMA_DB_URL -f sql/01-schema/003-pcg-analytique.sql
psql $HMA_DB_URL -f sql/01-schema/004-compte-resolution.sql
psql $HMA_DB_URL -f sql/01-schema/005-fec-import.sql
psql $HMA_DB_URL -f sql/01-schema/006-fec-ecriture.sql
psql $HMA_DB_URL -f sql/01-schema/007-sync-metadata.sql
psql $HMA_DB_URL -f sql/01-schema/008-dim-calendrier.sql
psql $HMA_DB_URL -f sql/01-schema/009-pcg-crd-mapping.sql
psql $HMA_DB_URL -f sql/01-schema/010-pennylane-balance.sql

# 2. Données de référence
psql $HMA_DB_URL -f sql/02-data/001-pcg-analytique-seed.sql

# 3. Fonctions (avant les vues qui en dépendent)
psql $HMA_DB_URL -f sql/04-functions/resolve-compte.sql
psql $HMA_DB_URL -f sql/04-functions/refresh-views.sql
psql $HMA_DB_URL -f sql/04-functions/refresh-views-conditional.sql

# 4. Vue matérialisée (seule MV restante) + vues simples
psql $HMA_DB_URL -f sql/03-views/001-mv-balance-generale.sql
psql $HMA_DB_URL -f sql/03-views/007-v-controles-coherence.sql
psql $HMA_DB_URL -f sql/03-views/009-vues-base-comptables.sql
psql $HMA_DB_URL -f sql/03-views/010-refactoring-vues-grand-livre.sql  # TOUTES les vues dérivées
```

**Architecture refactorée (avril 2026)** : les anciennes vues matérialisées (`mv_sig`, `mv_bilan`, `mv_compte_resultat`, `mv_bilan_fonctionnel`, `mv_resultat_differentiel`) ont été **supprimées**. Elles sont remplacées par des vues simples dérivées de `v_grand_livre` dans `010-refactoring-vues-grand-livre.sql`. Seule `mv_balance_generale` reste matérialisée.

```
fec_ecriture + pcg_analytique + dim_calendrier
    → v_grand_livre (source unique)
        → v_balance, v_sig, v_sig_drilldown
        → v_compte_resultat, v_crd, v_crd_drilldown
        → v_bilan, v_bilan_fonctionnel
        → v_ytd_mensuel/trimestriel/annuel
```

On peut aussi exécuter les migrations via SSH sur le VPS : `ssh root@187.124.150.82 "docker exec h2dnymbgnulve0kko87nh856 psql -U postgres -f /dev/stdin" < fichier.sql`

**Rafraîchissement** : `refresh_all_views()` ne rafraîchit que `mv_balance_generale` (seule vue matérialisée). Toutes les autres vues sont simples et se mettent à jour automatiquement.

### ETL Pennylane (sync incrémental)

```bash
# Script Python standalone (requiert pg8000, requests)
python3 scripts/sync-pennylane.py                     # Sync les 4 structures
python3 scripts/sync-pennylane.py --structure ETPA     # Sync une seule structure
python3 scripts/sync-pennylane.py --full-sync          # Force re-sync complet

# Via le conteneur hma-toolbox (Docker, pas besoin de deps locales)
cd hma-toolbox
docker compose run toolbox scripts/sync-pennylane.py
docker compose run toolbox scripts/sync-pennylane.py --structure HMA
docker compose run toolbox scripts/sync-pennylane.py --full              # Force full fetch
docker compose run toolbox scripts/sync-pennylane.py --skip-refresh      # Sync sans refresh vues
docker compose run toolbox scripts/sync-pennylane.py --force-refresh     # Force refresh meme sans changement
docker compose run toolbox scripts/sync-pennylane.py --endpoints journals ledger_accounts  # Endpoints specifiques
```

**Optimisations sync** :
- **Count check** : compare le nombre de lignes local vs Pennylane avant de syncer — skip si identique
- **sync_metadata** : table de tracking par structure/endpoint (dernier sync, count, statut)
- **Refresh conditionnel** : `refresh_views_if_needed()` ne rafraîchit les vues que si des données ont changé
- **Delta sync** : utilise `updated_since` basé sur le dernier import réussi
- **Fingerprint MD5** : déduplication via hash unique, `ON CONFLICT DO NOTHING`

### Contrôle de cohérence Pennylane vs GL

```bash
python3 scripts/sync-pennylane-balance.py                     # Import trial_balance Pennylane (contrôle)
python3 scripts/sync-pennylane-balance.py --structure STIVMAT  # Une seule structure
python3 scripts/sync-pennylane-balance.py --year 2025          # Année spécifique
```

Table `pennylane_balance` = snapshot de la trial_balance Pennylane. Vues de contrôle :
- `v_controle_balance` : compare GL (fec_ecriture) vs Pennylane (pennylane_balance) par compte
- `v_controle_resume` : résumé par structure (nb OK, nb écarts, écart total)

### Déploiement workflow n8n

```bash
python3 scripts/deploy-n8n-workflow.py n8n/workflow-sync-pennylane.json   # Déploie via l'API n8n
```

### Workflow n8n

`n8n/workflow-sync-pennylane.json` — workflow de synchronisation Pennylane → PostgreSQL pour les 4 structures.
- **Cron toutes les 2h** + déclenchement manuel
- Refresh conditionnel des vues (`refresh_views_if_needed()`)
- MAJ `sync_metadata` à chaque exécution
- À importer dans n8n via l'UI ou l'API

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
feat: ajout du workflow sync Pennylane
docs: ajout du service Mattermost dans l'inventaire
infra: déploiement Odoo via Coolify
sql:  nouvelle vue matérialisée mv_bilan
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

## Gestion des Credentials — Vaultwarden

Tous les credentials, clés API, secrets et accès de l'infrastructure HMA sont centralisés dans **Vaultwarden**, organisation **`stack_hma`**.

### Accès Vaultwarden

| Élément | Valeur |
|---------|--------|
| URL | `https://vaultwarden.poworkiki.cloud` |
| Compte | `poworkiki@gmail.com` |
| Organisation | `stack_hma` |
| Admin panel | `https://vaultwarden.poworkiki.cloud/admin` |

### Règles obligatoires

1. **Ne jamais hardcoder de secrets** dans le code, les fichiers `.env` commités, les prompts, ou les commentaires. Utiliser des variables d'environnement ou des références au coffre.
2. **Avant de créer un credential**, vérifier s'il existe déjà : `./scripts/vw-secret.sh list <mot-clé>`. Éviter les doublons.
3. **Tout nouveau credential** (clé API, token, mot de passe de service, accès BDD, etc.) doit être **enregistré dans Vaultwarden** immédiatement après création.
4. **Rotation de secrets** : utiliser `vw-secret.sh set` pour mettre à jour l'entrée existante — ne jamais créer de doublon.
5. **Nommage normalisé** des entrées : `<Type> — <Service/Structure>`. Exemples :
   - `Pennylane API — ETPA`
   - `PostgreSQL — Odoo`
   - `n8n API Key — HMA`

### Authentification API (OAuth 2.0 client_credentials)

Variables requises dans `.env` (gitignored, **jamais commité**) :
```
VAULTWARDEN_URL=https://vaultwarden.poworkiki.cloud
VAULTWARDEN_CLIENT_ID=...
VAULTWARDEN_CLIENT_SECRET=...
```

⚠️ Le `.env` contient des mots de passe avec caractères spéciaux (`$`, `!`, `#`). **Ne jamais utiliser `source .env`**. Les scripts chargent le `.env` automatiquement via parsing ligne par ligne.

### Scripts CLI — Référence complète

Tous les scripts sont dans `scripts/` et chargent automatiquement le `.env` à la racine.

#### Opérations CRUD sur les secrets

```bash
# LIRE un secret (password par défaut)
./scripts/vw-secret.sh get "Pennylane API — ETPA"

# LIRE un champ spécifique
./scripts/vw-secret.sh get "Pennylane API — ETPA" --field username
./scripts/vw-secret.sh get "Pennylane API — ETPA" --field uri
./scripts/vw-secret.sh get "Pennylane API — ETPA" --field notes

# LIRE tout le secret en JSON (password masqué)
./scripts/vw-secret.sh get "Pennylane API — ETPA" --json

# LISTER les secrets (avec filtre optionnel insensible à la casse)
./scripts/vw-secret.sh list                    # tout le coffre
./scripts/vw-secret.sh list pennylane          # filtré

# CRÉER un nouveau secret
./scripts/vw-secret.sh set "Nom du Secret" "username" "password" "https://url.service"

# METTRE À JOUR un secret existant (même nom = update automatique via PUT)
./scripts/vw-secret.sh set "Nom du Secret" "new_user" "new_password" "https://new-url"

# EXPORTER en variable d'environnement (pour scripts chaînés)
eval $(./scripts/vw-secret.sh export "Pennylane API — ETPA" PENNYLANE_TOKEN)
```

#### Opérations de maintenance

```bash
# HEALTH CHECK complet (HTTP, API Config, OAuth, Admin Panel)
./scripts/vw-healthcheck.sh

# AUDIT du coffre (inventaire, stats par type, vérifications sécurité)
./scripts/vw-audit.sh

# BACKUP chiffré horodaté (rotation automatique : 30 derniers conservés)
./scripts/vw-backup.sh                        # dans backups/ par défaut
./scripts/vw-backup.sh /chemin/custom          # dossier personnalisé

# AJOUT rapide (alternative simplifiée à vw-secret.sh set)
./scripts/vw-add.sh "Nom" "username" "password" "https://url"

# OBTENIR un token OAuth brut (pour scripts custom)
source scripts/vw-auth.sh                     # exporte $VW_ACCESS_TOKEN
```

### Workflow : Création d'un nouveau service

Quand un nouveau service est déployé (ex: nouveau conteneur Coolify) :

1. **Déployer** le service avec des credentials temporaires
2. **Vérifier** que le credential n'existe pas déjà :
   ```bash
   ./scripts/vw-secret.sh list <nom-service>
   ```
3. **Enregistrer** le credential dans Vaultwarden :
   ```bash
   ./scripts/vw-secret.sh set "<Type> — <Service>" "<username>" "<password>" "<url>"
   ```
4. **Vérifier** l'enregistrement :
   ```bash
   ./scripts/vw-secret.sh get "<Type> — <Service>" --json
   ```
5. **Mettre à jour** `docs/services.md` si c'est un nouveau service

### Workflow : Rotation d'un secret

1. **Générer** le nouveau secret côté service
2. **Mettre à jour** dans Vaultwarden (`set` avec le même nom fait un PUT) :
   ```bash
   ./scripts/vw-secret.sh set "Nom Existant" "user" "nouveau_password" "url"
   ```
3. **Mettre à jour** le `.env` local si le secret y est référencé
4. **Redémarrer** les services impactés
5. **Backup** après rotation : `./scripts/vw-backup.sh`

### Workflow : Récupération d'un token pour appel API

```bash
# Méthode 1 : variable inline
TOKEN=$(./scripts/vw-secret.sh get "Pennylane API — ETPA")
curl -s "https://app.pennylane.com/api/external/v2/me" -H "Authorization: Bearer $TOKEN"

# Méthode 2 : export pour la session
eval $(./scripts/vw-secret.sh export "Pennylane API — ETPA" PENNYLANE_TOKEN)
curl -s "https://app.pennylane.com/api/external/v2/me" -H "Authorization: Bearer $PENNYLANE_TOKEN"
```

### API REST directe (pour scripts Python ou cas avancés)

```
POST /identity/connect/token          → Obtenir un access_token (OAuth 2.0 client_credentials)
GET  /api/ciphers                     → Lister tous les secrets
POST /api/ciphers                     → Créer un secret (type: 1 = Login)
PUT  /api/ciphers/{id}                → Mettre à jour un secret
DELETE /api/ciphers/{id}              → Supprimer un secret (irréversible)
GET  /api/sync                        → Export complet du coffre (pour backup/audit)
GET  /alive                           → Health check HTTP
GET  /api/config                      → Config serveur
```

Headers : `Authorization: Bearer <access_token>`, `Content-Type: application/json`.

### Contenu actuel du coffre stack_hma

| Catégorie | Entrées |
|-----------|---------|
| **Infra VPS** | VPS Hostinger (root), Coolify Admin, PostgreSQL |
| **Apps HMA** | n8n, Odoo, Apache Superset, Metabase, NocoDB, Uptime Kuma |
| **APIs** | Pennylane (ETPA, HMA, STIVMAT, STA, Sandbox), OpenAI, Claude Code HMA |
| **Bases de données** | Odoo PostgreSQL, n8n PostgreSQL, PostgreSQL standalone, Supabase Cloud (x2) |
| **Vecteur** | Qdrant HMA, Qdrant Source |
| **Comptes** | GitHub, Gmail HMA, auth.hostinger.com, Vaultwarden Admin HMA |

### Comportement automatique de Claude Code

- **Création de service** : proposer `vw-secret.sh set` pour enregistrer les credentials
- **Consultation de secret** : utiliser `vw-secret.sh get` plutôt que chercher dans le code ou les `.env`
- **Modification d'infra** : exécuter `vw-healthcheck.sh` pour vérifier que Vaultwarden est opérationnel
- **Après rotation de secret** : proposer `vw-backup.sh`
- **Ne jamais afficher un password en clair** dans les réponses — utiliser `***` si besoin de référencer un secret

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
- **Constitution** : `.specify/memory/constitution.md` — document d'autorité maximale pour les décisions architecturales. Les principes `(NON-NEGOTIABLE)` ne peuvent être modifiés que par le décideur projet
- Artefacts de la feature en cours : `specs/001-agent-ia-comptable/` (spec, plan, tasks, research, data-model, contracts)

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

### Rapports d'analyse — `hma_holding/`

Les résultats d'analyse comptable par structure sont stockés en Markdown :
```
hma_holding/
├── ETPA/      ← analyse-complete-2025-12.md (1er exercice, en cours)
├── HMA/
├── STA/
└── STIVMAT/
```
Nommage : `analyse-<type>-<YYYY>-<MM>.md` — générés par le skill `/pennylane-analyse`

---

## Référentiel formules comptables

`docs/compta_analytique.md` — spécification technique exhaustive (~2 600 lignes) pour l'implémentation des vues SQL :
- **SIG** : 9 soldes + CAF (méthodes additive et soustractive), comptes PCG exacts, formules SQL
- **Compte de Résultat** : produits/charges par rubrique
- **Bilan comptable** : actif (brut-amort=net), passif
- **Bilan fonctionnel** : emplois/ressources stables, FRNG, BFR, TN
- **CRD (Compte de Résultat Différentiel)** : CA → MCV → Rés. exploitation → RCAI → Rés. net → CAF + seuil de rentabilité, point mort, marge de sécurité + pourcentages relatifs (% du CA)
- **25+ ratios financiers** : liquidité, solvabilité, rentabilité, rotation, sectoriels
- **Consolidation groupe** : agrégation, élimination intra-groupe

**Toujours consulter ce référentiel** avant de coder ou modifier une vue matérialisée.

---

## Superset — Dashboards

Instance : `superset.hma.business` — credentials dans Vaultwarden (`Apache Superset`).
Conteneur : `superset-mjhp747l60b4lzhkc1gfkari` — config FR dans `/app/superset_home/superset_config.py`.
Skill : `/superset-dashboard` — création/modification/diagnostic de dashboards via l'API REST.

### Feature flags Superset

Config dans `/app/superset_home/superset_config.py` :
```python
FEATURE_FLAGS = {
    "DRILL_TO_DETAIL": True,    # Clic droit → voir les écritures brutes
    "DRILL_BY": True,           # Clic droit → drill par dimension
    "DASHBOARD_CROSS_FILTERS": True,  # Cross-filter entre charts
}
```

### Dashboards déployés

| Dashboard | URL | Charts | Filtres |
|---|---|---|---|
| **Q1 2026 - Performance** | `/superset/dashboard/q1-2026/` | 9 (6 KPI + graphiques + CRD) | Entreprise, Trimestre, Mois |
| **SIG + CRD — Analyse détaillée** | `/superset/dashboard/sig-crd/` | 7 (résumé + détail cross-filter) | Entreprise, Trimestre, Mois |
| **Bilan et structure financière** | `/superset/dashboard/bilan/` | 3 | Entreprise |
| **Grand Livre et Balance** | `/superset/dashboard/grand-livre/` | 8 (résumé + détail cross-filter) | Entreprise |
| **CRD — Drilldown** | `/superset/dashboard/crd-drilldown/` | 9 (KPI + barres + courbe + drilldown) | Entreprise, Trimestre, Mois |
| **CRD (ancien)** | `/superset/dashboard/crd/` | 16 | Entreprise, Trimestre |

**Note** : les filtres Superset utilisent `adhoc_filters` hardcodés (`annee=2026`) car les native filters ne s'appliquent pas aux charts créés par API. Le filtre Année est dans la sidebar mais décoratif.

### API Superset — Points clés

- **Auth** : session cookie + CSRF token (le JWT seul échoue pour PUT/POST)
- **Charts créés par API** : nécessitent un `query_context` pour s'afficher sur le dashboard — soit le passer dans le payload, soit ouvrir le chart dans Explore → Update → Save
- **viz_type validés** : `echarts_timeseries_bar`, `echarts_timeseries_line`, `echarts_pie`, `big_number_total`, `table`, `pivot_table_v2` — ne PAS utiliser `echarts_bar`, `dist_bar`, `bar` (non enregistrés)
- **Format euros** : `y_axis_format: ",.0f"` pour KPI, `valueFormat: ",.2f"` pour pivots

---

## HMAnalytics — hma-marimo (gestion.hma.business)

Notebook Marimo réactif servant de **dashboard comptable principal**. 6 onglets : Vue d'ensemble · CRD Réel · Bilan Fonctionnel · Budget CRD · Budget Trésorerie · SQL libre.

**Stack** : Marimo `>=0.13.0,<0.24` + Altair `>=5.4.1,<6` (pin obligatoire, voir bug plus bas) + pandas + psycopg2-binary.
**Images** : `hma-marimo-hma-marimo:latest`, déployé sur VPS 187.124.150.82.
**URL** : `https://gestion.hma.business` (Traefik + Let's Encrypt, network `coolify`).
**Container** : `hma-marimo`, env `HMA_DB_URL` injecté via docker-compose.
**Source** : `hma-marimo/app.py` + `hma-marimo/custom.css` (theme pro frontend ~500 lignes).

### Règles Marimo non-négociables

1. **Jamais `.value` dans la cellule qui crée l'UI** — sépare création et lecture en 2 cellules distinctes (sinon `RuntimeError`).
2. **Variables privées** préfixées par `_` (ex: `_df`, `_tmp`) pour éviter `MultipleDefinitionError` entre cellules.
3. **Helpers partagés** via `@app.function` (`db_query`, `fmt`, `delta_pct`, `bf_fetch`, `fetch_kpi_by_cat`) — globaux à toutes les cellules.
4. **État partagé** via `mo.state()` — utilisé pour le bouton Live + multiselects bidirectionnels.
5. **Charts Altair rendus directement** (pas de `mo.ui.altair_chart()` wrapper) — marimo 0.23.1 + Altair 5.5 ont un bug dans `_get_binned_fields` qui throw `AttributeError: 'list' object has no attribute 'get'` sur certains encodings. Contournement : passer le chart Altair natif à `mo.vstack` ou `mo.hstack` directement.
6. **`db_query()` doit gérer INSERT/UPDATE sans RETURNING** : tester `cur.description is None` avant `cur.fetchall()` (sinon `ProgrammingError: no results to fetch`).

### Structure des cellules (ordre de définition)

```
1. with app.setup:                        → imports + constants (TZ_GUYANE, JOURS_FR, GROUPE_LABEL)
2. @app.function helpers                  → db_query, fmt, delta_pct, fetch_kpi_by_cat, bf_fetch, budget_*
3. Options (entité_map, annee_list)       → chargées au démarrage
4. mo.state pour get_years/set_years      → cellule dédiée
5. Création multiselects                  → value=get_state(), on_change=set_state (bidirectionnel)
6. Bouton Live (cellule séparée)          → on_click → set_years/set_months à aujourd'hui
7. Sidebar assembly                       → mo.sidebar([...]) + logo + footer
8. Parser filtres → variables             → annees_sel, mois_sel, entite_ids, annee, entite_id, is_groupe
9. Cellules data par page                 → kpi_data, crd_n/p, bf_n/p, budget_calc, treso_calc
10. Cellules rendu par page               → overview_tab, crd_tab, bf_tab, budget_tab, treso_tab, sql_tab (widgets)
11. mo.ui.tabs({...})                     → assemblage final des 6 onglets
```

### Filtres globaux (variables partagées)

| Variable | Type | Description |
|---|---|---|
| `entite_ids` | `list[str]` | UUIDs des structures sélectionnées. Vide = Groupe consolidé |
| `entite_id` | `str \| None` | Premier UUID de la liste (fallback pour pages mono-entité : Budget) |
| `is_groupe` | `bool` | True si aucune structure sélectionnée |
| `annees_sel` | `list[int]` | Années sélectionnées (multi). Défaut = année courante |
| `annee` | `int` | Première année (max) pour pages mono-année |
| `annee_prev` | `int` | `annee - 1` pour delta vs N-1 |
| `mois_sel` | `list[int]` | Mois sélectionnés 1-12. Vide = tous |

Les requêtes SQL utilisent `entite_id = ANY(%s::uuid[])`, `annee = ANY(%s)`, `mois = ANY(%s)` pour supporter le multi-select.

### Deploy workflow (hot-reload sans rebuild)

```bash
# 1. Edit local app.py ou custom.css
# 2. Syntax check (obligatoire)
python -c "import ast; ast.parse(open('hma-marimo/app.py',encoding='utf-8').read()); print('OK')"
# 3. Push vers build dir sur VPS
scp hma-marimo/app.py hma-marimo/custom.css root@187.124.150.82:/tmp/hma-marimo-build/hma-marimo/
# 4. Hot-copy dans le container (pas de rebuild)
ssh root@187.124.150.82 "docker cp /tmp/hma-marimo-build/hma-marimo/app.py hma-marimo:/app/app.py && docker cp /tmp/hma-marimo-build/hma-marimo/custom.css hma-marimo:/app/custom.css && docker restart hma-marimo"
# 5. Test Playwright avec ?v=N (bypass cache browser)
# URL : https://gestion.hma.business/?v=42
```

### Commandes de debug

```bash
# Logs live
ssh root@187.124.150.82 "docker logs hma-marimo --follow"

# Trouver la dernière erreur Python
ssh root@187.124.150.82 "docker logs hma-marimo --since 2m 2>&1 | grep -B2 -A5 'Traceback\|Error' | tail -30"

# Vérifier app_title / version déployée
ssh root@187.124.150.82 "docker exec hma-marimo grep app_title /app/app.py"

# Inspecter Shadow DOM via Playwright (marimo rend les tabs en Web Components)
# querySelectorAll('[role=tablist]') retourne 0 → il faut walker les shadowRoot
```

### CSS (hma-marimo/custom.css)

Thème pro frontend, ~500 lignes. Points critiques :
- Sidebar marimo forcée à **288px fixe** via `--hma-sidebar-width` + `width !important` sur `aside.app-sidebar` (sinon marimo a une classe `auto-collapse-nav` qui change dynamiquement la largeur)
- Top bar `[role="tablist"]` en `position: fixed; top: 12px` aligné sur `calc(var(--hma-sidebar-width) + 1rem)`
- Bouton Download marimo caché (`div.fixed.right-0.top-0.z-50 { display: none }`)
- Bouton collapse sidebar caché (`aside.app-sidebar > div.absolute[z-20] { display: none }`)
- Wrapper marimo `div[class*="xl:px-24"]` forcé à `padding: 1.5rem` (sinon gap de 96px sur la droite)
- Charts Altair/Vega : `height: 380px` fixe + `overflow: hidden` pour uniformiser les 3 cards de la Vue d'ensemble

### Skills dédiés

- `.claude/commands/marimo-create.md` — template + règles
- `.claude/commands/marimo-debug.md` — 10 erreurs Marimo courantes + fix
- `.claude/commands/marimo-deploy.md` — workflow Docker/Coolify

Référentiel exhaustif : `docs/marimo-reference.md` (1 709 lignes), `docs/marimo-templates.md` (1 929 lignes).

---

## Vues SQL YTD vs Solde à date (convention fondamentale)

Règle comptable française : **comptes de flux** (classes 6-7) = YTD cumulatif depuis le 1er janvier, **comptes de stock** (classes 1-5) = solde à date incluant les à-nouveaux. Ne jamais mélanger.

| Famille | Granularité | Usage | À-nouveaux |
|---|---|---|---|
| `v_resultat_journalier` / `_mensuel` / `_trimestriel` / `_annuel` | Mouvements **isolés** par période (non cumulatifs) | "CA de mars", "Charges du T2" | Exclus |
| `v_ytd_journalier`, `v_ytd_cumule` (mensuel) | Cumul **vrai** depuis 1er janvier + `ca_projete_annuel`, `taux_marge_ytd_pct` | Dashboards YTD + projection | Exclus |
| `v_solde_a_date`, `v_solde_a_date_journalier` | Solde cumulatif depuis ouverture compte | Bilan, trésorerie, encours clients/fournisseurs | **Inclus** |

**Deprecated** (garder pour backward compat, ne pas utiliser pour du nouveau code) :
- `v_ytd_mensuel/trimestriel/annuel` (mal nommés : ce sont des agrégations par période, **pas** des cumuls YTD — préférer `v_resultat_*`)

**Erreur classique** : utiliser `v_ytd_mensuel` en croyant avoir du cumul YTD. Utiliser `v_ytd_cumule` à la place.

Fichiers SQL :
- `sql/03-views/015-vues-cumul.sql` — `v_resultat_mensuel`, `v_ytd_cumule`
- `sql/03-views/016-vue-cumul-journalier.sql` — `v_resultat_journalier`, `v_ytd_journalier`
- `sql/03-views/017-vues-resultat-trim-annuel.sql` — `v_resultat_trimestriel`, `v_resultat_annuel`
- `sql/03-views/018-vue-solde-a-date.sql` — `v_solde_a_date`, `v_solde_a_date_journalier`

---

## Projet en cours : Agent IA comptable

Voir `docs/presentation-agent-ia-hma.md` pour la présentation complète.
Artefacts Spec-Kit dans `specs/001-agent-ia-comptable/` (spec, plan, tasks, research, data-model, contracts).

### Découpage en chantiers

| Chantier | Périmètre | Statut |
|---|---|---|
| **A** | Socle données : FEC, Balance, Bilan, CR, SIG (PostgreSQL HMA + Qdrant `kb_pcg_analytique`) | 🚧 En cours |
| **B** | Dashboards Superset (consomment les vues du chantier A) | 🚧 En cours |
| **C** | Budget multi-scénarios + cascade d'overrides + DSO/DPO/DIO trésorerie | 🚧 En cours (socle SQL déployé + onglets Marimo Budget CRD + Budget Trésorerie) |
| **D** | Système multi-agents (5 agents n8n) | ⬜ |
| **E** | Mémoire agents (Qdrant `agent_mem_*` + feedback) | ⬜ |

### Chantier C — Système budget (déployé avril 2026)

**Tables** (`sql/01-schema/011-budget.sql`) — cascade d'overrides du plus général au plus spécifique :
```
budget_scenario                       (multi-hypothèses par entité/année, brouillon/validé)
  └─ budget_regle_globale             (taux par défaut : revenus +10%, charges +5%)
     └─ budget_override_categorie     (override par crd_categorie)
        └─ budget_override_compte     (taux OU valeur fixe annuelle — plus spécifique)
  └─ budget_tresorerie_parametres     (DSO/DPO/DIO + mode montant_direct/hybride)
```

**Vues** :
- `v_budget_crd` (`sql/03-views/019-v-budget-crd.sql`) : applique la cascade `compte > catégorie > global` sur le réel de l'année de référence. Colonnes : `montant_reel`, `taux_effectif`, `source_override`, `montant_budget`, `ecart_budget`.
- `v_budget_tresorerie` (`sql/03-views/020-v-budget-tresorerie.sql`) : projection BFR et TN en 3 modes :
  - `taux_jours` : BFR = (CA_HT × 1.20 / 365 × DSO) + (Achats_HT / 365 × DIO) − (Achats_HT × 1.20 / 365 × DPO)
  - `montant_direct` : BFR cible et TN cible saisis directement en euros
  - `hybride` : DSO/DPO/DIO + override montant si renseigné
  TN projetée = FRNG_réel + Résultat_budget − BFR_budget

**Consommation** : HMAnalytics → onglets Budget CRD et Budget Trésorerie, sliders réactifs avec bouton Save qui UPDATE les tables.

**Règle critique** : le budget est **mono-entité**. Si "Groupe consolidé" est sélectionné dans la sidebar, les pages Budget affichent un warning et demandent à l'utilisateur de choisir une structure spécifique.

**Scenario par défaut** : HMAnalytics crée automatiquement un scenario "Central {annee}" par entité × année à la première visite via `budget_get_or_create_scenario()`.

### Architecture multi-agents (5 agents, orchestrés par n8n)

```
Utilisateur → Directeur de Mission → Expert(s) → Réviseur Qualité → Synthèse → Utilisateur
```

| Agent | Rôle | Sources |
|---|---|---|
| Directeur de Mission | Route, délègue, synthétise | Appel des 4 autres agents |
| Expert-Comptable Senior | Chiffres + Social (paie, CC, LODEOM social) | Pennylane API, PostgreSQL HMA SQL, Qdrant KB |
| Juriste Senior | Droit fiscal, sociétés, contrats, travail | Qdrant KB (manuels, réglementation) |
| Analyste Financier Senior | SIG, ratios, simulations, recommandations | PostgreSQL HMA vues matérialisées, Pennylane API |
| Réviseur Qualité | Vérifie calculs, croise sources, score confiance | PostgreSQL HMA SQL, Qdrant KB, Pennylane API |

**Mémoire structurée** (3 niveaux par agent) :
- **Long terme** (Qdrant) : outputs passés indexés par similarité — 4 collections `agent_mem_*`
- **Court terme** (PostgreSQL HMA `agent_session`) : contexte session partagé entre agents
- **Procédurale** (PostgreSQL HMA `agent_feedback`) : scoring + few-shot injection

**Données (PostgreSQL HMA + Qdrant)** :
- **dim_calendrier** (PostgreSQL) : table de dimension temporelle (2020-2030), 4 018 jours. Colonnes : `date_jour`, `annee`, `trimestre`, `mois`, `mois_label`, `mois_nom`, `semaine`, `jour_semaine`, `debut_mois`, `fin_mois`
- **pcg_analytique** (PostgreSQL) : mapping des 1 379 comptes PCG (SIG, CR, Bilan, BF, V/F, **CRD**) — source de vérité : `scripts/generate-pcg-seed.py` + `sql/01-schema/009-pcg-crd-mapping.sql`
  - Colonnes CRD : `crd_ordre` (1-9), `crd_categorie` (Chiffre d'affaires, Charges variables, etc.), `crd_rubrique` (sous-rubrique), `crd_signe` (+1/-1)
  - Le CRD s'arrête à l'ordre 6 (Résultat net). Ordres 7-9 = composantes CAF (hors tableau CRD)
- **pennylane_balance** (PostgreSQL) : snapshot trial_balance Pennylane pour contrôle de cohérence GL vs Pennylane
- **kb_pcg_analytique** (Qdrant) : même mapping enrichi en texte français pour RAG — dérivé de PostgreSQL, embeddings OpenAI `text-embedding-3-small`
- **fec_ecriture** (PostgreSQL) : 25 627 écritures comptables normalisées FEC (Art. A.47 A-1 LPF)
- **Vues matérialisées** (PostgreSQL) : mv_balance_generale, mv_sig, mv_compte_resultat, mv_bilan, mv_bilan_fonctionnel, mv_resultat_differentiel (CRD complet avec CAF + %)
- **Vues enrichies** (PostgreSQL) : v_sig, v_bilan, v_compte_resultat, v_bilan_fonctionnel, v_balance_generale, v_resultat_differentiel (ajoutent `entite_nom` + `exercice_label`), v_ytd_mensuel/trimestriel/annuel, v_sig_drilldown, v_crd_drilldown (avec `annee`, `trimestre`, `mois_label`)
- **Vues de base comptables** (PostgreSQL) : v_grand_livre (écritures + solde progressif), v_journal (totaux par journal/mois), v_balance_auxiliaire (solde par tiers + non lettré), v_balance_agee (créances/dettes par tranche d'ancienneté)
- **KB existantes** (Qdrant) : kb_manuels (18 132 pts), kb_reglementation (11 pts), kb_conventions (6 pts), kb_pcg_analytique (1 372 pts)
