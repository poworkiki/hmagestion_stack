# Implementation Plan: Agent IA Comptable — Chantier A (Socle de données)

**Branch**: `001-agent-ia-comptable` | **Date**: 2026-04-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-agent-ia-comptable/spec.md`
**Périmètre**: Chantier A uniquement — FEC, Grand Livre, Balance, Bilan, CR, SIG

## Summary

Construire le socle de données financières : synchroniser les écritures comptables des 4 structures depuis Pennylane vers Supabase (format FEC normalisé), mapper les 1 412 comptes PCG avec catégories analytiques, et produire 6 vues matérialisées (Balance générale, Bilan, Bilan fonctionnel, Compte de résultat, Résultat différentiel, SIG) + 1 vue de contrôle de cohérence.

## Technical Context

**Language/Version**: SQL (PostgreSQL 15+ via Supabase), JavaScript (n8n Code nodes)
**Primary Dependencies**: Supabase (self-hosted), n8n, Pennylane API v2
**Storage**: PostgreSQL (Supabase) — ~200k lignes d'écritures FEC estimées
**Testing**: Requêtes SQL de validation (v_controles_coherence), tests manuels via Metabase
**Target Platform**: VPS Hostinger (Ubuntu 24.04), conteneurs Docker via Coolify
**Project Type**: Pipeline ETL + schéma analytique (pas de code applicatif)
**Performance Goals**: Vues matérialisées rafraîchies en < 60 secondes, sync Pennylane < 5 minutes par structure
**Constraints**: Tokens API Pennylane en lecture seule, secrets dans Vaultwarden uniquement, RLS Supabase pour isolation multi-entité
**Scale/Scope**: 4 entités, ~200k écritures, 1 412 comptes PCG, 7 vues matérialisées

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v1.0.0 ratifiée le 2026-04-02. Vérification des 5 principes :

- ✅ **I. Secrets-First** : tokens Pennylane dans Vaultwarden, credentials n8n par référence, `.env` gitignored, aucun secret dans les fichiers SQL ou exports n8n
- ✅ **II. SQL-Only Data Layer** : 100% SQL + n8n, pas de code applicatif, vues matérialisées comme seule interface de lecture
- ✅ **III. Référentiel-Driven** : toutes les vues matérialisées MUST être conformes à `docs/compta_analytique.md`. Le mapping PCG (`scripts/generate-pcg-seed.py`) est la source de vérité unique. Une tâche de validation croisée seed ↔ référentiel est requise avant déploiement.
- ⏸️ **IV. 5 Agents Non-Négociable** : hors périmètre Chantier A (agents = Chantier D)
- ✅ **V. French-Only** : noms de tables, colonnes, commentaires SQL en français ou notation technique standard

## Project Structure

### Documentation (this feature)

```text
specs/001-agent-ia-comptable/
├── plan.md              # Ce fichier
├── research.md          # Recherches techniques (Pennylane API, FEC, PCG)
├── data-model.md        # Modèle de données Supabase complet
├── contracts/
│   └── pennylane-api.md # Contrat API Pennylane (endpoints, formats)
└── tasks.md             # Tâches (généré par /speckit.tasks)
```

### Source Code (repository root)

```text
sql/
├── 01-schema/
│   ├── 001-entite.sql                   # Table entite (4 structures)
│   ├── 002-exercice.sql                 # Table exercice
│   ├── 003-pcg-analytique.sql           # Table pcg_analytique (structure)
│   ├── 004-compte-resolution.sql        # Table compte_resolution + resolve_compte()
│   ├── 005-fec-import.sql               # Table fec_import (traçabilité)
│   └── 006-fec-ecriture.sql             # Table fec_ecriture (18 colonnes FEC)
├── 02-data/
│   └── 001-pcg-analytique-seed.sql      # INSERT des 1 412 comptes PCG mappés
├── 03-views/
│   ├── 001-mv-balance-generale.sql      # Vue matérialisée balance
│   ├── 002-mv-bilan.sql                 # Vue matérialisée bilan
│   ├── 003-mv-bilan-fonctionnel.sql     # Vue matérialisée bilan fonctionnel
│   ├── 004-mv-compte-resultat.sql       # Vue matérialisée CR
│   ├── 005-mv-resultat-differentiel.sql # Vue matérialisée CR différentiel
│   ├── 006-mv-sig.sql                   # Vue matérialisée SIG (9 soldes + CAF)
│   └── 007-v-controles-coherence.sql    # Vue de contrôle (D=C, clôture, doublons)
└── 04-functions/
    ├── resolve-compte.sql               # Fonction résolution préfixe → PCG
    └── refresh-views.sql                # Fonction refresh toutes les vues mat.

n8n/
└── workflow-sync-pennylane.json         # Export workflow n8n (4 structures)

scripts/
├── generate-pcg-seed.py                 # Pennylane → SQL seed (source de vérité mapping)
└── generate-pcg-qdrant.py               # Supabase → Qdrant kb_pcg_analytique (embeddings)
```

**Structure Decision**: Organisation par couches SQL numérotées (exécution séquentielle). Le dossier `n8n/` contient l'export JSON du workflow de synchronisation. Pas de code applicatif — tout est SQL + n8n.

## Phases d'implémentation

### Phase A1 — Tables de référence

| Étape | Livrable | Dépend de |
|---|---|---|
| Créer `entite` | 4 structures avec activité et profil | — |
| Créer `exercice` | Exercices comptables par entité | entite |
| Créer `pcg_analytique` (structure) | Table vide avec colonnes SIG/CR/Bilan/BF/V-F | — |
| Charger 1 412 comptes PCG | Seed complet avec mapping analytique | pcg_analytique |
| Charger 1 412 comptes dans Qdrant `kb_pcg_analytique` | Texte enrichi + embeddings OpenAI | pcg_analytique (Supabase) |
| Créer `compte_resolution` + `resolve_compte()` | Résolution préfixe FEC → numéro PCG | pcg_analytique |

### Phase A2 — Tables FEC et import

| Étape | Livrable | Dépend de |
|---|---|---|
| Créer `fec_import` | Traçabilité des imports (hash, date, statut) | entite, exercice |
| Créer `fec_ecriture` | 18 colonnes FEC + champs calculés + hash MD5 unique | entite, exercice, pcg_analytique |

### Phase A3 — Workflow sync Pennylane

| Étape | Livrable | Dépend de |
|---|---|---|
| Workflow n8n staging | Table temporaire, récupération `/ledger_entries` | fec_ecriture |
| Workflow n8n upsert | UPSERT idempotent staging → fec_ecriture (INSERT ON CONFLICT DO NOTHING sur hash_md5) | staging |
| Workflow n8n refresh | REFRESH CONCURRENTLY toutes les vues mat. | upsert |
| Boucle 4 structures | Paramétrage tokens Vaultwarden par structure | upsert |

### Phase A4 — Vues matérialisées

| Étape | Livrable | Dépend de |
|---|---|---|
| `mv_balance_generale` | Soldes par compte, entité, mois | fec_ecriture, pcg_analytique |
| `mv_bilan` | Actif/Passif (brut, amort, net) | mv_balance_generale |
| `mv_bilan_fonctionnel` | FRNG, BFR exploit/hors exploit, TN | mv_bilan |
| `mv_compte_resultat` | CR structuré (produits/charges par rubrique) | mv_balance_generale |
| `mv_resultat_differentiel` | MCV, taux MCV, seuil rentabilité, charges V/F | mv_compte_resultat |
| `mv_sig` | 9 soldes intermédiaires + CAF | mv_balance_generale |
| `v_controles_coherence` | Équilibre D=C, clôture N-1 = ouverture N, doublons | fec_ecriture |

### Phase A5 — Validation

| Étape | Livrable | Dépend de |
|---|---|---|
| Sync 3 cycles consécutifs sans doublons | Validation FR-018 | Phase A3 |
| Croiser SIG avec Pennylane `/trial_balance` | Validation FR-011 | Phase A4 |
| Vérifier D=C sur toutes les entités | Validation v_controles_coherence | Phase A4 |

## Complexity Tracking

Aucune violation de constitution à justifier.
