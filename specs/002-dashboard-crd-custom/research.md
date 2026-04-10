# Research: Dashboard CRD sur mesure

**Feature**: 002-dashboard-crd-custom
**Date**: 2026-04-10

## Decision 1 : Framework frontend

**Decision** : **Dash (Plotly)** + Dash Bootstrap Components

**Rationale** :
- Le drilldown a 3 niveaux (categorie → rubrique → compte PCG) se mappe directement sur les callbacks Dash avec `DataTable` et click events
- Les 5 KPI cards, courbes, barres, donut sont des composants Plotly natifs — pas de workaround
- Les filtres qui mettent a jour tous les composants simultanement correspondent exactement au pattern `@callback` avec multiples `Output`
- `dash-bootstrap-components` fournit une grille responsive Bootstrap 5 pour le mobile
- Docker : `python:3.12-slim` + `pip install dash dash-bootstrap-components psycopg2-binary` + `gunicorn` = production-ready

**Alternatives considerees** :

| Framework | Avantage | Raison du rejet |
|-----------|----------|-----------------|
| Streamlit | Plus simple pour un debutant | Pas de drilldown natif, click events limites, reflow single-column sur mobile |
| NiceGUI | Tailwind responsive, API moderne | Communaute plus petite, moins d'exemples financiers, ecosysteme moins mature |
| React + ECharts | Controle total UX | Necessite expertise JavaScript, courbe d'apprentissage trop forte pour le profil utilisateur |

## Decision 2 : Connexion PostgreSQL

**Decision** : `psycopg2-binary` avec connection pool

**Rationale** :
- Deja utilise dans le repo (`hmagents/requirements.txt`)
- Les vues SQL (`v_crd`, `v_crd_drilldown`, `v_ytd_mensuel`) sont pretes — pas besoin d'ORM
- Simple `SELECT * FROM v_crd WHERE entite_id = %s AND annee = %s` suffit

**Alternatives considerees** :

| Option | Raison du rejet |
|--------|-----------------|
| SQLAlchemy | Surcharge pour des SELECT simples sur des vues existantes |
| asyncpg | Dash est synchrone (Flask), pas besoin d'async |

## Decision 3 : Deploiement

**Decision** : Docker container standalone, Coolify projet `hma-apps`

**Rationale** :
- Meme pattern que les autres services (hmagents, n8n, Superset)
- Gunicorn comme serveur WSGI (production-grade)
- Traefik reverse-proxy sur `dashboard.hma.business`
- Reseau Docker `coolify` pour acceder a PostgreSQL HMA

## Decision 4 : Chartage et graphiques

**Decision** : Plotly Express + Plotly Graph Objects

**Rationale** :
- Plotly est natif dans Dash — zero config supplementaire
- `px.line()` pour les courbes, `px.bar()` pour les barres, `px.pie()` pour les donuts
- Tooltips interactifs inclus par defaut
- `go.Indicator()` pour les KPI cards avec delta/fleche
