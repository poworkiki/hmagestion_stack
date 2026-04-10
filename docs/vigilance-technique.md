# Points de vigilance technique — Stack HMA

**Dernière mise à jour** : 10 avril 2026
**Contexte** : leçons apprises lors de la session de refactoring du 10/04/2026

---

## 1. Synchronisation Pennylane → grand_livre

### Pipeline actuel

```
Pennylane API /ledger_entry_lines
    → sync-pennylane-gl.py (toolbox ou local)
        → UPSERT grand_livre (ON CONFLICT pennylane_line_id)
        → Réconciliation (DELETE lignes absentes de Pennylane)
        → REFRESH MATERIALIZED VIEW balance_generale
```

### Points de vigilance

| # | Risque | Ce qui s'est passé | Garde-fou en place |
|---|---|---|---|
| 1 | **Doublons si faux pennylane_line_id** | L'ancienne migration `fec_ecriture → grand_livre` générait des IDs fictifs (hash_md5 converti en bigint). Le sync avec les vrais IDs Pennylane créait des doublons. | Migration one-shot supprimée. Le pipeline est maintenant Pennylane → grand_livre direct. Ne jamais générer de faux `pennylane_line_id`. |
| 2 | **Lignes fantômes (sync normal sans --full)** | Le `ON CONFLICT DO UPDATE` met à jour et ajoute, mais ne supprime pas les lignes qui n'existent plus côté Pennylane. Le CA était gonflé (175k au lieu de 102k). | **Réconciliation automatique** : après l'upsert, table temp `_sync_ids` avec tous les IDs reçus, puis `DELETE WHERE pennylane_line_id NOT IN (SELECT pl_id FROM _sync_ids)`. |
| 3 | **Exercice mal affecté** | Toutes les écritures étaient rattachées à l'exercice 2025. STIVMAT avait 5 ans de données dans un seul exercice. | L'exercice est résolu **par ligne** en fonction de l'année de `ecriture_date`. Si l'exercice n'existe pas, il est créé automatiquement. |
| 4 | **Pennylane retourne des résultats variables** | Entre deux appels API identiques, Pennylane peut retourner un nombre de lignes différent (cache API, pagination). | Toujours utiliser `--full` pour un état garanti. Le sync normal avec réconciliation est fiable à 99%. |
| 5 | **Rate limit Pennylane (429)** | 5 requêtes/seconde max. Le script pagine ~245 pages pour STIVMAT. | Retry avec backoff exponentiel (30s × attempt). `time.sleep(0.25)` entre chaque page. |

### Commandes de référence

```bash
# Sync normal (réconciliation auto, idempotent)
docker exec toolbox python /app/scripts/sync-pennylane-gl.py

# Sync une structure
docker exec toolbox python /app/scripts/sync-pennylane-gl.py --structure STIVMAT

# Full sync (purge + re-import = état garanti)
docker exec toolbox python /app/scripts/sync-pennylane-gl.py --structure STIVMAT --full

# Via l'API toolbox (depuis n8n ou curl)
curl -X POST http://hma-toolbox:8000/sync
curl -X POST http://hma-toolbox:8000/sync/STIVMAT
curl -X POST http://hma-toolbox:8000/sync-full/STIVMAT
```

---

## 2. Architecture base de données

### Source unique : `grand_livre`

```
grand_livre (TABLE dénormalisée, 46 colonnes)
    → balance_generale (seule MV, agrégation mensuelle)
    → 31 vues simples (SIG, CRD, Bilan, BF, Balance clients/fournisseurs, FEC export, contrôles)
```

### Points de vigilance

| # | Risque | Détail |
|---|---|---|
| 1 | **`fec_ecriture` n'existe plus** | Supprimée le 10/04/2026. Le FEC légal est généré via `v_fec_export`. Ne jamais recréer cette table. |
| 2 | **`entite_code` doit être renseigné** | Colonne ajoutée le 10/04/2026. Le script de sync le renseigne automatiquement. Vérifier si des lignes ont `entite_code IS NULL` après un import. |
| 3 | **`is_a_nouveau` pour les classes 6-7** | Les vues SIG, CRD, YTD filtrent `WHERE NOT is_a_nouveau`. Les à-nouveaux ne doivent pas apparaître dans le P&L. La détection est basée sur `journal_code IN ('AN', 'OD-AN', 'RAN')`. |
| 4 | **`balance_generale` = seule MV** | Doit être rafraîchie après chaque sync. `REFRESH MATERIALIZED VIEW CONCURRENTLY balance_generale`. La fonction `refresh_all_views()` fait ça. |
| 5 | **Exercices : année civile** | Les 4 structures sont calées sur 01/01–31/12. L'exercice est déterminé par `annee` (extrait de `ecriture_date` via `dim_calendrier`). |
| 6 | **Pas de `TRUNCATE` ni `DROP` en production** | Toujours `--full` via le script (qui fait `DELETE WHERE entite_id = ...`) et non un `TRUNCATE` global. |

### Tables actives (8)

| Table | Rôle | Lignes |
|---|---|---|
| `grand_livre` | Source unique — écritures Pennylane enrichies | ~27 000 |
| `balance_generale` | MV agrégation mensuelle | ~800 |
| `pcg_analytique` | Plan comptable + mappings (SIG, CRD, Bilan, BF) | 1 379 |
| `dim_calendrier` | Dimension temps 2020-2030 | 4 018 |
| `entite` | 4 structures | 4 |
| `exercice` | Exercices comptables | 14 |
| `pennylane_balance` | Snapshot trial_balance (contrôle) | ~163 |
| `sync_metadata` | État sync par structure | 4 |

### Tables supprimées (ne pas recréer)

- `fec_ecriture` — remplacée par `grand_livre`
- `_staging_fec` — liée à `fec_ecriture`
- `compte_resolution` — liée à `resolve_compte()`
- Fonction `resolve_compte()` — plus nécessaire

---

## 3. Toolbox (hma-toolbox)

### Architecture

```
hma-toolbox (conteneur Docker)
├── FastAPI :8000 (API interne, appelée par n8n)
│   ├── /health      → Health check DB
│   ├── /sync        → Sync 4 structures
│   ├── /sync/{code} → Sync 1 structure
│   ├── /sync-full   → Full sync
│   ├── /refresh     → Refresh balance_generale
│   └── /status      → État sync_metadata
├── Streamlit :8501 (dashboard checks rapides)
│   └── 11 pages (Tableau de bord, BG, Bilan, BF, Clients, Fournisseurs, SIG, CRD, GL, Contrôles, SQL)
└── scripts/
    └── sync-pennylane-gl.py
```

### Points de vigilance

| # | Risque | Détail |
|---|---|---|
| 1 | **Image Docker à rebuilder** | L'image `hma-toolbox:latest` est buildée manuellement sur le VPS (`docker build`). Après chaque push, il faut rebuilder : `cd /tmp/hma-toolbox-build && git pull && cd hma-toolbox && docker build -t hma-toolbox:latest . && docker restart toolbox-*` |
| 2 | **Réseau Docker `coolify`** | La toolbox doit être sur le réseau `coolify` pour accéder à PostgreSQL et être accessible depuis n8n. Vérifier avec `docker inspect toolbox-* --format '{{json .NetworkSettings.Networks}}'`. |
| 3 | **Alias DNS `hma-toolbox`** | Configuré dans le compose Coolify (`networks.coolify.aliases`). Permet à n8n d'appeler `http://hma-toolbox:8000`. Si le conteneur perd l'alias, `docker network connect coolify toolbox-*`. |
| 4 | **Connexion DB idle** | Streamlit garde la connexion DB ouverte (`@st.cache_resource`). Si PostgreSQL redémarre, Streamlit crash. Solution : restart le conteneur toolbox. |
| 5 | **Branche Git** | Le compose Coolify clone la branche `002-dashboard-crd-custom`. Quand on merge sur `main`, il faudra mettre à jour le compose. |
| 6 | **Streamlit `autocommit`** | La connexion pg8000 n'est PAS en autocommit dans Streamlit (lecture seule, pas besoin). Mais si on ajoute des endpoints d'écriture dans l'API FastAPI, `conn.autocommit = True` est nécessaire. |

### Rebuild rapide

```bash
ssh root@187.124.150.82
cd /tmp/hma-toolbox-build && git pull
cd hma-toolbox && docker build -t hma-toolbox:latest .
docker restart toolbox-g4g3tmuip1f6g32sx0tgsxsh
```

---

## 4. Streamlit — Développement

### Conventions

| Règle | Détail |
|---|---|
| **Format montants** | Utiliser `fmt(valeur)` pour les KPIs Streamlit et `JS_FMT` pour les tooltips ECharts. Format : `1 000 000 €` (espace + €). |
| **Filtres globaux** | Les variables `where` et `where_no_an` sont construites en haut du fichier et s'appliquent à **toutes** les pages. Toute nouvelle page doit les utiliser. |
| **`where_no_an`** | = `where + " AND NOT is_a_nouveau"`. À utiliser pour les vues P&L (SIG, CRD, CA, résultat). NE PAS utiliser pour le bilan (les à-nouveaux sont nécessaires). |
| **Nouvelles pages** | Ajouter dans la liste `page = st.sidebar.radio(...)` et créer le bloc `elif page == "Nom":`. |
| **Requêtes SQL** | Toujours passer par `query()`, `query_dicts()`, `query_single()`. Jamais d'écriture (SELECT only). |
| **ECharts** | Utiliser `streamlit-echarts` avec `theme="streamlit"`. Tooltips : `"valueFormatter": JS_FMT`. |

### Pages avec filtre mois non applicable

| Page | Filtre mois | Raison |
|---|---|---|
| Balance Générale | Applicable via `balance_generale` (a la colonne `mois`) | OK |
| Bilan Comptable | Applicable mais peu pertinent (le bilan est une photo à une date) | Attention à l'interprétation |
| Bilan Fonctionnel | Idem bilan | Attention à l'interprétation |
| Contrôles qualité | Non applicable (les contrôles portent sur tout l'exercice) | Le filtre mois n'affecte pas les vues de contrôle |

---

## 5. Pennylane API

### Points de vigilance

| # | Risque | Détail |
|---|---|---|
| 1 | **`trial_balance` = écritures validées seulement** | Les écritures en brouillard ne sont PAS dans la trial_balance. Le GL contient tout (brouillons inclus via `/ledger_entry_lines`). Les écarts GL vs Pennylane sont normaux sur les exercices non clôturés. |
| 2 | **Pagination curseur obligatoire** | `limit` max 100 (sauf `/ledger_accounts` = 1000). Boucler tant que `has_more == true`. Ne jamais modifier `next_cursor` (opaque base64). |
| 3 | **Tokens lecture seule** | Les tokens Pennylane dans Vaultwarden sont en lecture seule. Pas de POST/PUT/DELETE sur l'API Pennylane. |
| 4 | **4 tokens = 4 sociétés distinctes** | Chaque token donne accès à une seule structure. Vérifier avec `/me` que le token correspond à la bonne structure. |
| 5 | **TVA en Guyane** | Pas de TVA (art. 294-1 CGI). Les comptes 445xx ne devraient pas apparaître pour les opérations locales. |

---

## 6. Infrastructure

### Points de vigilance

| # | Risque | Détail |
|---|---|---|
| 1 | **PostgreSQL pas exposé** | Port 5432 interne Docker uniquement. Accès via pgAdmin (`pgadmin.hma.business`) ou SSH + `docker exec`. |
| 2 | **`pg_stat_statements` installé** | Nécessite `shared_preload_libraries = 'pg_stat_statements'` (configuré le 10/04/2026). Si le conteneur est recréé sans ce paramètre, l'extension ne collectera pas. |
| 3 | **Backup PostgreSQL** | Pas de backup automatique PostgreSQL en place. Faire régulièrement : `docker exec h2dnymbgnulve0kko87nh856 pg_dump -U postgres -Fc postgres > backup.dump` |
| 4 | **Coolify compose ≠ fichier local** | Le compose de la toolbox est géré via l'API Coolify (base64 encodé). Le `docker-compose.yml` local dans `hma-toolbox/` n'est PAS utilisé par Coolify. |
| 5 | **Wildcard DNS** | `*.hma.business` résout vers le VPS. Tout nouveau sous-domaine fonctionne immédiatement. Traefik gère le SSL via Let's Encrypt. |
| 6 | **HMAGENTS déploiement manuel** | Image buildée sur le VPS (`docker build -t hmagents:latest`), pas via Coolify. Rebuild nécessaire après chaque modification de `hmagents/app/`. |

---

## 7. Checklist avant déploiement

Avant de déployer un changement en production, vérifier :

- [ ] Les fichiers SQL sont idempotents (`IF NOT EXISTS`, `CREATE OR REPLACE`)
- [ ] Les vues utilisent `grand_livre` (jamais `fec_ecriture`)
- [ ] Les filtres utilisent `entite_code` (pas `entite_nom` ni `entite_id`)
- [ ] Les vues P&L filtrent `NOT is_a_nouveau`
- [ ] Les montants utilisent `fmt()` / `JS_FMT` (format `1 000 000 €`)
- [ ] Le script de sync est poussé dans les DEUX fichiers (local + toolbox)
- [ ] L'image Docker est rebuildée après push (`docker build + restart`)
- [ ] La `balance_generale` est rafraîchie après modification de données
- [ ] Pas de secrets en clair (tokens dans Vaultwarden, connexion via env vars)
- [ ] Test Playwright sur `toolbox.hma.business` après déploiement
