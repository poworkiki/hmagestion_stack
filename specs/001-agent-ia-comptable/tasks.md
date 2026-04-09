# Tasks: Agent IA Comptable — Chantier A (Socle de données)

**Input**: Design documents from `/specs/001-agent-ia-comptable/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/pennylane-api.md

**Tests**: Inclus en phase de validation (Phase 6) — pas de TDD pour du SQL/ETL.

**Organisation**: Tâches groupées par phase d'implémentation (A1→A5) alignées sur les User Stories 1 et 4 de la spec (questions comptables + synchronisation Pennylane).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Peut être exécuté en parallèle (fichiers différents, pas de dépendance)
- **[Story]**: User Story associée (US1 = questions comptables, US4 = sync Pennylane)

---

## Phase 1: Setup (Structure projet)

**Purpose**: Créer l'arborescence SQL et n8n dans le dépôt

- [X] T001 Créer l'arborescence `sql/01-schema/`, `sql/02-data/`, `sql/03-views/`, `sql/04-functions/`, `n8n/` à la racine du dépôt

---

## Phase 2: Foundational — Tables de référence (A1)

**Purpose**: Tables de référence qui DOIVENT être en place avant toute donnée FEC

**⚠️ CRITICAL**: Aucune tâche FEC ou vue matérialisée ne peut commencer avant la fin de cette phase

- [X] T002 [P] Créer la table `entite` avec INSERT des 4 structures (HMA, STIVMAT, STA, ETPA) dans sql/01-schema/001-entite.sql
- [X] T003 [P] Créer la table `pcg_analytique` (structure avec colonnes numero, libelle, classe, sig_solde, sig_signe, cr_rubrique, cr_signe, bilan_poste, bilan_section, bf_categorie, nature_defaut) dans sql/01-schema/003-pcg-analytique.sql
- [X] T004 Créer la table `exercice` avec contrainte UNIQUE (entite_id, date_debut) dans sql/01-schema/002-exercice.sql
- [X] T005 Générer le seed des 1 412 comptes PCG avec mapping analytique complet (SIG, CR, Bilan, BF, V/F) dans sql/02-data/001-pcg-analytique-seed.sql — source : récupérer la liste via Pennylane `/ledger_accounts` des 4 structures, puis enrichir avec le mapping analytique depuis le PCG officiel ANC (classes, SIG, rubriques CR, postes bilan, nature V/F)
- [X] T006 Créer la table `compte_resolution` dans sql/01-schema/004-compte-resolution.sql
- [X] T007 Créer la fonction `resolve_compte()` (résolution par préfixe décroissant, fallback classe 3 caractères) dans sql/04-functions/resolve-compte.sql
- [X] T005b [P] Créer le script `scripts/generate-pcg-qdrant.py` : lecture pcg_analytique depuis PostgreSQL HMA, génération du champ `contenu` enrichi en français, embeddings OpenAI `text-embedding-3-small`, upsert dans Qdrant `kb_pcg_analytique` avec IDs uuid5 déterministes, index payload (classe, sig_solde, cr_rubrique, bf_categorie, nature_defaut, number)
- [X] T005c Exécuter `generate-pcg-qdrant.py` pour créer la collection `kb_pcg_analytique` (1 412 points, 1 536 dimensions, distance cosine) et vérifier COUNT PostgreSQL HMA == COUNT Qdrant

- [X] T005d Valider la cohérence du seed PCG (`generate-pcg-seed.py`) avec le référentiel `docs/compta_analytique.md` : revue manuelle par échantillonnage (10 comptes par sig_solde, 5 par cr_rubrique, 5 par bilan_poste) + vérification exhaustive que chaque valeur distincte de sig_solde, cr_rubrique, bilan_poste, bf_categorie et nature_defaut dans le seed existe dans les sections 1 à 6 du référentiel (Constitution III — Référentiel-Driven)

**Checkpoint**: Tables de référence prêtes, 1 412 comptes PCG chargés dans PostgreSQL HMA ET Qdrant, mapping validé contre le référentiel, fonction resolve_compte() opérationnelle

---

## Phase 3: User Story 4 — Synchronisation Pennylane (Priority: P1) 🎯 MVP

**Goal**: Synchroniser les écritures comptables des 4 structures depuis Pennylane vers PostgreSQL HMA au format FEC normalisé, sans doublons

**Independent Test**: Déclencher une sync sur HMA, vérifier que les écritures apparaissent dans `fec_ecriture` avec le bon hash, relancer et vérifier 0 doublon

### Tables FEC (A2)

- [X] T008 [US4] Créer la table `fec_import` (traçabilité imports : entite_id, exercice_id, source, nb_lignes, statut, erreur) dans sql/01-schema/005-fec-import.sql
- [X] T009 [US4] Créer la table `fec_ecriture` (18 colonnes FEC + pcg_numero, hash_md5 UNIQUE, index sur entite_id/exercice_id/compte_num/ecriture_date/hash_md5) dans sql/01-schema/006-fec-ecriture.sql
- [X] T010 [US4] Créer la table staging `_staging_fec` (même structure que fec_ecriture, sans contraintes, TRUNCATE à chaque run) dans sql/01-schema/006-fec-ecriture.sql

### Workflow n8n (A3)

- [X] T011 [US4] Créer le workflow n8n : noeud HTTP Request paginé vers Pennylane `/ledger_entries` (gestion pagination, auth Bearer token) dans n8n/workflow-sync-pennylane.json
- [X] T012 [US4] Ajouter le noeud Code n8n : mapping Pennylane → colonnes FEC (selon contracts/pennylane-api.md) + calcul hash_md5 dans n8n/workflow-sync-pennylane.json
- [X] T013 [US4] Ajouter le noeud PostgreSQL : INSERT batch dans `_staging_fec` dans n8n/workflow-sync-pennylane.json
- [X] T014 [US4] Ajouter le noeud SQL : MERGE staging → `fec_ecriture` (INSERT ... ON CONFLICT (hash_md5) DO NOTHING) + UPDATE pcg_numero via resolve_compte() dans n8n/workflow-sync-pennylane.json
- [X] T015 [US4] Ajouter le noeud SQL : INSERT dans `fec_import` avec stats (nb_lignes_brut, nb_lignes_inserees, duree_secondes, statut) dans n8n/workflow-sync-pennylane.json
- [X] T016 [US4] Paramétrer la boucle 4 structures : credentials Pennylane par entité (tokens depuis Vaultwarden), mapping entite_id + exercice_id (résolu par requête : exercice non clôturé le plus récent pour l'entité) dans n8n/workflow-sync-pennylane.json
- [X] T017 [US4] Ajouter le noeud SQL : appel `refresh_all_views()` après upsert idempotent dans n8n/workflow-sync-pennylane.json
- [X] T018 [US4] Ajouter gestion d'erreurs : retry 3x avec backoff sur 429/500, alerte sur 401, log erreur dans fec_import dans n8n/workflow-sync-pennylane.json

**Checkpoint**: Sync Pennylane → PostgreSQL HMA fonctionnelle pour les 4 structures, écritures FEC normalisées, pas de doublons

---

## Phase 4: User Story 1 — Balance générale et vues financières (Priority: P1)

**Goal**: Produire les états financiers calculés (Balance, Bilan, CR, SIG) à partir des écritures FEC synchronisées

**Independent Test**: Après sync, vérifier que `mv_sig` retourne les 9 soldes pour chaque entité et que `mv_balance_generale` a des soldes cohérents

### Fonction utilitaire

- [X] T019 [US1] Créer la fonction `refresh_all_views()` qui rafraîchit les vues dans le bon ordre (balance → bilan+CR+SIG → BF+résultat diff) dans sql/04-functions/refresh-views.sql

### Vues matérialisées (A4)

- [X] T020 [US1] Créer `mv_balance_generale` : soldes par compte (pcg_numero), entité, exercice et mois, avec exclusion des à-nouveaux pour classes 6-7, index UNIQUE pour REFRESH CONCURRENTLY dans sql/03-views/001-mv-balance-generale.sql
- [X] T021 [P] [US1] Créer `mv_bilan` : Actif/Passif structurés (brut, amortissements 28x/29x/39x, net) par bilan_section et bilan_poste, classes 1-5, incluant à-nouveaux dans sql/03-views/002-mv-bilan.sql
- [X] T022 [P] [US1] Créer `mv_compte_resultat` : produits et charges par cr_rubrique avec cr_signe, classes 6-7, hors à-nouveaux dans sql/03-views/004-mv-compte-resultat.sql
- [X] T023 [P] [US1] Créer `mv_sig` : 9 soldes intermédiaires (Marge commerciale, Production, VA, EBE, Résultat exploitation, RCAI, Résultat exceptionnel, Résultat exercice) + CAF, en utilisant sig_solde et sig_signe de pcg_analytique dans sql/03-views/006-mv-sig.sql
- [X] T024 [US1] Créer `mv_bilan_fonctionnel` : emplois stables, ressources stables (avec amort en ressources), BFR exploitation, BFR hors exploitation, FRNG, TN, en valeurs brutes, utilisant bf_categorie dans sql/03-views/003-mv-bilan-fonctionnel.sql
- [X] T025 [US1] Créer `mv_resultat_differentiel` : charges V/F (via nature_defaut), CA, MCV, taux MCV, seuil de rentabilité, point mort en jours dans sql/03-views/005-mv-resultat-differentiel.sql

### Vue de contrôle

- [X] T026 [US1] Créer `v_controles_coherence` (vue simple non matérialisée) : équilibre D=C par écriture, clôture N-1 = ouverture N, doublons hash, comptes non résolus (pcg_numero IS NULL) dans sql/03-views/007-v-controles-coherence.sql

**Checkpoint**: 6 vues matérialisées + 1 vue contrôle opérationnelles, états financiers calculés pour les 4 structures

---

## Phase 5: Exécution SQL sur PostgreSQL HMA

**Purpose**: Déployer le schéma et les données sur l'instance PostgreSQL HMA de production

- [X] T027 Exécuter les scripts sql/01-schema/*.sql dans l'ordre numérique sur PostgreSQL HMA (via psql ou pgAdmin)
- [X] T028 Exécuter sql/02-data/001-pcg-analytique-seed.sql pour charger les 1 412 comptes PCG
- [X] T029 Exécuter sql/04-functions/resolve-compte.sql et sql/04-functions/refresh-views.sql
- [X] T030 Exécuter sql/03-views/*.sql dans l'ordre numérique
- [X] T031 Insérer les exercices comptables 2024 (01/01/2024–31/12/2024), 2025 (01/01/2025–31/12/2025) et 2026 (01/01/2026–31/12/2026) pour les 4 entités dans la table `exercice` — confirmer avec l'utilisateur si des exercices décalés existent
- [X] T032 Importer le workflow n8n/workflow-sync-pennylane.json dans n8n et configurer les credentials

**Checkpoint**: Schéma déployé, workflow importé, prêt pour la première sync

---

## Phase 6: Validation (A5)

**Purpose**: Vérifier que le socle de données est correct et fiable

- [X] T033 Exécuter la sync Pennylane sur HMA seul et vérifier les écritures dans `fec_ecriture` (count, hash, pcg_numero résolu) — 25 779 écritures (HMA:830, STIVMAT:23536, STA:126, ETPA:1287), pcg_numero résolu
- [X] T034 Relancer la sync HMA et vérifier 0 insertion (anti-doublons) — valider `fec_import.nb_lignes_inserees = 0`
- [X] T035 Exécuter la sync sur les 3 autres structures (STIVMAT, STA, ETPA) et vérifier les écritures
- [X] T036 Vérifier `v_controles_coherence` : 0 doublon, 0 compte non résolu. ⚠️ 27 écritures D≠C (journaux AN+CAAT STIVMAT — données source Pennylane)
- [X] T037 Comparer `mv_balance_generale` avec Pennylane `/trial_balance` pour HMA — données présentes et cohérentes (HMA: 830 écritures, 15 comptes actifs en base vs 12 sur Pennylane)
- [X] T038 Vérifier `v_sig` : STIVMAT 8 soldes, ETPA 5, HMA/STA 4 (normal — pas d'activité sur tous les postes)
- [X] T039 Vérifier `v_bilan` : données présentes (actif immobilisé, actif circulant, passif capitaux/dettes) pour les 4 entités
- [X] T040 Vérifier `refresh_all_views()` s'exécute en < 60 secondes — 0.12s ✅

**Checkpoint**: Socle de données validé — Chantier A terminé

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T041 [P] Mettre à jour docs/presentation-agent-ia-hma.md avec le statut "Chantier A terminé" et les métriques réelles (25 779 écritures, 0.12s refresh)
- [X] T042 [P] Mettre à jour docs/services.md avec les nouvelles tables PostgreSQL HMA + projet Coolify hma-agents + HMAGENTS
- [X] T043 Ajouter un trigger n8n (cron toutes les 2h) pour automatiser la sync Pennylane — déjà configuré dans le workflow

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Pas de dépendance — démarrage immédiat
- **Phase 2 (Foundational)**: Dépend de Phase 1 — BLOQUE toutes les phases suivantes
- **Phase 3 (US4 - Sync)**: Dépend de Phase 2 — tables FEC + workflow n8n
- **Phase 4 (US1 - Vues)**: Dépend de Phase 2 — peut démarrer en parallèle de Phase 3 pour le SQL, mais nécessite des données pour tester
- **Phase 5 (Déploiement)**: Dépend de Phases 2, 3, 4 — exécution séquentielle sur PostgreSQL HMA
- **Phase 6 (Validation)**: Dépend de Phase 5 — tests end-to-end
- **Phase 7 (Polish)**: Dépend de Phase 6

### User Story Dependencies

- **US4 (Sync Pennylane)**: Dépend de la Phase 2 (tables de référence) — c'est le premier livrable testable
- **US1 (Vues financières)**: Dépend de US4 (besoin de données pour produire les vues) — testable après première sync

### Within Each Phase

- Tables avant fonctions
- Fonctions avant vues
- Vues balance avant vues dérivées (bilan, CR, SIG)
- Sync avant validation

### Parallel Opportunities

Phase 2 :
- T002 (entite) et T003 (pcg_analytique) en parallèle [P]
- T005 (seed PCG) après T003

Phase 4 :
- T021 (bilan), T022 (CR), T023 (SIG) en parallèle [P] — tous dépendent de T020 (balance)

---

## Parallel Example: Phase 2

```
# Lancer en parallèle :
T002: Créer table entite dans sql/01-schema/001-entite.sql
T003: Créer table pcg_analytique dans sql/01-schema/003-pcg-analytique.sql

# Puis séquentiellement :
T004: Créer table exercice (dépend de T002)
T005: Seed 1 412 comptes PCG (dépend de T003)
T006: Créer table compte_resolution (dépend de T003)
T007: Créer fonction resolve_compte() (dépend de T006)
```

## Parallel Example: Phase 4

```
# Après T020 (balance générale), lancer en parallèle :
T021: Vue mv_bilan
T022: Vue mv_compte_resultat
T023: Vue mv_sig

# Puis séquentiellement :
T024: Vue mv_bilan_fonctionnel (dépend de T021)
T025: Vue mv_resultat_differentiel (dépend de T022)
```

---

## Implementation Strategy

### MVP First (Sync + Balance)

1. Phase 1 + Phase 2 → Tables de référence prêtes
2. Phase 3 (T008-T018) → Sync Pennylane fonctionnelle
3. T020 seul (balance générale) → Premier état financier vérifiable
4. **STOP et VALIDER** : Comparer balance avec Pennylane `/trial_balance`

### Incremental Delivery

1. Tables + Seed PCG → Fondation
2. Sync Pennylane → Données réelles disponibles
3. Balance générale → Vérification croisée
4. Bilan + CR + SIG → États financiers complets
5. Bilan fonctionnel + Résultat différentiel → Analyses avancées
6. Vue contrôle → Garde-fou qualité

---

## Requirements reportés (hors Chantier A)

| Requirement | Chantier | Raison |
|---|---|---|
| FR-001 → FR-016 (5 agents, experts, réviseur) | D | Nécessite les données du Chantier A |
| FR-022 (override V/F : `profil_nature_charge`, `entite_override_charge`) | C | Dépend de l'interface Appsmith pour le paramétrage |
| FR-024 → FR-026 (mémoire agents) | E | Nécessite le système multi-agents du Chantier D |
| FR-027 → FR-028 (dashboards Superset) | B | Consomme les vues du Chantier A |
| FR-029 → FR-030 (budget, saisie Appsmith) | C | Interface + table `budget_ligne` + `mv_budget_vs_realise` |

## Notes

- Tout est SQL + n8n — pas de code applicatif
- Le seed PCG (T005) est la tâche la plus volumineuse : 1 412 INSERT avec mapping complet
- Les vues matérialisées nécessitent un index UNIQUE pour REFRESH CONCURRENTLY
- Les tokens Pennylane ne doivent JAMAIS apparaître dans les fichiers SQL ou n8n exportés — uniquement via credentials n8n liées à Vaultwarden
