# Feature Specification: Dashboard CRD sur mesure

**Feature Branch**: `002-dashboard-crd-custom`
**Created**: 2026-04-10
**Status**: Draft
**Input**: Dashboard CRD interactif sur mesure avec drilldown, KPI cards, graphiques courbe/barre/camembert/donut pour analyse comptable CRD des 4 structures HMA

## Contexte

Le cabinet HMA dispose actuellement de dashboards CRD dans Superset (`superset.hma.business`), mais ils sont limités en interactivité et en personnalisation. Les filtres natifs Superset ne s'appliquent pas systématiquement aux charts créés par API, le drilldown est basique, et le design est contraint par les templates Superset.

L'objectif est de créer un dashboard CRD (Compte de Resultat Differentiel) **sur mesure**, code en dur, connecte directement aux vues SQL PostgreSQL HMA (`v_crd`, `v_crd_drilldown`, `v_ytd_mensuel`). Ce dashboard doit offrir une experience interactive complete : drilldown par categorie/rubrique/compte, KPI cards avec evolution, et graphiques varies (courbe, barre, camembert, donut).

### Donnees source disponibles

Les vues PostgreSQL HMA sont deja en place et operationnelles :

- **`v_crd`** : CRD agrege par entite/exercice/trimestre — CA, charges variables, MCV, charges fixes, resultat exploitation, RCAI, resultat net, CAF + pourcentages et seuil de rentabilite
- **`v_crd_drilldown`** : Detail par categorie/rubrique/compte avec mois — permet le drill de chaque ligne CRD jusqu'au compte PCG
- **`v_ytd_mensuel`** : CA, charges, produits, resultat par mois — pour les courbes d'evolution temporelle
- **`v_sig`** : 9 soldes intermediaires de gestion + CAF
- **`v_sig_drilldown`** : Detail SIG par rubrique/compte avec mois

### Hypotheses

- Les vues SQL sont a jour et rafraichies automatiquement (sync Pennylane toutes les 2h)
- Les utilisateurs sont les gestionnaires du cabinet HMA (3-5 personnes)
- Le dashboard sera accessible via un navigateur web sur desktop et mobile
- L'authentification n'est pas requise pour le MVP (reseau interne / VPN)
- Le dashboard complement Superset, il ne le remplace pas immediatement

---

## Clarifications

### Session 2026-04-10

- Q: Comparaison inter-exercices — quelle periode de reference pour l'evolution des KPI ? → A: Libre choix de la periode de reference (N-1, N-2, trimestre, mois), avec l'exercice 2026 en cours comme contexte principal.
- Q: Consolidation groupe — le dashboard doit-il inclure une vue "Groupe HMA" agregee ? → A: Pas de consolidation — uniquement les 4 structures individuelles + comparaison cote a cote (US4).

---

## User Scenarios & Testing

### User Story 1 — Vue d'ensemble CRD avec KPI cards (Priority: P1)

Un gestionnaire ouvre le dashboard et voit immediatement les 5 indicateurs cles du CRD (CA, MCV, Resultat exploitation, Resultat net, CAF) pour la structure selectionnee, avec les pourcentages par rapport au CA et l'evolution par rapport a une periode de reference au choix (trimestre precedent, exercice N-1, N-2, mois). L'exercice 2026 en cours est le contexte par defaut.

**Why this priority** : C'est le premier ecran — l'utilisateur doit comprendre la situation financiere en un coup d'oeil sans aucune interaction.

**Independent Test** : Ouvrir le dashboard, selectionner STIVMAT, verifier que les 5 KPI cards affichent les bons montants (croises avec `v_crd`) et les bons pourcentages.

**Acceptance Scenarios** :

1. **Given** le dashboard est charge, **When** l'utilisateur selectionne une structure (ex: STIVMAT), **Then** les 5 KPI cards (CA, MCV, Resultat exploitation, Resultat net, CAF) affichent les montants en euros et le pourcentage du CA.
2. **Given** les KPI cards sont affichees, **When** une periode de reference est selectionnee (trimestre precedent, N-1, N-2, mois), **Then** chaque card affiche une fleche haut/bas avec le pourcentage d'evolution par rapport a cette reference.
3. **Given** l'utilisateur change de structure ou de periode, **When** il utilise les filtres, **Then** toutes les KPI cards se mettent a jour instantanement.

---

### User Story 2 — Tableau CRD complet avec drilldown (Priority: P1)

Un gestionnaire consulte le tableau CRD structure (du CA au resultat net + CAF) et peut cliquer sur chaque ligne pour voir le detail par rubrique, puis par compte PCG.

**Why this priority** : Le drilldown est la valeur ajoutee principale par rapport a Superset — comprendre d'ou viennent les chiffres en 2 clics.

**Independent Test** : Cliquer sur "Charges variables" dans le tableau CRD et verifier que les rubriques s'affichent avec leurs montants (croises avec `v_crd_drilldown`), puis cliquer sur une rubrique pour voir les comptes PCG.

**Acceptance Scenarios** :

1. **Given** le tableau CRD est affiche, **When** l'utilisateur clique sur une categorie (ex: "Charges variables"), **Then** les rubriques de cette categorie s'affichent avec leurs montants.
2. **Given** une categorie est expanee, **When** l'utilisateur clique sur une rubrique, **Then** les comptes PCG individuels s'affichent avec numero, libelle et montant.
3. **Given** le drilldown est ouvert, **When** l'utilisateur reclique sur la categorie, **Then** le detail se replie.
4. **Given** le tableau CRD est affiche, **When** les donnees sont presentes, **Then** chaque ligne affiche le montant, le pourcentage du CA et une barre de progression visuelle.

---

### User Story 3 — Graphiques d'evolution temporelle (Priority: P1)

Un gestionnaire visualise l'evolution mensuelle du CA, de la MCV et du resultat net sous forme de courbes, et la repartition des charges en camembert/donut.

**Why this priority** : Les tendances temporelles sont essentielles pour detecter des anomalies ou des saisonnalites — impossible a voir dans un tableau statique.

**Independent Test** : Verifier que la courbe du CA mensuel correspond aux donnees de `v_ytd_mensuel` pour STIVMAT 2025, et que le camembert des charges montre la bonne repartition V/F.

**Acceptance Scenarios** :

1. **Given** une structure et un exercice sont selectionnes, **When** le dashboard affiche la section graphiques, **Then** une courbe d'evolution mensuelle montre CA, MCV et resultat net sur 12 mois.
2. **Given** les graphiques sont affiches, **When** l'utilisateur survole un point de la courbe, **Then** un tooltip affiche le mois, le montant exact et le pourcentage d'evolution.
3. **Given** les donnees de charges sont disponibles, **When** le dashboard affiche le graphique de repartition, **Then** un donut/camembert montre la repartition charges variables vs charges fixes avec montants et pourcentages.
4. **Given** les graphiques sont affiches, **When** l'utilisateur clique sur un segment du camembert, **Then** le detail des rubriques de ce segment s'affiche.

---

### User Story 4 — Comparaison multi-structures (Priority: P2)

Un gestionnaire compare les indicateurs CRD de 2, 3 ou 4 structures cote a cote pour identifier les ecarts de performance.

**Why this priority** : La comparaison inter-structures est utile pour le pilotage groupe mais moins critique que la vue individuelle.

**Independent Test** : Selectionner STIVMAT et ETPA, verifier que les barres groupees affichent les bons CA respectifs.

**Acceptance Scenarios** :

1. **Given** le mode comparaison est actif, **When** l'utilisateur selectionne 2+ structures, **Then** un graphique en barres groupees affiche les KPI cles cote a cote.
2. **Given** la comparaison est affichee, **When** l'utilisateur survole une barre, **Then** un tooltip affiche le montant et la structure.

---

### User Story 5 — Export et partage (Priority: P3)

Un gestionnaire exporte le dashboard en PDF ou capture les graphiques pour les integrer dans un rapport.

**Why this priority** : L'export est pratique mais secondaire — les gestionnaires peuvent faire des captures d'ecran en attendant.

**Independent Test** : Cliquer sur "Exporter PDF" et verifier que le fichier genere contient les KPI et graphiques visibles.

**Acceptance Scenarios** :

1. **Given** le dashboard est affiche avec des donnees, **When** l'utilisateur clique sur "Exporter PDF", **Then** un fichier PDF est telecharge contenant les KPI cards, le tableau CRD et les graphiques.

---

### Edge Cases

- **Donnees absentes** : une structure n'a pas d'ecritures pour l'exercice selectionne — le dashboard affiche "Aucune donnee" avec un message explicatif au lieu de 0 partout.
- **CA a zero** : le CA est a 0 pour un trimestre (structure sans activite) — les pourcentages du CA affichent "N/A" au lieu de divisions par zero.
- **Trimestre incomplet** : le trimestre en cours n'a que 1 ou 2 mois de donnees — le dashboard l'indique clairement ("donnees partielles").
- **Ecran mobile** : le dashboard est consulte sur un telephone — les KPI cards s'empilent verticalement, le tableau CRD est scrollable horizontalement.
- **Connexion lente** : la requete SQL prend plus de 5 secondes — un indicateur de chargement est affiche.

---

## Requirements

### Functional Requirements

#### KPI Cards

- **FR-001**: System MUST afficher 5 KPI cards principales : CA, MCV, Resultat d'exploitation, Resultat net, CAF — avec montant en euros et pourcentage du CA.
- **FR-002**: System MUST afficher l'evolution (fleche + pourcentage) par rapport a une periode de reference configurable (trimestre precedent, exercice N-1, N-2, mois precedent) sur chaque KPI card.
- **FR-003**: System MUST colorer les KPI cards selon la performance : vert si positif/en hausse, rouge si negatif/en baisse.

#### Tableau CRD drilldown

- **FR-004**: System MUST afficher le tableau CRD complet (du CA au Resultat net + CAF) avec montant, pourcentage du CA et barre de progression.
- **FR-005**: System MUST permettre le drilldown a 3 niveaux : categorie CRD → rubrique → compte PCG (numero + libelle + montant).
- **FR-006**: System MUST afficher le seuil de rentabilite, le point mort (en jours) et la marge de securite dans une section dediee du tableau.

#### Graphiques

- **FR-007**: System MUST afficher un graphique en courbes de l'evolution mensuelle (CA, MCV, Resultat net) sur l'exercice selectionne.
- **FR-008**: System MUST afficher un graphique donut/camembert de la repartition charges variables vs charges fixes.
- **FR-009**: System MUST afficher un graphique en barres horizontales ou verticales pour le detail par rubrique CRD.
- **FR-010**: System MUST afficher des tooltips interactifs (montant, pourcentage, mois) au survol de chaque element graphique.

#### Filtres et navigation

- **FR-011**: System MUST proposer un filtre Structure (HMA, STIVMAT, STA, ETPA) avec selection unique ou multiple.
- **FR-012**: System MUST proposer un filtre Exercice (annee, defaut: 2026), un filtre Trimestre, et un selecteur de periode de reference pour l'evolution (N-1, N-2, trimestre precedent, mois precedent).
- **FR-013**: System MUST actualiser tous les composants (KPI, tableau, graphiques) instantanement lors d'un changement de filtre.

#### Comparaison multi-structures

- **FR-014**: System MUST permettre la comparaison cote a cote de 2 a 4 structures via un graphique en barres groupees.

#### Responsive et performance

- **FR-015**: System MUST etre consultable sur mobile (responsive design) avec un layout adapte (KPI empilees, tableau scrollable).
- **FR-016**: System MUST afficher les donnees en moins de 3 secondes apres un changement de filtre.

### Key Entities

- **Structure (Entite)** : une des 4 structures gerees (HMA, STIVMAT, STA, ETPA), identifiee par `entite_id`.
- **CRD** : Compte de Resultat Differentiel — decomposition du CA en charges variables, MCV, charges fixes, resultat exploitation, RCAI, resultat net, CAF.
- **Rubrique CRD** : sous-categorie d'une ligne CRD (ex: "Achats matieres premieres" dans "Charges variables").
- **Compte PCG** : compte du Plan Comptable General (numero + libelle) — niveau de detail le plus fin du drilldown.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Les gestionnaires visualisent les 5 KPI CRD d'une structure en moins de 3 secondes apres chargement.
- **SC-002**: Le drilldown d'une categorie CRD jusqu'au compte PCG s'effectue en 2 clics maximum.
- **SC-003**: Les graphiques d'evolution mensuels couvrent 12 mois d'un exercice complet.
- **SC-004**: Le dashboard est lisible et utilisable sur un ecran mobile (largeur 375px minimum).
- **SC-005**: Les montants affiches dans le dashboard correspondent exactement aux donnees des vues SQL PostgreSQL (ecart 0).
- **SC-006**: Le temps de chargement initial du dashboard est inferieur a 5 secondes.
