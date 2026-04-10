# Quickstart: Dashboard CRD sur mesure

## Prerequis

- Python 3.11+
- Acces a PostgreSQL HMA (`HMA_DB_URL` dans `.env`)
- Docker (pour deploiement Coolify)

## Installation locale

```bash
cd hma-dashboard
python3 -m venv .venv
source .venv/bin/activate   # ou .venv\Scripts\activate sur Windows
pip install -r requirements.txt
```

## Lancer en developpement

```bash
# Charger la connexion DB
export HMA_DB_URL=$(grep '^HMA_DB_URL=' ../.env | cut -d= -f2-)

# Lancer Dash en mode debug
python app.py
# → http://localhost:8050
```

## Lancer en production (Docker)

```bash
cd hma-dashboard
docker compose up -d
# → http://localhost:8050
# → Via Coolify : https://dashboard.hma.business
```

## Structure du projet

```
hma-dashboard/
├── app.py               # Point d'entree Dash + layout
├── callbacks.py          # Callbacks Dash (filtres, drilldown, charts)
├── data.py               # Couche acces donnees (SQL → DataFrame)
├── components/
│   ├── kpi_cards.py      # 5 KPI cards avec delta
│   ├── crd_table.py      # Tableau CRD drilldown
│   └── charts.py         # Courbes, barres, donut
├── assets/
│   └── style.css         # CSS custom
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Tester

```bash
# Verifier la connexion DB
python -c "from data import get_crd; print(get_crd(1, 2026))"

# Lancer les tests
pytest tests/
```
