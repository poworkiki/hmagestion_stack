-- ============================================
-- Vue materialisee: mv_resultat_differentiel
-- MCV, taux MCV, seuil de rentabilite, point mort
-- Charges V/F via nature_defaut de pcg_analytique
-- Ref: docs/compta_analytique.md section 5
-- ============================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_resultat_differentiel AS
WITH donnees AS (
    SELECT
        e.entite_id,
        e.exercice_id,
        -- CA = comptes 70x - 709x (credit - debit)
        SUM(CASE
            WHEN p.numero ~ '^70[1-8]' OR p.numero LIKE '707%'
            THEN e.credit - e.debit
            WHEN p.numero ~ '^709'
            THEN e.credit - e.debit  -- RRR : negatif naturellement
            ELSE 0
        END) AS ca,
        -- Charges variables
        SUM(CASE
            WHEN p.classe IN (6, 7) AND p.nature_defaut = 'variable'
            THEN e.debit - e.credit
            ELSE 0
        END) AS charges_variables,
        -- Charges fixes
        SUM(CASE
            WHEN p.classe IN (6, 7) AND p.nature_defaut = 'fixe'
            THEN e.debit - e.credit
            ELSE 0
        END) AS charges_fixes
    FROM fec_ecriture e
    JOIN pcg_analytique p ON p.numero = e.pcg_numero
    WHERE e.journal_code NOT IN ('AN', 'OD-AN', 'RAN')
      AND p.classe IN (6, 7)
    GROUP BY e.entite_id, e.exercice_id
)
SELECT
    entite_id,
    exercice_id,
    ca,
    charges_variables,
    charges_fixes,
    -- MCV = CA - charges variables
    ca - charges_variables AS mcv,
    -- Taux de MCV = MCV / CA
    CASE WHEN ca != 0
        THEN ROUND((ca - charges_variables) / ca, 4)
        ELSE 0
    END AS taux_mcv,
    -- Seuil de rentabilite = charges fixes / taux MCV
    CASE WHEN ca != 0 AND (ca - charges_variables) != 0
        THEN ROUND(charges_fixes / ((ca - charges_variables) / ca), 2)
        ELSE 0
    END AS seuil_rentabilite,
    -- Point mort en jours = (seuil de rentabilite / CA) x 365
    CASE WHEN ca != 0 AND (ca - charges_variables) != 0
        THEN ROUND((charges_fixes / ((ca - charges_variables) / ca)) / ca * 365, 1)
        ELSE 0
    END AS point_mort_jours,
    -- Marge de securite = CA - seuil de rentabilite
    CASE WHEN ca != 0 AND (ca - charges_variables) != 0
        THEN ca - ROUND(charges_fixes / ((ca - charges_variables) / ca), 2)
        ELSE 0
    END AS marge_securite
FROM donnees
WITH DATA;

-- Index UNIQUE pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_rd_pk
    ON mv_resultat_differentiel(entite_id, exercice_id);
