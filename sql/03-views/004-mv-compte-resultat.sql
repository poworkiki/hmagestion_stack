-- ============================================
-- Vue materialisee: mv_compte_resultat
-- Produits et charges par rubrique CR
-- Classes 6-7, hors a-nouveaux
-- Ref: docs/compta_analytique.md section 2
-- ============================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_compte_resultat AS
SELECT
    e.entite_id,
    e.exercice_id,
    p.cr_rubrique,
    p.cr_signe,
    -- Montant : credit - debit pour les produits (cr_signe = +1)
    --           debit - credit pour les charges (cr_signe = -1)
    -- On normalise : montant positif = contribution positive au resultat
    SUM(e.credit - e.debit) * p.cr_signe AS montant
FROM fec_ecriture e
JOIN pcg_analytique p ON p.numero = e.pcg_numero
WHERE p.classe IN (6, 7)
  AND p.cr_rubrique IS NOT NULL
  -- Exclure les a-nouveaux
  AND e.journal_code NOT IN ('AN', 'OD-AN', 'RAN')
GROUP BY e.entite_id, e.exercice_id, p.cr_rubrique, p.cr_signe
WITH DATA;

-- Index UNIQUE pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_cr_pk
    ON mv_compte_resultat(entite_id, exercice_id, cr_rubrique);

CREATE INDEX IF NOT EXISTS idx_mv_cr_entite ON mv_compte_resultat(entite_id);
