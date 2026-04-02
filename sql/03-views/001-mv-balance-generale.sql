-- ============================================
-- Vue materialisee: mv_balance_generale
-- Soldes par compte PCG, entite, exercice et mois
-- Ref: docs/compta_analytique.md
-- ============================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_balance_generale AS
SELECT
    e.entite_id,
    e.exercice_id,
    e.pcg_numero,
    p.libelle AS pcg_libelle,
    p.classe,
    date_trunc('month', e.ecriture_date)::date AS mois,
    SUM(e.debit) AS total_debit,
    SUM(e.credit) AS total_credit,
    SUM(e.debit) - SUM(e.credit) AS solde
FROM fec_ecriture e
JOIN pcg_analytique p ON p.numero = e.pcg_numero
WHERE e.pcg_numero IS NOT NULL
  -- Exclure les a-nouveaux pour les comptes de classe 6 et 7 (charges/produits)
  AND NOT (p.classe IN (6, 7) AND e.journal_code IN ('AN', 'OD-AN', 'RAN'))
GROUP BY
    e.entite_id,
    e.exercice_id,
    e.pcg_numero,
    p.libelle,
    p.classe,
    date_trunc('month', e.ecriture_date)::date
WITH DATA;

-- Index UNIQUE requis pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_balance_pk
    ON mv_balance_generale(entite_id, exercice_id, pcg_numero, mois);

-- Index supplementaires pour les requetes
CREATE INDEX IF NOT EXISTS idx_mv_balance_entite ON mv_balance_generale(entite_id);
CREATE INDEX IF NOT EXISTS idx_mv_balance_classe ON mv_balance_generale(classe);
