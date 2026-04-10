# Tasks: Dashboard CRD sur mesure

**Input**: Design documents from `/specs/002-dashboard-crd-custom/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Tests Playwright en phase finale (validation UI responsive). Pas de TDD.

**Organisation**: Taches groupees par user story (US1-US5) pour permettre une implementation et un test independants de chaque story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Peut etre execute en parallele (fichiers differents, pas de dependance)
- **[Story]**: User Story associee (US1 = KPI cards, US2 = drilldown, US3 = graphiques, US4 = comparaison, US5 = export)

---

## Phase 1: Setup (Infrastructure projet)

**Purpose**: Creer l'arborescence du projet Dash et installer les dependances

- [ ] T001 Creer l'arborescence `hma-dashboard/` avec `components/`, `assets/`, `tests/` a la racine du depot
- [ ] T002 Creer `hma-dashboard/requirements.txt` avec dash, dash-bootstrap-components, plotly, psycopg2-binary, pandas, gunicorn
- [ ] T003 Creer `hma-dashboard/assets/style.css` avec les styles de base (couleurs HMA, KPI cards, responsive)

---

## Phase 2: Foundational (Couche donnees + layout)

**Purpose**: Connexion PostgreSQL et squelette Dash — BLOQUE toutes les user stories

**CRITICAL**: Aucune tache US ne peut commencer avant la fin de cette phase

- [ ] T004 Creer `hma-dashboard/data.py` : connexion PostgreSQL via `HMA_DB_URL` (env var), fonctions `get_crd(entite_id, annee, trimestre=None)`, `get_crd_drilldown(entite_id, annee, categorie=None, rubrique=None)`, `get_ytd_mensuel(entite_id, annee)` retournant des pandas DataFrame
- [ ] T005 Creer `hma-dashboard/app.py` : application Dash avec layout Bootstrap (`dbc.Container`), sidebar filtres (Structure dropdown, Exercice dropdown defaut 2026, Trimestre dropdown), zone contenu principale avec placeholders pour KPI/tableau/graphiques
- [ ] T006 Creer le callback principal dans `hma-dashboard/callbacks.py` : importer les callbacks depuis les modules composants, enregistrer avec l'app Dash

**Checkpoint**: App Dash demarre, filtres fonctionnels, donnees chargees depuis PostgreSQL HMA

---

## Phase 3: User Story 1 — KPI Cards avec evolution (Priority: P1)

**Goal**: Afficher les 5 indicateurs cles CRD avec evolution configurable

**Independent Test**: Ouvrir le dashboard, selectionner STIVMAT, verifier que les 5 KPI (CA, MCV, Res. exploit, Res. net, CAF) affichent les bons montants et le bon % du CA

- [ ] T007 [US1] Creer `hma-dashboard/components/kpi_cards.py` : fonction `create_kpi_card(title, value, pct_ca, delta_pct, delta_direction)` utilisant `go.Indicator` avec mode="number+delta", format euros, couleur conditionnelle vert/rouge
- [ ] T008 [US1] Creer le layout KPI dans `hma-dashboard/components/kpi_cards.py` : fonction `create_kpi_row()` retournant une `dbc.Row` de 5 `dbc.Col` (responsive : `lg=2, md=4, sm=6, xs=12`)
- [ ] T009 [US1] Ajouter le selecteur de periode de reference dans `hma-dashboard/app.py` : dropdown avec options "Trimestre precedent", "Exercice N-1", "Exercice N-2", "Mois precedent"
- [ ] T010 [US1] Ajouter la fonction `get_crd_reference(entite_id, annee, trimestre, ref_type)` dans `hma-dashboard/data.py` : requete `v_crd` pour la periode de reference selectionnee, calcul du delta (%) entre periode courante et reference
- [ ] T011 [US1] Creer le callback KPI dans `hma-dashboard/callbacks.py` : Input(filtre structure, exercice, trimestre, reference) → Output(5 KPI cards) — appelle `get_crd()` + `get_crd_reference()`, genere les 5 cards avec delta

**Checkpoint**: 5 KPI cards affichees avec montants, % CA, evolution (fleche + %) — mises a jour a chaque changement de filtre

---

## Phase 4: User Story 2 — Tableau CRD drilldown (Priority: P1)

**Goal**: Afficher le tableau CRD complet avec drilldown 3 niveaux (categorie → rubrique → compte PCG)

**Independent Test**: Cliquer sur "Charges variables" → les rubriques s'affichent, cliquer sur une rubrique → les comptes PCG apparaissent

- [ ] T012 [US2] Creer `hma-dashboard/components/crd_table.py` : fonction `create_crd_summary_table(df_crd)` retournant un tableau HTML (`dbc.Table`) avec 10 lignes CRD (CA, Charges var., MCV, Charges fixes, Res. exploit, Res. financier, RCAI, Res. exceptionnel, IS, Res. net) + CAF, colonnes montant + % CA + barre de progression CSS
- [ ] T013 [US2] Ajouter le drilldown niveau 1 dans `hma-dashboard/components/crd_table.py` : chaque ligne categorie est cliquable (`n_clicks`), callback affiche/masque les rubriques (`v_crd_drilldown` groupees par `crd_rubrique`) en dessous de la ligne cliquee
- [ ] T014 [US2] Ajouter le drilldown niveau 2 dans `hma-dashboard/components/crd_table.py` : chaque rubrique est cliquable, callback affiche les comptes PCG (`compte_numero`, `compte_libelle`, `montant`) en sous-lignes indentees
- [ ] T015 [US2] Ajouter la section seuil de rentabilite dans `hma-dashboard/components/crd_table.py` : sous le tableau CRD, afficher seuil de rentabilite (euros), point mort (jours), marge de securite (euros + %) depuis `v_crd`
- [ ] T016 [US2] Creer le callback drilldown dans `hma-dashboard/callbacks.py` : Input(filtre structure/exercice + clics lignes) → Output(tableau CRD avec lignes expandees) — gestion de l'etat ouvert/ferme via `dcc.Store`

**Checkpoint**: Tableau CRD complet avec drilldown fonctionnel sur 3 niveaux + seuil de rentabilite

---

## Phase 5: User Story 3 — Graphiques interactifs (Priority: P1)

**Goal**: Courbes d'evolution mensuelle, donut charges V/F, barres par rubrique — avec tooltips

**Independent Test**: Verifier que la courbe du CA mensuel STIVMAT 2025 correspond a `v_ytd_mensuel`, et que le donut charges montre la bonne repartition

- [ ] T017 [P] [US3] Creer `hma-dashboard/components/charts.py` : fonction `create_line_chart(df_ytd)` utilisant `px.line()` avec 3 series (CA, MCV, Resultat net) sur l'axe mois, tooltips avec montant + % evolution, format euros sur l'axe Y
- [ ] T018 [P] [US3] Ajouter la fonction `create_donut_chart(df_crd)` dans `hma-dashboard/components/charts.py` : `px.pie(hole=0.4)` avec 2 segments (charges variables, charges fixes), montants + % dans les labels, couleurs distinctes
- [ ] T019 [P] [US3] Ajouter la fonction `create_bar_chart(df_drilldown)` dans `hma-dashboard/components/charts.py` : `px.bar()` horizontal ou vertical avec les rubriques CRD, montants en euros, triees par montant decroissant
- [ ] T020 [US3] Creer le callback graphiques dans `hma-dashboard/callbacks.py` : Input(filtre structure/exercice/trimestre) → Output(3 graphiques) — appelle `get_ytd_mensuel()` et `get_crd_drilldown()`, genere les 3 figures Plotly
- [ ] T021 [US3] Ajouter l'interactivite donut : callback sur `clickData` du donut → filtre les barres par rubrique pour montrer uniquement les rubriques du segment clique (charges variables OU fixes)

**Checkpoint**: 3 graphiques interactifs avec tooltips, donut cliquable qui filtre les barres

---

## Phase 6: User Story 4 — Comparaison multi-structures (Priority: P2)

**Goal**: Comparer les KPI CRD de 2 a 4 structures cote a cote en barres groupees

**Independent Test**: Selectionner STIVMAT + ETPA, verifier que les barres groupees affichent les bons CA respectifs

- [ ] T022 [US4] Modifier le filtre Structure dans `hma-dashboard/app.py` : ajouter un toggle "Mode comparaison" qui passe le dropdown en multi-select
- [ ] T023 [US4] Ajouter la fonction `get_crd_multi(entite_ids, annee, trimestre=None)` dans `hma-dashboard/data.py` : requete `v_crd` pour plusieurs entites, retourne un DataFrame avec colonne `entite_nom`
- [ ] T024 [US4] Ajouter la fonction `create_comparison_chart(df_multi)` dans `hma-dashboard/components/charts.py` : `px.bar(barmode="group")` avec les 5 KPI en axe X, une barre par structure, couleurs par structure, tooltips avec montant + structure
- [ ] T025 [US4] Creer le callback comparaison dans `hma-dashboard/callbacks.py` : quand mode comparaison actif, remplacer les KPI cards et graphiques individuels par le graphique de comparaison groupee

**Checkpoint**: Mode comparaison fonctionnel avec barres groupees pour 2-4 structures

---

## Phase 7: User Story 5 — Export PDF (Priority: P3)

**Goal**: Exporter le dashboard visible en PDF

**Independent Test**: Cliquer sur "Exporter PDF", verifier que le fichier contient les KPI et graphiques visibles

- [ ] T026 [US5] Ajouter un bouton "Exporter PDF" dans `hma-dashboard/app.py` : `dbc.Button` dans la barre de titre
- [ ] T027 [US5] Creer le callback export dans `hma-dashboard/callbacks.py` : capture du contenu HTML visible, conversion en PDF via `weasyprint` ou `pdfkit`, telechargement via `dcc.Download`
- [ ] T028 [US5] Ajouter `weasyprint` (ou `pdfkit`) dans `hma-dashboard/requirements.txt`

**Checkpoint**: Export PDF fonctionnel avec KPI + tableau + graphiques

---

## Phase 8: Docker + Deploiement Coolify

**Purpose**: Conteneuriser et deployer sur le VPS

- [ ] T029 Creer `hma-dashboard/Dockerfile` : `FROM python:3.12-slim`, `pip install -r requirements.txt`, `CMD ["gunicorn", "app:server", "-b", "0.0.0.0:8050"]`
- [ ] T030 Creer `hma-dashboard/docker-compose.yml` : port 8050, env var `HMA_DB_URL`, reseau `coolify`, labels Traefik pour `dashboard.hma.business`
- [ ] T031 Deployer sur Coolify projet `hma-apps`, verifier l'acces via `https://dashboard.hma.business`

**Checkpoint**: Dashboard accessible en production via `dashboard.hma.business`

---

## Phase 9: Polish & Validation

**Purpose**: Tests finaux, responsive, documentation

- [ ] T032 [P] Tester avec Playwright : chargement < 5s, KPI cards visibles, drilldown fonctionnel, responsive 375px
- [ ] T033 [P] Mettre a jour `docs/services.md` avec le nouveau service Dashboard CRD
- [ ] T034 Ajuster le CSS responsive dans `hma-dashboard/assets/style.css` : KPI empilees verticalement sous 768px, tableau scrollable horizontalement sous 576px

**Checkpoint**: Dashboard valide, deploye, documente

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Pas de dependance — demarrage immediat
- **Phase 2 (Foundational)**: Depend de Phase 1 — BLOQUE toutes les user stories
- **Phase 3 (US1 - KPI)**: Depend de Phase 2
- **Phase 4 (US2 - Drilldown)**: Depend de Phase 2 — peut demarrer en parallele de Phase 3
- **Phase 5 (US3 - Graphiques)**: Depend de Phase 2 — peut demarrer en parallele de Phase 3-4
- **Phase 6 (US4 - Comparaison)**: Depend de Phase 2 + data.py de Phase 3
- **Phase 7 (US5 - Export)**: Depend de Phases 3-5 (besoin du contenu a exporter)
- **Phase 8 (Docker)**: Depend de Phase 2 minimum, idealement Phase 3-5
- **Phase 9 (Polish)**: Depend de Phases 3-8

### User Story Dependencies

- **US1 (KPI Cards)**: Independante apres Phase 2
- **US2 (Drilldown)**: Independante apres Phase 2
- **US3 (Graphiques)**: Independante apres Phase 2
- **US4 (Comparaison)**: Depend de `data.py` (Phase 2) + partage `charts.py` avec US3
- **US5 (Export)**: Depend de US1+US2+US3 (besoin du contenu visible)

### Parallel Opportunities

Phase 2 terminee → US1, US2, US3 peuvent demarrer en parallele :
- T007-T011 (KPI cards) en parallele de T012-T016 (drilldown) en parallele de T017-T021 (graphiques)

Phase 5 :
- T017, T018, T019 (3 fonctions charts) en parallele [P]

---

## Parallel Example: Phase 5 (Graphiques)

```
# Lancer en parallele (fichiers differents) :
T017: Fonction create_line_chart() dans components/charts.py
T018: Fonction create_donut_chart() dans components/charts.py
T019: Fonction create_bar_chart() dans components/charts.py

# Puis sequentiellement :
T020: Callback graphiques (depend de T017-T019)
T021: Interactivite donut → barres (depend de T020)
```

---

## Implementation Strategy

### MVP First (US1 — KPI Cards)

1. Phase 1 + Phase 2 → Squelette Dash + donnees
2. Phase 3 (T007-T011) → 5 KPI cards avec evolution
3. **STOP et VALIDER** : Comparer les montants avec `v_crd` dans pgAdmin
4. Deployer (Phase 8) → Dashboard minimal mais fonctionnel

### Incremental Delivery

1. Setup + Foundational → Connexion DB + layout
2. US1 (KPI cards) → Premier livrable visuel
3. US2 (Drilldown) → Valeur ajoutee principale
4. US3 (Graphiques) → Visualisation complete
5. US4 (Comparaison) → Pilotage groupe
6. US5 (Export) → Confort utilisateur
7. Docker + Polish → Production

---

## Notes

- Toutes les donnees sont en lecture seule — le dashboard ne modifie rien dans PostgreSQL
- Le callback principal enchaine : filtre → requete SQL → DataFrame → composant Plotly → rendu HTML
- Les requetes SQL utilisent des `%s` parametres (jamais de f-string) pour la securite
- `gunicorn` en production, `app.run_server(debug=True)` en dev
