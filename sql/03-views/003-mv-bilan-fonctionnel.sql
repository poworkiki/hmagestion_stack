-- ============================================
-- Vue materialisee: mv_bilan_fonctionnel
-- FRNG, BFR exploitation, BFR hors exploitation, TN
-- En VALEURS BRUTES (amort reclasses en ressources stables)
-- Ref: docs/compta_analytique.md section 4
-- ============================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_bilan_fonctionnel AS
WITH balances_brutes AS (
    SELECT
        e.entite_id,
        e.exercice_id,
        e.pcg_numero,
        p.bf_categorie,
        p.classe,
        SUM(e.debit) - SUM(e.credit) AS solde
    FROM fec_ecriture e
    JOIN pcg_analytique p ON p.numero = e.pcg_numero
    WHERE p.bf_categorie IS NOT NULL
    GROUP BY e.entite_id, e.exercice_id, e.pcg_numero, p.bf_categorie, p.classe
),
-- Les amortissements et depreciations sont reclasses en ressources stables
amort_reclasses AS (
    SELECT
        e.entite_id,
        e.exercice_id,
        'ressources_stables' AS bf_categorie,
        -- Amort/deprec : credit - debit (positif = ressource)
        SUM(e.credit - e.debit) AS montant
    FROM fec_ecriture e
    JOIN pcg_analytique p ON p.numero = e.pcg_numero
    WHERE p.numero LIKE '28%'
       OR p.numero LIKE '29%'
       OR p.numero LIKE '39%'
       OR p.numero LIKE '49%'
       OR p.numero LIKE '59%'
    GROUP BY e.entite_id, e.exercice_id
),
categories AS (
    -- Emplois et actifs circulants en valeurs brutes
    SELECT
        entite_id,
        exercice_id,
        bf_categorie,
        SUM(CASE
            WHEN bf_categorie IN ('emplois_stables', 'bfr_exploit', 'bfr_hors_exploit', 'tresorerie_active')
            THEN solde      -- debit - credit pour l'actif
            ELSE -solde     -- credit - debit pour le passif
        END) AS montant
    FROM balances_brutes
    WHERE bf_categorie NOT IN ('amort_deprec')  -- amort traites separement
    GROUP BY entite_id, exercice_id, bf_categorie

    UNION ALL

    -- Amortissements reclasses en ressources stables
    SELECT entite_id, exercice_id, bf_categorie, montant
    FROM amort_reclasses
)
SELECT
    entite_id,
    exercice_id,
    bf_categorie,
    SUM(montant) AS montant
FROM categories
GROUP BY entite_id, exercice_id, bf_categorie
WITH DATA;

-- Index UNIQUE pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_bf_pk
    ON mv_bilan_fonctionnel(entite_id, exercice_id, bf_categorie);

CREATE INDEX IF NOT EXISTS idx_mv_bf_entite ON mv_bilan_fonctionnel(entite_id);
