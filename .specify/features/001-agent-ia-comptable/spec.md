# Feature Specification: Agent IA Comptable Multi-Agents

**Feature Branch**: `001-agent-ia-comptable`
**Created**: 2026-04-02
**Status**: Draft
**Input**: Agent IA comptable multi-agents pour l'analyse financière et comptable des 4 structures HMA (HMA, STIVMAT, STA, ETPA)

## Contexte

HMA est un cabinet de gestion/expertise comptable basé en Guyane qui gère 4 structures : HMA (holding), STIVMAT (transport de personnes), STA (transport de personnes), ETPA (transformation de produits agricoles). Le cabinet a besoin d'un assistant IA capable de répondre à des questions comptables, fiscales, juridiques et financières en s'appuyant sur les données réelles des 4 structures et une base de connaissances métier.

### Périmètre

Le système couvre 3 niveaux de questions :
1. **Questions métier pures** : réponses basées sur la base de connaissances (manuels DCG/DSCG, réglementation LODEOM/Girardin, conventions collectives Guyane)
2. **Questions sur les données comptables** : interrogation des données des 4 structures via l'API Pennylane et les données synchronisées en base
3. **Questions croisées** : analyse combinant données comptables et expertise métier (ex : "Le taux de matières premières d'ETPA est-il cohérent pour la transformation agricole ?")

### Hypothèses

- Les 4 tokens API Pennylane sont fonctionnels et en lecture seule
- L'infrastructure est déjà déployée : n8n, Qdrant, Supabase, Metabase, Appsmith, Vaultwarden
- La base de connaissances Qdrant contient déjà les manuels DCG/DSCG (18 132 points), la réglementation (11 points) et les conventions collectives (6 points)
- Les utilisateurs sont des comptables et gestionnaires du cabinet HMA
- Le système est en français exclusivement
- Pas de consolidation légale IFRS (hors périmètre) — uniquement agrégation + élimination intra-groupe par flag

---

## User Scenarios & Testing

### User Story 1 — Question comptable sur une structure (Priority: P1)

Un comptable du cabinet pose une question sur les données comptables d'une structure spécifique. Le système identifie la structure, interroge les données et fournit une réponse chiffrée sourcée.

**Why this priority** : C'est l'usage quotidien principal — accéder rapidement aux chiffres sans naviguer dans Pennylane manuellement.

**Independent Test** : Peut être testé en posant "Quel est le chiffre d'affaires de STIVMAT au T3 2025 ?" et en vérifiant que la réponse correspond aux données Pennylane.

**Acceptance Scenarios** :

1. **Given** l'utilisateur est connecté au chat, **When** il demande "Quel est le CA de STIVMAT au T3 2025 ?", **Then** le système identifie la structure STIVMAT, interroge les données comptables et retourne le montant exact avec la période couverte.
2. **Given** l'utilisateur pose une question sur une structure, **When** la structure n'est pas explicitement nommée mais identifiable par le contexte de session, **Then** le système utilise la structure active de la session.
3. **Given** l'utilisateur demande des données, **When** les données ne sont pas disponibles ou la période est hors exercice, **Then** le système indique clairement l'absence de données au lieu d'inventer un chiffre.

---

### User Story 2 — Question métier juridique ou réglementaire (Priority: P1)

Un gestionnaire pose une question sur la réglementation applicable (LODEOM, Girardin, conventions collectives, droit fiscal). Le système recherche dans la base de connaissances et fournit une réponse argumentée avec les sources.

**Why this priority** : Les questions réglementaires ultramarines sont complexes et spécifiques — l'accès rapide à l'information est critique pour le cabinet.

**Independent Test** : Peut être testé en posant "Quelles sont les conditions d'éligibilité au Girardin IS ?" et en vérifiant la présence de sources citées.

**Acceptance Scenarios** :

1. **Given** l'utilisateur pose une question juridique, **When** la réponse existe dans la KB Qdrant, **Then** le système fournit une réponse structurée avec les articles de loi ou références cités.
2. **Given** l'utilisateur pose une question hors périmètre du KB, **When** aucune source pertinente n'est trouvée, **Then** le système indique que la question dépasse sa base de connaissances et recommande une vérification manuelle.

---

### User Story 3 — Question croisée multi-expert (Priority: P1)

Un gestionnaire pose une question complexe nécessitant l'intervention de plusieurs experts (ex : impact global d'une embauche incluant coût chargé, obligations juridiques et impact financier).

**Why this priority** : C'est la valeur différenciante du système — croiser automatiquement les données comptables, la réglementation et l'analyse financière.

**Independent Test** : Peut être testé en posant "ETPA veut embaucher 3 conducteurs de travaux. Quel impact global ?" et en vérifiant que la réponse couvre les aspects comptable, juridique et financier.

**Acceptance Scenarios** :

1. **Given** l'utilisateur pose une question mixte, **When** le Directeur de Mission identifie plusieurs domaines d'expertise, **Then** plusieurs experts sont sollicités et leurs réponses sont croisées et vérifiées avant synthèse.
2. **Given** deux experts produisent des informations contradictoires, **When** le Réviseur Qualité détecte l'incohérence, **Then** le Directeur de Mission arbitre et la contradiction est signalée dans la réponse.
3. **Given** une question multi-expert est traitée, **When** la réponse est produite, **Then** un score de confiance (haute / moyenne / à vérifier) est affiché avec le détail des vérifications effectuées.

---

### User Story 4 — Synchronisation des données Pennylane (Priority: P1)

Les données comptables des 4 structures sont synchronisées automatiquement depuis Pennylane vers la base Supabase, permettant des analyses et des vues matérialisées performantes.

**Why this priority** : Sans données à jour, aucune question comptable ne peut recevoir de réponse fiable.

**Independent Test** : Peut être testé en déclenchant une synchronisation et en vérifiant que les écritures Pennylane apparaissent dans la table `fec_ecriture` avec le bon hash anti-doublons.

**Acceptance Scenarios** :

1. **Given** une synchronisation est déclenchée, **When** de nouvelles écritures existent dans Pennylane, **Then** elles sont importées dans `fec_ecriture` via le pattern staging → merge → refresh.
2. **Given** une écriture déjà importée existe, **When** la synchronisation s'exécute, **Then** l'écriture n'est pas dupliquée (contrôle par hash MD5).
3. **Given** la synchronisation est terminée, **When** les vues matérialisées sont rafraîchies, **Then** les SIG, CR, Bilan et autres vues reflètent les données à jour.

---

### User Story 5 — Dashboards financiers (Priority: P2)

Les gestionnaires consultent des tableaux de bord visuels (SIG, Compte de résultat, Bilan, Ratios) pour chaque structure et en comparatif groupe.

**Why this priority** : Les dashboards complètent le chat IA en offrant une vue synthétique permanente. Ils sont utiles mais moins critiques que le système conversationnel.

**Independent Test** : Peut être testé en ouvrant le dashboard Metabase SIG et en vérifiant que les 9 soldes intermédiaires sont calculés pour chaque structure.

**Acceptance Scenarios** :

1. **Given** les données sont synchronisées, **When** un gestionnaire ouvre le dashboard SIG, **Then** les 9 soldes intermédiaires de gestion + CAF sont affichés par entité et par mois.
2. **Given** le gestionnaire active le toggle consolidation, **When** des flux intra-groupe existent, **Then** ils sont éliminés du total consolidé.
3. **Given** un budget a été saisi, **When** le gestionnaire ouvre le dashboard Budget vs Réalisé, **Then** les écarts montant et % sont affichés avec des alertes visuelles sur les dépassements.

---

### User Story 6 — Saisie budget et paramétrage (Priority: P2)

Les gestionnaires saisissent les budgets prévisionnels et paramètrent les profils de charges (variable/fixe) par entité via une interface dédiée.

**Why this priority** : Le budget est nécessaire pour le dashboard Budget vs Réalisé et les simulations de l'Analyste Financier, mais le système fonctionne sans.

**Independent Test** : Peut être testé en saisissant un budget pour STIVMAT et en vérifiant qu'il apparaît dans le dashboard Budget vs Réalisé.

**Acceptance Scenarios** :

1. **Given** un gestionnaire ouvre le formulaire budget, **When** il saisit un montant par compte ou catégorie, **Then** le budget est enregistré et disponible pour comparaison.
2. **Given** un gestionnaire modifie le profil nature de charge d'une entité, **When** il change un compte de "variable" à "fixe", **Then** le résultat différentiel et le seuil de rentabilité sont recalculés.

---

### User Story 7 — Feedback et amélioration continue (Priority: P3)

Les utilisateurs notent les réponses de l'agent (1 à 5) et peuvent fournir des corrections. Les bonnes réponses deviennent des exemples injectés dans les futurs prompts.

**Why this priority** : L'amélioration continue est importante mais le système doit d'abord fonctionner correctement avant de s'auto-améliorer.

**Independent Test** : Peut être testé en notant une réponse avec un score de 5, puis en vérifiant qu'elle est récupérée comme exemple positif lors d'une question similaire ultérieure.

**Acceptance Scenarios** :

1. **Given** l'agent a fourni une réponse, **When** l'utilisateur attribue un score de 1 à 5, **Then** le feedback est enregistré avec le prompt original, l'output et les tags associés.
2. **Given** une réponse a un score >= 4, **When** une question similaire est posée ultérieurement, **Then** la réponse précédente est injectée comme exemple positif (few-shot).
3. **Given** une réponse a un score < 4 avec correction, **When** une question similaire est posée, **Then** la correction est utilisée comme contre-exemple.

---

### Edge Cases

- Que se passe-t-il quand l'utilisateur pose une question sur une 5ème structure qui n'existe pas ?
- Comment le système gère-t-il une question dans une langue autre que le français ?
- Que se passe-t-il si l'API Pennylane est indisponible lors d'une question comptable ?
- Comment le système gère-t-il un exercice comptable décalé (≠ année civile) ?
- Que se passe-t-il quand le Réviseur détecte une erreur de calcul critique dans la réponse d'un expert ?
- Comment le système gère-t-il une question hors périmètre (ex : "Quel temps fait-il ?") ?
- Que se passe-t-il si les vues matérialisées ne sont pas à jour au moment d'une question ?

---

## Requirements

### Functional Requirements

#### Système multi-agents (5 agents)

- **FR-001**: System MUST router chaque question vers le(s) expert(s) approprié(s) via le Directeur de Mission, en identifiant l'intent (comptable / fiscal / financier / mixte / hors dossier) et la(les) structure(s) concernée(s).
- **FR-002**: System MUST permettre la délégation parallèle à plusieurs experts quand la question est mixte.
- **FR-003**: System MUST soumettre chaque réponse d'expert au Réviseur Qualité avant la synthèse finale.
- **FR-004**: System MUST attribuer un score de confiance (haute / moyenne / à vérifier) à chaque réponse, avec le détail des vérifications effectuées.
- **FR-005**: System MUST citer les sources utilisées (articles de loi, comptes PCG, collections Qdrant) dans chaque réponse.

#### Expert-Comptable Senior

- **FR-006**: System MUST interroger les données comptables des 4 structures (balances, écritures, factures, tiers) via les données synchronisées et l'API Pennylane.
- **FR-007**: System MUST calculer les coûts chargés en tenant compte des exonérations LODEOM applicables.
- **FR-008**: System MUST identifier les comptes impactés (numéros PCG) lors d'une analyse comptable.

#### Juriste Senior

- **FR-009**: System MUST rechercher dans la base de connaissances Qdrant (manuels, réglementation, conventions collectives) pour répondre aux questions juridiques.
- **FR-010**: System MUST distinguer le social chiffré (paie, cotisations → Expert-Comptable) du social juridique (licenciement, contentieux → Juriste).

#### Analyste Financier Senior

- **FR-011**: System MUST calculer les 9 soldes intermédiaires de gestion (SIG) + CAF à partir des vues matérialisées.
- **FR-012**: System MUST produire des simulations d'impact (ex : variation de charges sur l'EBE) à partir des données existantes.
- **FR-013**: System MUST comparer les indicateurs financiers des 4 structures entre elles.

#### Réviseur Qualité

- **FR-014**: System MUST recalculer indépendamment les chiffres fournis par les experts pour vérification.
- **FR-015**: System MUST vérifier que les articles et normes cités existent dans la base de connaissances.
- **FR-016**: System MUST détecter les contradictions entre les réponses de plusieurs experts.

#### Synchronisation Pennylane

- **FR-017**: System MUST synchroniser les écritures comptables des 4 structures depuis Pennylane vers Supabase via un pattern staging → merge → refresh.
- **FR-018**: System MUST prévenir les doublons d'import via un hash MD5 unique par écriture.
- **FR-019**: System MUST rafraîchir les 7 vues matérialisées après chaque synchronisation.

#### Modèle de données

- **FR-020**: System MUST stocker les écritures au format FEC normalisé (18 colonnes + champs calculés, Art. A.47 A-1 LPF).
- **FR-021**: System MUST maintenir un mapping des 1 412 comptes PCG avec catégories analytiques (SIG, CR, Bilan, Bilan fonctionnel, Variable/Fixe).
- **FR-022**: System MUST permettre l'override de la nature Variable/Fixe par profil sectoriel et par entité.
- **FR-023**: System MUST résoudre les numéros de compte FEC (avec auxiliaires) vers les comptes PCG via une table de résolution par préfixe décroissant.

#### Mémoire agents

- **FR-024**: System MUST stocker les outputs passés de chaque expert dans des collections Qdrant dédiées (mémoire long terme sémantique).
- **FR-025**: System MUST maintenir un contexte de session partagé entre les 5 agents (mémoire court terme).
- **FR-026**: System MUST enregistrer le feedback utilisateur (score 1-5, correction optionnelle) et l'utiliser pour l'injection few-shot (mémoire procédurale).

#### Dashboards

- **FR-027**: System MUST afficher des dashboards visuels pour les SIG, Compte de résultat, Bilan, Bilan fonctionnel, Résultat différentiel, Budget vs Réalisé et Ratios financiers.
- **FR-028**: System MUST permettre la consolidation groupe avec élimination des flux intra-groupe activable/désactivable par toggle.

#### Interface de saisie

- **FR-029**: System MUST fournir un formulaire de saisie budget par compte ou catégorie (montant ou %).
- **FR-030**: System MUST permettre le paramétrage des profils de charges et overrides par entité.

### Key Entities

- **Entité** : une des 4 structures gérées (HMA, STIVMAT, STA, ETPA), avec activité, profil sectoriel et relation parent/enfant.
- **Exercice** : exercice comptable par entité, pouvant être décalé par rapport à l'année civile.
- **Écriture FEC** : écriture comptable normalisée au format FEC, rattachée à une entité et un exercice.
- **Compte PCG** : un des 1 412 comptes du Plan Comptable Général, avec mapping analytique (SIG, CR, Bilan, V/F).
- **Budget** : budget prévisionnel par ligne ou catégorie, par entité et exercice.
- **Session agent** : contexte partagé d'une conversation multi-agents, avec les données collectées et décisions prises.
- **Feedback agent** : notation d'une réponse avec score, correction optionnelle et tags pour injection few-shot.

---

## Success Criteria

### Measurable Outcomes

- **SC-001** : Les utilisateurs obtiennent une réponse à une question comptable simple en moins de 30 secondes.
- **SC-002** : Les réponses multi-experts (questions croisées) sont délivrées en moins de 2 minutes.
- **SC-003** : 95% des réponses chiffrées correspondent aux données sources (Pennylane / Supabase) après vérification du Réviseur.
- **SC-004** : 100% des réponses citent au moins une source vérifiable (article de loi, compte PCG, collection KB).
- **SC-005** : La synchronisation Pennylane des 4 structures s'exécute sans doublon sur 3 cycles consécutifs.
- **SC-006** : Les 7 vues matérialisées se rafraîchissent en moins de 60 secondes après synchronisation.
- **SC-007** : Le score de confiance moyen des réponses atteint "haute" pour 80% des questions après 30 jours d'utilisation avec feedback.
- **SC-008** : Les gestionnaires réduisent de 50% le temps passé à chercher manuellement des informations comptables et réglementaires.
