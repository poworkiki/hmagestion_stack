# Quickstart: Chantier A — Socle de données financières

## Prérequis

- Accès SSH au VPS HMA (187.124.150.82)
- PostgreSQL HMA standalone opérationnel (credentials dans Vaultwarden)
- n8n opérationnel (n8n.hma.business)
- Tokens Pennylane dans Vaultwarden (4 structures)

## Ordre d'exécution

### 1. Schéma SQL (sur PostgreSQL HMA)

Exécuter les fichiers SQL dans l'ordre numérique via `psql` :

```bash
# Se connecter à PostgreSQL HMA standalone
psql $HMA_DB_URL

# Exécuter dans l'ordre
\i sql/01-schema/001-entite.sql
\i sql/01-schema/002-exercice.sql
\i sql/01-schema/003-pcg-analytique.sql
\i sql/01-schema/004-compte-resolution.sql
\i sql/01-schema/005-fec-import.sql
\i sql/01-schema/006-fec-ecriture.sql

# Charger les données de référence
\i sql/02-data/001-pcg-analytique-seed.sql

# Fonctions
\i sql/04-functions/resolve-compte.sql
\i sql/04-functions/refresh-views.sql

# Vues matérialisées
\i sql/03-views/001-mv-balance-generale.sql
\i sql/03-views/002-mv-bilan.sql
\i sql/03-views/003-mv-bilan-fonctionnel.sql
\i sql/03-views/004-mv-compte-resultat.sql
\i sql/03-views/005-mv-resultat-differentiel.sql
\i sql/03-views/006-mv-sig.sql
\i sql/03-views/007-v-controles-coherence.sql
```

### 2. Workflow n8n

1. Importer `n8n/workflow-sync-pennylane.json` dans n8n
2. Configurer les credentials Pennylane (4 tokens depuis Vaultwarden)
3. Configurer la connexion PostgreSQL HMA
4. Exécuter manuellement une première fois sur une structure (ex: HMA)
5. Vérifier dans PostgreSQL que les écritures sont insérées
6. Activer le trigger automatique (cron ou webhook)

### 3. Validation

```sql
-- Vérifier les imports
SELECT * FROM fec_import ORDER BY date_import DESC LIMIT 10;

-- Compter les écritures par entité
SELECT e.code, COUNT(*) FROM fec_ecriture f
JOIN entite e ON e.id = f.entite_id
GROUP BY e.code;

-- Vérifier la cohérence
SELECT * FROM v_controles_coherence;

-- Vérifier les SIG
SELECT * FROM mv_sig WHERE entite_id = (SELECT id FROM entite WHERE code = 'HMA');

-- Croiser avec Pennylane trial_balance
-- Comparer les soldes mv_balance_generale avec /trial_balance de l'API
```

## Structure des fichiers

```
sql/
├── 01-schema/   → Tables (exécuter en premier)
├── 02-data/     → Données de référence (seed PCG)
├── 03-views/    → Vues matérialisées
└── 04-functions/ → Fonctions SQL

n8n/
└── workflow-sync-pennylane.json
```
