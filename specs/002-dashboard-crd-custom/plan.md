# Implementation Plan: Dashboard CRD sur mesure

**Branch**: `002-dashboard-crd-custom` | **Date**: 2026-04-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-dashboard-crd-custom/spec.md`

## Summary

Creer un dashboard CRD (Compte de Resultat Differentiel) interactif sur mesure avec Dash (Plotly), connecte directement aux vues SQL PostgreSQL HMA. Le dashboard offre 5 KPI cards avec evolution configurable, un tableau CRD avec drilldown 3 niveaux, des graphiques interactifs (courbes, barres, donut), et une comparaison multi-structures — le tout deployable en Docker sur Coolify.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: Dash 2.x, Plotly, dash-bootstrap-components, psycopg2-binary, pandas, gunicorn
**Storage**: PostgreSQL HMA (lecture seule — vues existantes `v_crd`, `v_crd_drilldown`, `v_ytd_mensuel`)
**Testing**: pytest + Playwright (tests UI responsive)
**Target Platform**: Docker container sur VPS Hostinger (Coolify), navigateur desktop + mobile
**Project Type**: Application web dashboard (single-page, lecture seule)
**Performance Goals**: Chargement initial < 5s, changement de filtre < 3s
**Constraints**: Pas d'authentification MVP, reseau interne/VPN, donnees en lecture seule
**Scale/Scope**: 4 entites, 3-5 utilisateurs, ~25k ecritures, 3 vues SQL source

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v1.0.0 ratifiee le 2026-04-02. Verification des 5 principes :

- ✅ **I. Secrets-First** : `HMA_DB_URL` passe par variable d'environnement (Coolify), `.env` gitignored, aucun secret dans le code
- ✅ **II. SQL-Only Data Layer** : le dashboard consomme les vues SQL existantes (lecture seule), ne cree aucune table ni vue. La couche donnees du Chantier A reste 100% SQL.
- ✅ **III. Referentiel-Driven** : les vues `v_crd` et `v_crd_drilldown` sont derivees de `v_grand_livre` qui utilise `pcg_analytique` (source de verite). Le dashboard ne recalcule rien — il affiche les resultats des vues.
- ⏸️ **IV. 5 Agents Non-Negociable** : hors perimetre (dashboard ≠ agents)
- ✅ **V. French-Only** : interface en francais, labels en francais, documentation en francais

## Project Structure

### Documentation (this feature)

```text
specs/002-dashboard-crd-custom/
├── plan.md              # Ce fichier
├── research.md          # Choix techniques (Dash vs Streamlit vs NiceGUI)
├── data-model.md        # Vues SQL consommees + requetes prevues
├── quickstart.md        # Guide demarrage rapide
└── tasks.md             # Taches (genere par /speckit.tasks)
```

### Source Code (repository root)

```text
hma-dashboard/
├── app.py               # Point d'entree Dash + layout principal
├── callbacks.py         # Callbacks Dash (filtres → KPI + tableau + charts)
├── data.py              # Couche acces donnees (SQL → pandas DataFrame)
├── components/
│   ├── kpi_cards.py     # 5 KPI cards (go.Indicator) avec delta configurable
│   ├── crd_table.py     # Tableau CRD drilldown 3 niveaux
│   └── charts.py        # Graphiques (px.line, px.bar, px.pie/donut)
├── assets/
│   └── style.css        # CSS custom (couleurs, responsive overrides)
├── tests/
│   ├── test_data.py     # Tests couche donnees (mock DB)
│   └── test_layout.py   # Tests layout Dash
├── requirements.txt     # dash, dash-bootstrap-components, psycopg2-binary, pandas, gunicorn
├── Dockerfile           # python:3.12-slim + gunicorn
└── docker-compose.yml   # Port 8050, reseau coolify, env vars
```

**Structure Decision**: Projet standalone `hma-dashboard/` a la racine du repo, meme pattern que `hmagents/`. Separation claire : `data.py` (SQL), `callbacks.py` (logique reactive), `components/` (composants visuels). Pas de backend separe — Dash est le serveur.

## Phases d'implementation

### Phase 1 — Fondation : connexion DB + layout minimal

| Etape | Livrable | Depend de |
|---|---|---|
| Creer `hma-dashboard/` avec `requirements.txt` | Arborescence projet | — |
| Creer `data.py` : fonctions `get_crd()`, `get_crd_drilldown()`, `get_ytd_mensuel()` | Couche donnees | requirements.txt |
| Creer `app.py` : layout Dash Bootstrap (sidebar filtres + zone contenu) | Squelette UI | data.py |
| Ajouter filtres : Structure (dropdown), Exercice (dropdown, defaut 2026), Trimestre (dropdown) | Navigation de base | app.py |

### Phase 2 — KPI Cards + evolution

| Etape | Livrable | Depend de |
|---|---|---|
| Creer `components/kpi_cards.py` : 5 cards (CA, MCV, Res. exploit, Res. net, CAF) avec `go.Indicator` | KPI visuels | Phase 1 |
| Ajouter selecteur periode de reference (N-1, N-2, trimestre prec., mois prec.) | Filtre evolution | kpi_cards.py |
| Creer callback : filtre → requete `v_crd` → mise a jour 5 KPI cards avec delta | Interactivite | kpi_cards.py |
| Coloration conditionnelle (vert/rouge) + fleche haut/bas | UX | callback |

### Phase 3 — Tableau CRD drilldown

| Etape | Livrable | Depend de |
|---|---|---|
| Creer `components/crd_table.py` : tableau CRD complet (10 lignes : CA → CAF) avec montant + % CA + barre | Tableau statique | Phase 1 |
| Ajouter drilldown niveau 1 : clic categorie → affiche rubriques | Premier drill | crd_table.py |
| Ajouter drilldown niveau 2 : clic rubrique → affiche comptes PCG (numero + libelle + montant) | Drill complet | drill N1 |
| Ajouter section seuil de rentabilite, point mort, marge de securite | Indicateurs CRD | crd_table.py |

### Phase 4 — Graphiques interactifs

| Etape | Livrable | Depend de |
|---|---|---|
| Creer `components/charts.py` : courbe evolution mensuelle (`px.line`) CA + MCV + Res. net | Courbe temporelle | Phase 1 |
| Ajouter donut charges V/F (`px.pie` hole=0.4) | Donut repartition | data.py |
| Ajouter barres par rubrique CRD (`px.bar`) | Detail rubriques | data.py |
| Ajouter tooltips interactifs (montant, %, mois) sur tous les graphiques | UX complete | charts.py |

### Phase 5 — Comparaison + responsive + export

| Etape | Livrable | Depend de |
|---|---|---|
| Ajouter mode comparaison multi-structures (barres groupees) | US4 | Phase 4 |
| CSS responsive mobile (KPI empilees, tableau scrollable) | Mobile | Phase 2-4 |
| Export PDF (capture HTML → PDF) | US5 | Phase 2-4 |

### Phase 6 — Docker + deploiement Coolify

| Etape | Livrable | Depend de |
|---|---|---|
| Creer `Dockerfile` (python:3.12-slim + gunicorn) | Image Docker | Phase 1-5 |
| Creer `docker-compose.yml` (port 8050, reseau coolify, env vars) | Compose | Dockerfile |
| Deployer sur Coolify projet `hma-apps`, domaine `dashboard.hma.business` | Production | docker-compose |
| Tests Playwright (KPI, drilldown, responsive 375px) | Validation | deploiement |

## Requirements couverts par phase

| Phase | Requirements | User Stories |
|---|---|---|
| Phase 1 | FR-011, FR-012, FR-013 | — (fondation) |
| Phase 2 | FR-001, FR-002, FR-003 | US1 |
| Phase 3 | FR-004, FR-005, FR-006 | US2 |
| Phase 4 | FR-007, FR-008, FR-009, FR-010 | US3 |
| Phase 5 | FR-014, FR-015 | US4, US5 |
| Phase 6 | FR-016 | — (deploiement) |

## Complexity Tracking

Aucune violation de constitution a justifier.
