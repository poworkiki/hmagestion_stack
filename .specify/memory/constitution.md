<!--
Sync Impact Report
- Version change: 0.0.0 (template) → 1.0.0
- Modified principles: N/A (first initialization)
- Added sections: 5 Core Principles, Contraintes Opérationnelles, Workflow Qualité, Governance
- Removed sections: All placeholder tokens replaced
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ compatible (Constitution Check section exists)
  - .specify/templates/spec-template.md ✅ compatible (no constitution reference needed)
  - .specify/templates/tasks-template.md ✅ compatible (phase structure aligned)
- Follow-up TODOs: none
-->

# Agent IA Comptable HMA — Constitution

## Core Principles

### I. Secrets-First (NON-NEGOTIABLE)

Aucun secret en clair dans le code, SQL, exports n8n ou fichiers versionnés.

- Les tokens API (Pennylane, OpenAI, Qdrant) MUST être stockés exclusivement dans Vaultwarden
- Les variables d'environnement locales MUST passer par `.env` (gitignored)
- Les credentials n8n MUST référencer Vaultwarden, jamais de valeurs en dur
- Tout commit contenant un secret MUST être rejeté et le secret révoqué immédiatement

### II. SQL-Only Data Layer

Le socle de données est 100% SQL (PostgreSQL/Supabase) + workflows n8n. Pas de code applicatif pour la couche données.

- Les vues matérialisées MUST être la seule interface de lecture des états financiers
- Les transformations de données MUST être implémentées en SQL ou en Code nodes n8n
- Aucun ORM ou couche d'abstraction applicative ne SHOULD être introduit pour le Chantier A
- Les scripts Python (seed, embeddings) MUST se limiter à la génération de données, pas à la logique métier

### III. Référentiel-Driven

`scripts/generate-pcg-seed.py` est la source de vérité unique pour le mapping des 1 412 comptes PCG.

- Toute vue matérialisée MUST être conforme à `docs/compta_analytique.md`
- Aucun calcul financier (SIG, CR, Bilan, ratios) ne MUST être implémenté sans vérification préalable dans ce référentiel
- Le mapping analytique (SIG, CR, Bilan, BF, V/F) MUST être modifié uniquement via `generate-pcg-seed.py`, jamais par UPDATE SQL direct
- Les formules du référentiel MUST citer les comptes PCG exacts utilisés

### IV. 5 Agents Non-Négociable (NON-NEGOTIABLE)

L'architecture multi-agents comporte exactement 5 agents, ni plus ni moins.

- Directeur de Mission : routage, délégation, synthèse
- Expert-Comptable Senior : chiffres, paie, cotisations, LODEOM social
- Juriste Senior : droit fiscal, sociétés, contrats, travail
- Analyste Financier Senior : SIG, ratios, simulations, recommandations
- Réviseur Qualité : vérification calculs, croisement sources, score confiance

Toute proposition de fusion ou suppression d'un agent MUST être refusée. Cette architecture a été validée par le décideur projet.

### V. French-Only

Tout est en français : code SQL (noms de colonnes, commentaires), documentation, interface utilisateur, réponses des agents, spécifications.

- Les mots-clés techniques (SQL, API, JSON, UUID, etc.) MUST rester en anglais
- Les titres de Requirements Spec-Kit MUST utiliser les mots-clés `SHALL` / `MUST` en anglais pour la validation
- Les noms de tables et colonnes SQL MUST être en français ou en notation technique standard (ex: `entite`, `exercice`, `pcg_numero`, `hash_md5`)

## Contraintes Opérationnelles

- Images Docker officielles uniquement pour les services déployés via Coolify
- Interface claire et minimaliste, pas de mode sombre pour le MVP
- Isolation multi-entité par RLS Supabase (quand activé)
- Les 4 structures (HMA, STIVMAT, STA, ETPA) ont des exercices calés sur l'année civile (01/01–31/12)

## Workflow Qualité

- Chaque vue matérialisée MUST être vérifiable par croisement avec les données source Pennylane
- La vue `v_controles_coherence` MUST être consultée après chaque synchronisation
- Les vues MUST supporter `REFRESH CONCURRENTLY` (index UNIQUE obligatoire)
- Tout développement UI MUST être testé avec Playwright

## Governance

- Cette constitution est le document d'autorité maximale pour les décisions architecturales du projet Agent IA Comptable
- Les principes marqués `(NON-NEGOTIABLE)` ne peuvent être modifiés que par décision explicite du décideur projet, documentée dans un amendement versionné
- Tout plan ou tâche en conflit avec un principe MUST être signalé comme CRITICAL dans `/speckit.analyze`
- Les amendements suivent le versionnement sémantique : MAJOR (suppression/redéfinition de principe), MINOR (ajout de principe ou section), PATCH (clarification)

**Version**: 1.0.0 | **Ratified**: 2026-04-02 | **Last Amended**: 2026-04-02
