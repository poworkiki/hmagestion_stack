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

**Projets Coolify** : `hma-monitoring` (Uptime Kuma, Vaultwarden) · `hma-apps` (services métier) · `hma-agents` (HMAGENTS + Qdrant + PostgreSQL HMA). Tout nouveau service métier va dans `hma-apps`, tout ce qui touche aux agents IA va dans `hma-agents`.

**Bases de données** : chaque service applicatif a sa propre instance PostgreSQL dédiée. Base métier principale : **PostgreSQL HMA standalone** (`hma-db`) — remplace Supabase self-hosted. Instance Supabase Cloud (eu-west-3) en veille.

**Qdrant** : base vectorielle pour le RAG comptable. Exposé en HTTPS sur `qdrant.hma.business`. API key dans `.mcp.json` et Vaultwarden. Serveur MCP local (`mcp-qdrant-hma/server.py`) pour accès direct depuis Claude Code.

**Infrastructure multi-VPS** :
- VPS principal (187.124.150.82) : Coolify HMA, tous les services métier
- VPS secondaire (168.231.69.226) : anciens services en cours de migration

**Stack de visualisation / saisie** :
- **Superset** (`superset.hma.business`) : dashboards + SQL Lab (lecture seule). Driver `psycopg2-binary` installé via volume persistant (`PYTHONPATH=/app/superset_home/pip_packages`)
- **pgAdmin** (`pgadmin.hma.business`) : administration PostgreSQL
- **Appsmith** (`appsmith.hma.business`) : saisie, formulaires, interfaces métier (écriture)

Services supprimés (avril 2026) : Metabase (redondant avec Superset), Teable (redondant), Supabase self-hosted (remplacé par PostgreSQL standalone)

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

**⚠️ Rate limit** : Vaultwarden limite les logins (~2 par minute). Pour récupérer plusieurs secrets, utiliser **un seul script Python** qui fait 1 login puis fetch tous les ciphers via `VwSession` (voir `scripts/vw-crypto.py` classe `VwSession`). Ne PAS appeler `vw-secret.sh get` en boucle rapide.

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

**⚠️ `trial_balance` vs `ledger_entries`** : `trial_balance` ne retourne que les écritures **validées** — peut renvoyer 0 pour un exercice non clôturé. Les données FEC en base proviennent de `ledger_entries` (brouillons inclus). Pour les audits, préférer les vues SQL (`v_sig`, `v_bilan`, etc.) qui contiennent toutes les écritures synchronisées.

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
# 1. Schéma (tables de référence + grand_livre)
psql $HMA_DB_URL -f sql/01-schema/001-entite.sql
psql $HMA_DB_URL -f sql/01-schema/002-exercice.sql
psql $HMA_DB_URL -f sql/01-schema/003-pcg-analytique.sql
psql $HMA_DB_URL -f sql/01-schema/005-fec-import.sql
psql $HMA_DB_URL -f sql/01-schema/007-sync-metadata.sql
psql $HMA_DB_URL -f sql/01-schema/008-dim-calendrier.sql
psql $HMA_DB_URL -f sql/01-schema/009-pcg-crd-mapping.sql
psql $HMA_DB_URL -f sql/01-schema/010-pennylane-balance.sql
psql $HMA_DB_URL -f sql/01-schema/011-grand-livre.sql
psql $HMA_DB_URL -f sql/01-schema/012-balance-generale.sql

# 2. Données de référence
psql $HMA_DB_URL -f sql/02-data/001-pcg-analytique-seed.sql

# 3. Fonctions
psql $HMA_DB_URL -f sql/04-functions/refresh-views.sql
psql $HMA_DB_URL -f sql/04-functions/refresh-views-conditional.sql

# 4. Vues (toutes depuis grand_livre)
psql $HMA_DB_URL -f sql/03-views/007-v-controles-coherence.sql
psql $HMA_DB_URL -f sql/03-views/009-vues-base-comptables.sql
psql $HMA_DB_URL -f sql/03-views/011-vues-depuis-grand-livre.sql
psql $HMA_DB_URL -f sql/03-views/012-vues-display-gl-bg.sql
psql $HMA_DB_URL -f sql/03-views/013-vues-balance-tiers.sql
psql $HMA_DB_URL -f sql/03-views/014-vue-fec-export.sql
```

**Architecture (avril 2026)** : `grand_livre` est la **source unique** (table dénormalisée, données Pennylane enrichies PCG + calendrier). Seule `balance_generale` est matérialisée. Toutes les autres vues sont simples. `fec_ecriture` a été supprimée — le FEC légal est généré à la demande via `v_fec_export`.

```
grand_livre (TABLE dénormalisée, source unique)
    → balance_generale (MV, agrégation mensuelle)
    → v_grand_livre, v_balance, v_bg_display, v_bg_mensuelle
    → v_sig, v_sig_drilldown, v_compte_resultat
    → v_crd, v_crd_drilldown
    → v_bilan, v_bilan_fonctionnel
    → v_ytd_mensuel/trimestriel/annuel
    → v_balance_clients, v_balance_fournisseurs
    → v_fec_export (FEC légal Art. A.47 A-1 LPF)
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
- `v_controle_balance` : compare GL (grand_livre) vs Pennylane (pennylane_balance) par compte
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

## Projet en cours : Agent IA comptable

Voir `docs/presentation-agent-ia-hma.md` pour la présentation complète.
Artefacts Spec-Kit dans `specs/001-agent-ia-comptable/` (spec, plan, tasks, research, data-model, contracts).

### Découpage en chantiers

| Chantier | Périmètre | Statut |
|---|---|---|
| **A** | Socle données : FEC, Balance, Bilan, CR, SIG (PostgreSQL HMA + Qdrant `kb_pcg_analytique`) | ✅ Terminé |
| **B** | Dashboards Superset (consomment les vues du chantier A) | 🚧 En cours |
| **C** | Budget + saisie Appsmith + tables override V/F | ⬜ |
| **D** | Système multi-agents HMAGENTS (5 agents CrewAI) | ✅ Déployé |
| **E** | Mémoire agents (mem0 + Qdrant `agent_mem_*` + feedback) | 🚧 Scaffoldé |

### HMAGENTS — Système multi-agents (`agents.hma.business`)

**Stack** : CrewAI (orchestration) + LlamaIndex (RAG + SQL) + mem0 (mémoire) + GPT-4o (LLM) + FastAPI (API)
**Config détaillée** : `specs/001-agent-ia-comptable/hmagents-stack.md`
**Code** : `hmagents/` (Dockerfile, docker-compose, app/)

```
POST https://agents.hma.business/ask    → Question aux agents
GET  https://agents.hma.business/health → Health check
```

```bash
# Test rapide
curl -sk -X POST https://agents.hma.business/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Quel est le CA de STIVMAT ?", "entite":"STIVMAT", "exercice":"2025"}'
```

**5 agents** (Process.hierarchical, Directeur = manager_agent) :

| Agent | Rôle | Outils |
|---|---|---|
| Directeur de Mission | Route, délègue, synthétise | Délégation CrewAI |
| Expert-Comptable Senior | Chiffres + Social + LODEOM | SQL (7 vues) + Pennylane API + KB Qdrant + mem0 |
| Juriste Senior | Droit fiscal, sociétés, contrats | KB Qdrant (manuels, réglementation, conventions) + mem0 |
| Analyste Financier Senior | SIG, ratios, simulations | SQL (vues) + Pennylane API + KB Qdrant + mem0 |
| Réviseur Qualité | Vérifie calculs, score confiance | SQL + KB Qdrant + Pennylane API + mem0 |

**Outils disponibles** (tous exception-safe, lazy init) :
- `kb_manuels`, `kb_reglementation`, `kb_conventions`, `kb_pcg_analytique` — RAG LlamaIndex → Qdrant
- `sql_balance`, `sql_sig`, `sql_bilan`, `sql_bilan_fonctionnel`, `sql_compte_resultat`, `sql_resultat_differentiel`, `sql_ecritures_fec` — NLSQLTableQueryEngine → PostgreSQL HMA
- `pennylane_trial_balance`, `pennylane_ledger_entries`, `pennylane_ledger_accounts` — API Pennylane directe
- `memoire_expert_comptable`, `memoire_juriste`, `memoire_analyste`, `memoire_reviseur` — mem0 → Qdrant

**Déploiement** : Coolify (projet `hma-agents`) depuis GitHub `001-agent-ia-comptable`. Env vars injectées via Coolify. Réseaux Docker : `coolify` (partagé avec Qdrant + PostgreSQL).

**Redéploiement manuel** (si nécessaire) :
```bash
ssh root@187.124.150.82 "cd /tmp/hmagents-build/hmagents && git pull && docker build -t hmagents:latest . && docker stop hmagents && docker rm hmagents && docker run -d --name hmagents --restart unless-stopped --env-file .env --network coolify -p 8100:8000 hmagents:latest"
```

**Mémoire structurée** (3 niveaux par agent) :
- **Long terme** (mem0 → Qdrant) : outputs passés indexés par similarité — 4 collections `agent_mem_*`
- **Court terme** (PostgreSQL HMA `agent_session`) : contexte session partagé entre agents — À implémenter
- **Procédurale** (PostgreSQL HMA `agent_feedback`) : scoring + few-shot injection — À implémenter

**Données (PostgreSQL HMA + Qdrant)** :
- **dim_calendrier** (PostgreSQL) : table de dimension temporelle (2020-2030), 4 018 jours. Colonnes : `date_jour`, `annee`, `trimestre`, `mois`, `mois_label`, `mois_nom`, `semaine`, `jour_semaine`, `debut_mois`, `fin_mois`
- **pcg_analytique** (PostgreSQL) : mapping des 1 379 comptes PCG (SIG, CR, Bilan, BF, V/F, **CRD**) — source de vérité : `scripts/generate-pcg-seed.py` + `sql/01-schema/009-pcg-crd-mapping.sql`
  - Colonnes CRD : `crd_ordre` (1-9), `crd_categorie` (Chiffre d'affaires, Charges variables, etc.), `crd_rubrique` (sous-rubrique), `crd_signe` (+1/-1)
  - Le CRD s'arrête à l'ordre 6 (Résultat net). Ordres 7-9 = composantes CAF (hors tableau CRD)
- **pennylane_balance** (PostgreSQL) : snapshot trial_balance Pennylane pour contrôle de cohérence GL vs Pennylane
- **kb_pcg_analytique** (Qdrant) : même mapping enrichi en texte français pour RAG — dérivé de PostgreSQL, embeddings OpenAI `text-embedding-3-small`
- **grand_livre** (PostgreSQL) : ~39 000 écritures comptables dénormalisées (source unique), enrichies PCG + calendrier
- **Vue matérialisée** (PostgreSQL) : `balance_generale` (agrégation mensuelle par compte). Toutes les autres vues sont simples
- **v_fec_export** (PostgreSQL) : FEC légal (Art. A.47 A-1 LPF) généré à la demande depuis `grand_livre`
- **Vues enrichies** (PostgreSQL) : v_sig, v_bilan, v_compte_resultat, v_bilan_fonctionnel, v_balance_generale, v_resultat_differentiel (ajoutent `entite_nom` + `exercice_label`), v_ytd_mensuel/trimestriel/annuel, v_sig_drilldown, v_crd_drilldown (avec `annee`, `trimestre`, `mois_label`)
- **Vues de base comptables** (PostgreSQL) : v_grand_livre (écritures + solde progressif), v_journal (totaux par journal/mois), v_balance_auxiliaire (solde par tiers + non lettré), v_balance_agee (créances/dettes par tranche d'ancienneté)
- **KB existantes** (Qdrant) : kb_manuels (18 132 pts), kb_reglementation (11 pts), kb_conventions (6 pts), kb_pcg_analytique (1 372 pts)
