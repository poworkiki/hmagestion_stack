-- ============================================
-- Vue materialisee: mv_bilan
-- Actif/Passif structures (brut, amort, net)
-- Classes 1-5, incluant a-nouveaux
-- Ref: docs/compta_analytique.md section 3
-- ============================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_bilan AS
WITH balances AS (
    -- Toutes les ecritures classes 1-5 (y compris a-nouveaux)
    SELECT
        e.entite_id,
        e.exercice_id,
        e.pcg_numero,
        p.classe,
        p.bilan_section,
        p.bilan_poste,
        SUM(e.debit) AS total_debit,
        SUM(e.credit) AS total_credit,
        SUM(e.debit) - SUM(e.credit) AS solde
    FROM fec_ecriture e
    JOIN pcg_analytique p ON p.numero = e.pcg_numero
    WHERE p.classe BETWEEN 1 AND 5
      AND p.bilan_section IS NOT NULL
    GROUP BY e.entite_id, e.exercice_id, e.pcg_numero, p.classe, p.bilan_section, p.bilan_poste
)
SELECT
    entite_id,
    exercice_id,
    bilan_section,
    bilan_poste,
    -- Montant brut : comptes principaux (hors amortissements 28x et depreciations 29x, 39x, 49x, 59x)
    SUM(CASE
        WHEN pcg_numero NOT LIKE '28%'
         AND pcg_numero NOT LIKE '29%'
         AND pcg_numero NOT LIKE '39%'
         AND pcg_numero NOT LIKE '49%'
         AND pcg_numero NOT LIKE '59%'
        THEN CASE
            WHEN bilan_section LIKE 'actif%' THEN solde       -- Actif : debit - credit
            ELSE -solde                                         -- Passif : credit - debit
        END
        ELSE 0
    END) AS montant_brut,
    -- Amortissements et depreciations (comptes 28x, 29x, 39x, 49x, 59x)
    SUM(CASE
        WHEN pcg_numero LIKE '28%'
          OR pcg_numero LIKE '29%'
          OR pcg_numero LIKE '39%'
          OR pcg_numero LIKE '49%'
          OR pcg_numero LIKE '59%'
        THEN -solde  -- credit - debit (les amort sont crediteurs)
        ELSE 0
    END) AS amortissements,
    -- Net = brut - amortissements
    SUM(CASE
        WHEN bilan_section LIKE 'actif%' THEN solde
        ELSE -solde
    END) AS montant_net
FROM balances
GROUP BY entite_id, exercice_id, bilan_section, bilan_poste
WITH DATA;

-- Index UNIQUE pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_bilan_pk
    ON mv_bilan(entite_id, exercice_id, bilan_section, bilan_poste);

CREATE INDEX IF NOT EXISTS idx_mv_bilan_entite ON mv_bilan(entite_id);
CREATE INDEX IF NOT EXISTS idx_mv_bilan_section ON mv_bilan(bilan_section);
