-- ============================================
-- Vue materialisee: mv_sig
-- 9 Soldes Intermediaires de Gestion + CAF
-- Ref: docs/compta_analytique.md section 1
-- ============================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_sig AS
WITH soldes_par_compte AS (
    -- Solde par compte PCG, entite, exercice (hors a-nouveaux)
    SELECT
        e.entite_id,
        e.exercice_id,
        e.pcg_numero,
        p.sig_solde,
        p.sig_signe,
        p.classe,
        SUM(e.credit - e.debit) AS solde_crediteur  -- positif = crediteur
    FROM fec_ecriture e
    JOIN pcg_analytique p ON p.numero = e.pcg_numero
    WHERE p.sig_solde IS NOT NULL
      AND e.journal_code NOT IN ('AN', 'OD-AN', 'RAN')
    GROUP BY e.entite_id, e.exercice_id, e.pcg_numero, p.sig_solde, p.sig_signe, p.classe
),
sig_bruts AS (
    -- Agreger par solde SIG
    SELECT
        entite_id,
        exercice_id,
        sig_solde,
        -- sig_signe * solde_crediteur : +1 pour les produits, -1 pour les charges
        SUM(sig_signe * solde_crediteur) AS montant
    FROM soldes_par_compte
    GROUP BY entite_id, exercice_id, sig_solde
),
sig_cascade AS (
    -- Calcul en cascade des 9 soldes
    SELECT entite_id, exercice_id, 1 AS sig_rang, 'Marge commerciale' AS sig_solde,
        COALESCE((SELECT montant FROM sig_bruts b WHERE b.sig_solde = 'Marge commerciale' AND b.entite_id = e.entite_id AND b.exercice_id = e.exercice_id), 0) AS montant
    FROM (SELECT DISTINCT entite_id, exercice_id FROM sig_bruts) e

    UNION ALL

    SELECT entite_id, exercice_id, 2, 'Production de l''exercice',
        COALESCE((SELECT montant FROM sig_bruts b WHERE b.sig_solde = 'Production de l''exercice' AND b.entite_id = e.entite_id AND b.exercice_id = e.exercice_id), 0)
    FROM (SELECT DISTINCT entite_id, exercice_id FROM sig_bruts) e

    UNION ALL

    SELECT entite_id, exercice_id, 3, 'Valeur ajoutee',
        COALESCE((SELECT montant FROM sig_bruts b WHERE b.sig_solde = 'Valeur ajoutee' AND b.entite_id = e.entite_id AND b.exercice_id = e.exercice_id), 0)
    FROM (SELECT DISTINCT entite_id, exercice_id FROM sig_bruts) e

    UNION ALL

    SELECT entite_id, exercice_id, 4, 'EBE',
        COALESCE((SELECT montant FROM sig_bruts b WHERE b.sig_solde = 'EBE' AND b.entite_id = e.entite_id AND b.exercice_id = e.exercice_id), 0)
    FROM (SELECT DISTINCT entite_id, exercice_id FROM sig_bruts) e

    UNION ALL

    SELECT entite_id, exercice_id, 5, 'Resultat d''exploitation',
        COALESCE((SELECT montant FROM sig_bruts b WHERE b.sig_solde = 'Resultat d''exploitation' AND b.entite_id = e.entite_id AND b.exercice_id = e.exercice_id), 0)
    FROM (SELECT DISTINCT entite_id, exercice_id FROM sig_bruts) e

    UNION ALL

    SELECT entite_id, exercice_id, 6, 'RCAI',
        COALESCE((SELECT montant FROM sig_bruts b WHERE b.sig_solde = 'RCAI' AND b.entite_id = e.entite_id AND b.exercice_id = e.exercice_id), 0)
    FROM (SELECT DISTINCT entite_id, exercice_id FROM sig_bruts) e

    UNION ALL

    SELECT entite_id, exercice_id, 7, 'Resultat exceptionnel',
        COALESCE((SELECT montant FROM sig_bruts b WHERE b.sig_solde = 'Resultat exceptionnel' AND b.entite_id = e.entite_id AND b.exercice_id = e.exercice_id), 0)
    FROM (SELECT DISTINCT entite_id, exercice_id FROM sig_bruts) e

    UNION ALL

    SELECT entite_id, exercice_id, 8, 'Resultat de l''exercice',
        COALESCE((SELECT montant FROM sig_bruts b WHERE b.sig_solde = 'Resultat de l''exercice' AND b.entite_id = e.entite_id AND b.exercice_id = e.exercice_id), 0)
    FROM (SELECT DISTINCT entite_id, exercice_id FROM sig_bruts) e

    UNION ALL

    -- CAF methode additive : Resultat net + dotations - reprises + VCEAC - PCEA - quote-part sub
    SELECT entite_id, exercice_id, 9, 'CAF',
        COALESCE((SELECT montant FROM sig_bruts b WHERE b.sig_solde = 'CAF' AND b.entite_id = e.entite_id AND b.exercice_id = e.exercice_id), 0)
    FROM (SELECT DISTINCT entite_id, exercice_id FROM sig_bruts) e
)
SELECT
    entite_id,
    exercice_id,
    sig_rang,
    sig_solde,
    montant
FROM sig_cascade
WITH DATA;

-- Index UNIQUE pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_sig_pk
    ON mv_sig(entite_id, exercice_id, sig_rang);

CREATE INDEX IF NOT EXISTS idx_mv_sig_entite ON mv_sig(entite_id);
