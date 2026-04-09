-- ============================================
-- Vue materialisee: mv_resultat_differentiel (CRD)
-- Compte de Resultat Differentiel complet :
--   CA → MCV → Res. exploitation → RCAI → Res. net → CAF
--   + Pourcentages relatifs (% du CA)
--   + Seuil de rentabilite, point mort, marge securite
-- Charges V/F via nature_defaut de pcg_analytique
-- CAF methode additive depuis le resultat net
-- Ref: docs/compta_analytique.md section 5
-- ============================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_resultat_differentiel AS
WITH donnees AS (
    SELECT
        e.entite_id, e.exercice_id,
        -- CA = comptes 70x - 709x
        SUM(CASE WHEN p.numero ~ '^70[1-8]' OR p.numero LIKE '707%' OR p.numero ~ '^709'
            THEN e.credit - e.debit ELSE 0 END) AS ca,
        -- Charges variables
        SUM(CASE WHEN p.classe IN (6, 7) AND p.nature_defaut = 'variable'
            THEN e.debit - e.credit ELSE 0 END) AS charges_variables,
        -- Charges fixes exploitation (hors financier, exceptionnel, IS)
        SUM(CASE WHEN p.classe = 6 AND p.nature_defaut = 'fixe'
            AND p.numero NOT LIKE '66%' AND p.numero NOT LIKE '67%'
            AND p.numero NOT LIKE '695%' AND p.numero NOT LIKE '691%'
            THEN e.debit - e.credit ELSE 0 END) AS charges_fixes,
        -- Resultat financier = produits financiers (76) - charges financieres (66)
        SUM(CASE WHEN p.numero LIKE '76%' THEN e.credit - e.debit ELSE 0 END)
        - SUM(CASE WHEN p.numero LIKE '66%' THEN e.debit - e.credit ELSE 0 END) AS resultat_financier,
        -- Resultat exceptionnel = produits exceptionnels (77) - charges exceptionnelles (67)
        SUM(CASE WHEN p.numero LIKE '77%' THEN e.credit - e.debit ELSE 0 END)
        - SUM(CASE WHEN p.numero LIKE '67%' THEN e.debit - e.credit ELSE 0 END) AS resultat_exceptionnel,
        -- IS (695) + participation (691)
        SUM(CASE WHEN p.numero LIKE '695%' OR p.numero LIKE '691%'
            THEN e.debit - e.credit ELSE 0 END) AS impot_sur_societes,
        -- DAP (dotations amort/provisions - 681, 686, 687)
        SUM(CASE WHEN p.numero LIKE '681%' OR p.numero LIKE '686%' OR p.numero LIKE '687%'
            THEN e.debit - e.credit ELSE 0 END) AS dap,
        -- RAP (reprises amort/provisions - 781, 786, 787)
        SUM(CASE WHEN p.numero LIKE '781%' OR p.numero LIKE '786%' OR p.numero LIKE '787%'
            THEN e.credit - e.debit ELSE 0 END) AS rap,
        -- VCEAC (valeur comptable elements actif cedes - 675)
        SUM(CASE WHEN p.numero LIKE '675%' THEN e.debit - e.credit ELSE 0 END) AS vceac,
        -- PCEA (produits cessions elements actif - 775)
        SUM(CASE WHEN p.numero LIKE '775%' THEN e.credit - e.debit ELSE 0 END) AS pcea
    FROM fec_ecriture e
    JOIN pcg_analytique p ON p.numero = e.pcg_numero
    WHERE e.journal_code NOT IN ('AN', 'OD-AN', 'RAN') AND p.classe IN (6, 7)
    GROUP BY e.entite_id, e.exercice_id
),
calculs AS (
    SELECT *,
        ca - charges_variables AS mcv,
        (ca - charges_variables) - charges_fixes AS resultat_exploitation,
        (ca - charges_variables) - charges_fixes + resultat_financier AS rcai,
        (ca - charges_variables) - charges_fixes + resultat_financier
            + resultat_exceptionnel - impot_sur_societes AS resultat_net,
        (ca - charges_variables) - charges_fixes + resultat_financier
            + resultat_exceptionnel - impot_sur_societes
            + dap - rap + vceac - pcea AS caf
    FROM donnees
)
SELECT
    entite_id, exercice_id,
    -- Bloc 1 : CRD valeurs absolues
    ca,
    charges_variables,
    mcv,
    charges_fixes,
    resultat_exploitation,
    resultat_financier,
    rcai,
    resultat_exceptionnel,
    impot_sur_societes,
    resultat_net,
    -- Bloc 2 : CAF (methode additive)
    dap, rap, vceac, pcea,
    caf,
    -- Bloc 3 : Pourcentages relatifs (% du CA)
    CASE WHEN ca != 0 THEN ROUND(charges_variables / ca * 100, 1) ELSE 0 END AS pct_charges_var,
    CASE WHEN ca != 0 THEN ROUND(mcv / ca * 100, 1) ELSE 0 END AS pct_mcv,
    CASE WHEN ca != 0 THEN ROUND(charges_fixes / ca * 100, 1) ELSE 0 END AS pct_charges_fixes,
    CASE WHEN ca != 0 THEN ROUND(resultat_exploitation / ca * 100, 1) ELSE 0 END AS pct_res_exploit,
    CASE WHEN ca != 0 THEN ROUND(rcai / ca * 100, 1) ELSE 0 END AS pct_rcai,
    CASE WHEN ca != 0 THEN ROUND(resultat_net / ca * 100, 1) ELSE 0 END AS pct_res_net,
    CASE WHEN ca != 0 THEN ROUND(caf / ca * 100, 1) ELSE 0 END AS pct_caf,
    -- Bloc 4 : Seuil de rentabilite / Point mort
    CASE WHEN ca != 0 AND mcv != 0
        THEN ROUND(charges_fixes / (mcv / ca), 2) ELSE 0
    END AS seuil_rentabilite,
    CASE WHEN ca != 0 AND mcv != 0
        THEN ROUND((charges_fixes / (mcv / ca)) / ca * 365, 1) ELSE 0
    END AS point_mort_jours,
    CASE WHEN ca != 0 AND mcv != 0
        THEN ca - ROUND(charges_fixes / (mcv / ca), 2) ELSE 0
    END AS marge_securite,
    CASE WHEN ca != 0 AND mcv != 0
        THEN ROUND((ca - ROUND(charges_fixes / (mcv / ca), 2)) / ca * 100, 1) ELSE 0
    END AS pct_marge_securite
FROM calculs
WITH DATA;

-- Index UNIQUE pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_rd_pk
    ON mv_resultat_differentiel(entite_id, exercice_id);
