-- ============================================
-- REFACTORING v3 : Toutes les vues depuis la TABLE grand_livre
-- Source unique : grand_livre (dénormalisée, pré-jointée)
-- Plus besoin de JOIN pcg_analytique ni dim_calendrier à chaque requête
-- Date : 2026-04-09
-- ============================================

-- ============================================
-- 0. NETTOYAGE anciennes vues
-- ============================================
DROP VIEW IF EXISTS v_resultat_differentiel CASCADE;
DROP VIEW IF EXISTS v_balance_generale CASCADE;
DROP VIEW IF EXISTS v_ytd_mensuel CASCADE;
DROP VIEW IF EXISTS v_ytd_trimestriel CASCADE;
DROP VIEW IF EXISTS v_ytd_annuel CASCADE;
DROP VIEW IF EXISTS v_sig_drilldown CASCADE;
DROP VIEW IF EXISTS v_crd_drilldown CASCADE;
DROP VIEW IF EXISTS v_sig CASCADE;
DROP VIEW IF EXISTS v_compte_resultat CASCADE;
DROP VIEW IF EXISTS v_bilan CASCADE;
DROP VIEW IF EXISTS v_bilan_fonctionnel CASCADE;
DROP VIEW IF EXISTS v_crd CASCADE;
DROP VIEW IF EXISTS v_balance CASCADE;
DROP VIEW IF EXISTS v_grand_livre CASCADE;

DROP MATERIALIZED VIEW IF EXISTS mv_balance_generale CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_sig CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_compte_resultat CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_bilan CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_bilan_fonctionnel CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_resultat_differentiel CASCADE;


-- ============================================
-- 1. GRAND LIVRE (v_grand_livre)
-- Simple alias vers la table grand_livre
-- ============================================

CREATE VIEW v_grand_livre AS
SELECT
    id AS ecriture_id,
    entite_id, exercice_id, entite_nom, exercice_label,
    ecriture_date, annee, trimestre, mois, mois_label, mois_nom, semaine, debut_mois,
    journal_code, journal_lib, ecriture_num,
    compte_numero, compte_libelle, classe,
    comp_aux_num, comp_aux_lib, piece_ref, piece_date, ecriture_lib,
    debit, credit, solde, ecriture_let, date_let,
    sig_solde, sig_signe, cr_rubrique, cr_signe,
    bilan_poste, bilan_section, bf_categorie, nature_defaut,
    crd_ordre, crd_categorie, crd_rubrique, crd_signe,
    is_a_nouveau
FROM grand_livre;


-- ============================================
-- 2. BALANCE (v_balance)
-- Alias vers la MV balance_generale
-- ============================================

CREATE VIEW v_balance AS
SELECT
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label, debut_mois,
    compte_numero, compte_libelle, classe,
    sig_solde, sig_signe, cr_rubrique, cr_signe,
    bilan_poste, bilan_section, bf_categorie, nature_defaut,
    total_debit, total_credit, solde
FROM balance_generale;


-- ============================================
-- 3. SIG (v_sig) — par mois, drilldown-ready
-- ============================================

CREATE VIEW v_sig AS
SELECT
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label,
    sig_solde,
    SUM(sig_signe * (credit - debit)) AS montant
FROM grand_livre
WHERE sig_solde IS NOT NULL AND NOT is_a_nouveau
GROUP BY entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label, sig_solde;


-- ============================================
-- 4. SIG DRILLDOWN (v_sig_drilldown)
-- ============================================

CREATE VIEW v_sig_drilldown AS
SELECT
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label,
    sig_solde, sig_signe,
    compte_numero, compte_libelle,
    SUM(sig_signe * (credit - debit)) AS montant
FROM grand_livre
WHERE sig_solde IS NOT NULL AND NOT is_a_nouveau
GROUP BY entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label,
    sig_solde, sig_signe, compte_numero, compte_libelle
HAVING SUM(sig_signe * (credit - debit)) != 0;


-- ============================================
-- 5. COMPTE DE RESULTAT (v_compte_resultat)
-- ============================================

CREATE VIEW v_compte_resultat AS
SELECT
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label,
    cr_rubrique, cr_signe,
    SUM(cr_signe * (credit - debit)) AS montant
FROM grand_livre
WHERE cr_rubrique IS NOT NULL AND classe IN (6, 7) AND NOT is_a_nouveau
GROUP BY entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label, cr_rubrique, cr_signe;


-- ============================================
-- 6. BILAN (v_bilan)
-- ============================================

CREATE VIEW v_bilan AS
SELECT
    entite_id, entite_nom, exercice_id, exercice_label, annee,
    bilan_section, bilan_poste,
    SUM(CASE
        WHEN compte_numero NOT LIKE '28%' AND compte_numero NOT LIKE '29%'
         AND compte_numero NOT LIKE '39%' AND compte_numero NOT LIKE '49%'
         AND compte_numero NOT LIKE '59%'
        THEN CASE WHEN bilan_section LIKE 'actif%' THEN debit - credit ELSE credit - debit END
        ELSE 0
    END) AS montant_brut,
    SUM(CASE
        WHEN compte_numero LIKE '28%' OR compte_numero LIKE '29%'
          OR compte_numero LIKE '39%' OR compte_numero LIKE '49%'
          OR compte_numero LIKE '59%'
        THEN credit - debit ELSE 0
    END) AS amortissements,
    SUM(CASE
        WHEN bilan_section LIKE 'actif%' THEN debit - credit ELSE credit - debit
    END) AS montant_net
FROM grand_livre
WHERE bilan_section IS NOT NULL AND classe BETWEEN 1 AND 5
GROUP BY entite_id, entite_nom, exercice_id, exercice_label, annee,
    bilan_section, bilan_poste;


-- ============================================
-- 7. BILAN FONCTIONNEL (v_bilan_fonctionnel)
-- ============================================

CREATE VIEW v_bilan_fonctionnel AS
WITH brut AS (
    SELECT entite_id, entite_nom, exercice_id, exercice_label, annee, bf_categorie,
        SUM(CASE
            WHEN bf_categorie IN ('emplois_stables','bfr_exploit','bfr_hors_exploit','tresorerie_active')
            THEN debit - credit ELSE credit - debit
        END) AS montant
    FROM grand_livre
    WHERE bf_categorie IS NOT NULL
      AND compte_numero NOT LIKE '28%' AND compte_numero NOT LIKE '29%'
      AND compte_numero NOT LIKE '39%' AND compte_numero NOT LIKE '49%'
      AND compte_numero NOT LIKE '59%'
    GROUP BY entite_id, entite_nom, exercice_id, exercice_label, annee, bf_categorie
),
amort AS (
    SELECT entite_id, entite_nom, exercice_id, exercice_label, annee,
        'ressources_stables' AS bf_categorie,
        SUM(credit - debit) AS montant
    FROM grand_livre
    WHERE compte_numero LIKE '28%' OR compte_numero LIKE '29%'
       OR compte_numero LIKE '39%' OR compte_numero LIKE '49%'
       OR compte_numero LIKE '59%'
    GROUP BY entite_id, entite_nom, exercice_id, exercice_label, annee
)
SELECT entite_id, entite_nom, exercice_id, exercice_label, annee,
    bf_categorie, SUM(montant) AS montant
FROM (SELECT * FROM brut UNION ALL SELECT * FROM amort) combined
GROUP BY entite_id, entite_nom, exercice_id, exercice_label, annee, bf_categorie;


-- ============================================
-- 8. CRD (v_crd) — par trimestre
-- ============================================

CREATE VIEW v_crd AS
WITH donnees AS (
    SELECT
        entite_id, entite_nom, exercice_id, exercice_label, annee, trimestre,
        SUM(CASE WHEN crd_categorie = 'Chiffre d''affaires'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS ca,
        SUM(CASE WHEN crd_categorie = 'Charges variables'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS charges_variables,
        SUM(CASE WHEN crd_categorie = 'Charges fixes exploitation'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS charges_fixes,
        SUM(CASE WHEN crd_categorie = 'Resultat financier'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS resultat_financier,
        SUM(CASE WHEN crd_categorie = 'Resultat exceptionnel'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS resultat_exceptionnel,
        SUM(CASE WHEN crd_categorie = 'Impot sur les societes'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS impot_sur_societes,
        SUM(CASE WHEN crd_categorie = 'CAF - Dotations'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS dap,
        SUM(CASE WHEN crd_categorie = 'CAF - Reprises'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS rap,
        SUM(CASE WHEN crd_categorie = 'CAF - Cessions' AND crd_rubrique = 'VCEAC'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS vceac,
        SUM(CASE WHEN crd_categorie = 'CAF - Cessions' AND crd_rubrique = 'PCEA'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS pcea
    FROM grand_livre
    WHERE NOT is_a_nouveau AND crd_categorie IS NOT NULL
    GROUP BY entite_id, entite_nom, exercice_id, exercice_label, annee, trimestre
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
    entite_id, entite_nom, exercice_id, exercice_label, annee, trimestre,
    ca, charges_variables, mcv, charges_fixes,
    resultat_exploitation, resultat_financier, rcai,
    resultat_exceptionnel, impot_sur_societes, resultat_net,
    dap, rap, vceac, pcea, caf,
    CASE WHEN ca != 0 THEN ROUND(charges_variables/ca*100,1) ELSE 0 END AS pct_charges_var,
    CASE WHEN ca != 0 THEN ROUND(mcv/ca*100,1) ELSE 0 END AS pct_mcv,
    CASE WHEN ca != 0 THEN ROUND(charges_fixes/ca*100,1) ELSE 0 END AS pct_charges_fixes,
    CASE WHEN ca != 0 THEN ROUND(resultat_exploitation/ca*100,1) ELSE 0 END AS pct_res_exploit,
    CASE WHEN ca != 0 THEN ROUND(rcai/ca*100,1) ELSE 0 END AS pct_rcai,
    CASE WHEN ca != 0 THEN ROUND(resultat_net/ca*100,1) ELSE 0 END AS pct_res_net,
    CASE WHEN ca != 0 THEN ROUND(caf/ca*100,1) ELSE 0 END AS pct_caf,
    CASE WHEN ca!=0 AND mcv!=0 THEN ROUND(charges_fixes/(mcv/ca),2) ELSE 0 END AS seuil_rentabilite,
    CASE WHEN ca!=0 AND mcv!=0 THEN ROUND((charges_fixes/(mcv/ca))/ca*365,1) ELSE 0 END AS point_mort_jours,
    CASE WHEN ca!=0 AND mcv!=0 THEN ca - ROUND(charges_fixes/(mcv/ca),2) ELSE 0 END AS marge_securite,
    CASE WHEN ca!=0 AND mcv!=0 THEN ROUND((ca-ROUND(charges_fixes/(mcv/ca),2))/ca*100,1) ELSE 0 END AS pct_marge_securite
FROM calculs;


-- ============================================
-- 9. CRD DRILLDOWN (v_crd_drilldown)
-- ============================================

CREATE VIEW v_crd_drilldown AS
SELECT
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label,
    crd_ordre, crd_categorie, crd_rubrique, crd_signe,
    compte_numero, compte_libelle, nature_defaut,
    SUM(crd_signe * (credit - debit)) AS montant
FROM grand_livre
WHERE crd_categorie IS NOT NULL AND NOT is_a_nouveau
  AND crd_ordre <= 6
GROUP BY entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label,
    crd_ordre, crd_categorie, crd_rubrique, crd_signe,
    compte_numero, compte_libelle, nature_defaut
HAVING SUM(crd_signe * (credit - debit)) != 0;


-- ============================================
-- 10. YTD mensuel / trimestriel / annuel
-- ============================================

CREATE VIEW v_ytd_mensuel AS
SELECT
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, mois, mois_label, trimestre, debut_mois,
    SUM(CASE WHEN compte_numero ~ '^70' THEN credit - debit ELSE 0 END) AS ca,
    SUM(CASE WHEN classe = 6 THEN debit - credit ELSE 0 END) AS charges,
    SUM(CASE WHEN classe = 7 THEN credit - debit ELSE 0 END) AS produits,
    SUM(CASE WHEN classe = 7 THEN credit - debit ELSE 0 END)
        - SUM(CASE WHEN classe = 6 THEN debit - credit ELSE 0 END) AS resultat
FROM grand_livre
WHERE classe IN (6, 7) AND NOT is_a_nouveau
GROUP BY entite_id, entite_nom, exercice_id, exercice_label,
    annee, mois, mois_label, trimestre, debut_mois;

CREATE VIEW v_ytd_trimestriel AS
SELECT entite_id, entite_nom, exercice_id, exercice_label, annee, trimestre,
    SUM(ca) AS ca, SUM(charges) AS charges, SUM(produits) AS produits, SUM(resultat) AS resultat
FROM v_ytd_mensuel
GROUP BY entite_id, entite_nom, exercice_id, exercice_label, annee, trimestre;

CREATE VIEW v_ytd_annuel AS
SELECT entite_id, entite_nom, exercice_id, exercice_label, annee,
    SUM(ca) AS ca, SUM(charges) AS charges, SUM(produits) AS produits, SUM(resultat) AS resultat
FROM v_ytd_mensuel
GROUP BY entite_id, entite_nom, exercice_id, exercice_label, annee;


-- ============================================
-- 11. ALIAS COMPATIBILITE
-- ============================================

CREATE OR REPLACE VIEW v_resultat_differentiel AS SELECT * FROM v_crd;
CREATE OR REPLACE VIEW v_balance_generale AS SELECT * FROM v_balance;


-- ============================================
-- 12. REFRESH FUNCTION (mise à jour)
-- ============================================

CREATE OR REPLACE FUNCTION refresh_all_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY balance_generale;
END;
$$ LANGUAGE plpgsql;


-- ============================================
-- FIN REFACTORING v3
-- Architecture : grand_livre (TABLE dénormalisée)
--   → v_grand_livre (alias), balance_generale (MV)
--     → v_balance (alias MV), v_sig, v_crd, v_bilan, etc.
-- Plus de JOIN à chaque requête = performances optimales
-- ============================================
