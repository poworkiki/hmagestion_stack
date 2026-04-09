-- ============================================
-- REFACTORING v2 : Toutes les vues depuis le Grand Livre
-- Source unique : fec_ecriture + pcg_analytique + dim_calendrier
-- Date : 2026-04-08
-- ============================================

-- ============================================
-- 0. NETTOYAGE
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

DROP MATERIALIZED VIEW IF EXISTS mv_sig CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_compte_resultat CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_bilan CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_bilan_fonctionnel CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_resultat_differentiel CASCADE;


-- ============================================
-- 1. GRAND LIVRE (v_grand_livre)
-- Source unique — JOIN calendrier + PCG
-- ============================================

CREATE VIEW v_grand_livre AS
SELECT
    e.id AS ecriture_id,
    e.entite_id,
    e.exercice_id,
    ent.nom AS entite_nom,
    ex.label AS exercice_label,
    -- Calendrier (depuis dim_calendrier)
    e.ecriture_date,
    cal.annee,
    cal.trimestre,
    cal.mois,
    cal.mois_label,
    cal.mois_nom,
    cal.semaine,
    cal.debut_mois,
    -- Ecriture
    e.journal_code,
    e.journal_lib,
    e.ecriture_num,
    e.pcg_numero AS compte_numero,
    COALESCE(p.libelle, e.compte_lib) AS compte_libelle,
    COALESCE(p.classe, CAST(LEFT(e.pcg_numero, 1) AS smallint)) AS classe,
    e.comp_aux_num,
    e.comp_aux_lib,
    e.piece_ref,
    e.piece_date,
    e.ecriture_lib,
    e.debit,
    e.credit,
    e.debit - e.credit AS solde,
    e.ecriture_let,
    e.date_let,
    -- Mapping PCG analytique
    p.sig_solde,
    p.sig_signe,
    p.cr_rubrique,
    p.cr_signe,
    p.bilan_poste,
    p.bilan_section,
    p.bf_categorie,
    p.nature_defaut,
    p.crd_ordre,
    p.crd_categorie,
    p.crd_rubrique,
    p.crd_signe,
    -- Flag a-nouveaux
    CASE WHEN e.journal_code IN ('AN', 'OD-AN', 'RAN') THEN true ELSE false END AS is_a_nouveau
FROM fec_ecriture e
JOIN entite ent ON ent.id = e.entite_id
JOIN exercice ex ON ex.id = e.exercice_id
JOIN dim_calendrier cal ON cal.date_jour = e.ecriture_date
LEFT JOIN pcg_analytique p ON p.numero = e.pcg_numero;


-- ============================================
-- 2. BALANCE (v_balance)
-- Solde par compte / entite / mois
-- ============================================

CREATE VIEW v_balance AS
SELECT
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label, debut_mois,
    compte_numero, compte_libelle, classe,
    sig_solde, sig_signe, cr_rubrique, cr_signe,
    bilan_poste, bilan_section, bf_categorie, nature_defaut,
    SUM(debit) AS total_debit,
    SUM(credit) AS total_credit,
    SUM(solde) AS solde
FROM v_grand_livre
WHERE compte_numero IS NOT NULL
GROUP BY
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label, debut_mois,
    compte_numero, compte_libelle, classe,
    sig_solde, sig_signe, cr_rubrique, cr_signe,
    bilan_poste, bilan_section, bf_categorie, nature_defaut;


-- ============================================
-- 3. SIG (v_sig) — par mois, drilldown-ready
-- ============================================

CREATE VIEW v_sig AS
SELECT
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label,
    sig_solde,
    SUM(sig_signe * (credit - debit)) AS montant
FROM v_grand_livre
WHERE sig_solde IS NOT NULL AND NOT is_a_nouveau
GROUP BY entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label, sig_solde;


-- ============================================
-- 4. SIG DRILLDOWN (v_sig_drilldown)
-- Detail par compte dans chaque solde SIG
-- ============================================

CREATE VIEW v_sig_drilldown AS
SELECT
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label,
    sig_solde, sig_signe,
    compte_numero, compte_libelle,
    SUM(sig_signe * (credit - debit)) AS montant
FROM v_grand_livre
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
FROM v_grand_livre
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
FROM v_grand_livre
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
    FROM v_grand_livre
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
    FROM v_grand_livre
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
        -- CA : utilise crd_categorie (mapping PCG)
        SUM(CASE WHEN crd_categorie = 'Chiffre d''affaires'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS ca,
        -- Charges variables : crd_categorie (exclut le CA)
        SUM(CASE WHEN crd_categorie = 'Charges variables'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS charges_variables,
        -- Charges fixes exploitation
        SUM(CASE WHEN crd_categorie = 'Charges fixes exploitation'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS charges_fixes,
        -- Resultat financier
        SUM(CASE WHEN crd_categorie = 'Resultat financier'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS resultat_financier,
        -- Resultat exceptionnel
        SUM(CASE WHEN crd_categorie = 'Resultat exceptionnel'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS resultat_exceptionnel,
        -- IS
        SUM(CASE WHEN crd_categorie = 'Impot sur les societes'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS impot_sur_societes,
        -- CAF composantes
        SUM(CASE WHEN crd_categorie = 'CAF - Dotations'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS dap,
        SUM(CASE WHEN crd_categorie = 'CAF - Reprises'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS rap,
        SUM(CASE WHEN crd_categorie = 'CAF - Cessions' AND crd_rubrique = 'VCEAC'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS vceac,
        SUM(CASE WHEN crd_categorie = 'CAF - Cessions' AND crd_rubrique = 'PCEA'
            THEN crd_signe * (credit - debit) ELSE 0 END) AS pcea
    FROM v_grand_livre
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
-- Dynamique : drill par rubrique → compte
-- ============================================

CREATE VIEW v_crd_drilldown AS
SELECT
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label,
    crd_ordre,
    crd_categorie,
    crd_rubrique,
    crd_signe,
    compte_numero, compte_libelle, nature_defaut,
    SUM(crd_signe * (credit - debit)) AS montant
FROM v_grand_livre
WHERE crd_categorie IS NOT NULL AND NOT is_a_nouveau
  AND crd_ordre <= 6  -- Jusqu'au resultat net (exclut CAF composantes)
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
FROM v_grand_livre
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
-- FIN REFACTORING v2
-- Architecture : dim_calendrier + fec_ecriture + pcg_analytique
--   → v_grand_livre (source unique)
--     → v_balance, v_sig, v_crd, v_bilan, etc.
-- Toutes les vues sont dynamiques, drilldown-ready
-- ============================================
