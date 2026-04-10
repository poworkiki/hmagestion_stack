-- ============================================
-- VUES BALANCE CLIENTS + FOURNISSEURS
-- Vues dediees pour le suivi tiers
-- Source : grand_livre (table denormalisee)
-- Date : 2026-04-10
-- ============================================

DROP VIEW IF EXISTS v_balance_clients CASCADE;
DROP VIEW IF EXISTS v_balance_fournisseurs CASCADE;


-- ============================================
-- 1. BALANCE CLIENTS (comptes 411xxx)
-- Solde par client, avec detail lettre/non lettre
-- + anciennete de la creance la plus ancienne
-- ============================================

CREATE VIEW v_balance_clients AS
SELECT
    entite_code,
    entite_nom,
    exercice_label,
    annee,
    compte_numero,
    compte_libelle,
    comp_aux_num AS client_numero,
    COALESCE(comp_aux_lib, compte_libelle) AS client_nom,
    COUNT(*) AS nb_ecritures,
    SUM(debit) AS total_debit,
    SUM(credit) AS total_credit,
    SUM(solde) AS solde,
    -- Detail lettre / non lettre
    SUM(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN debit ELSE 0 END) AS debit_non_lettre,
    SUM(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN credit ELSE 0 END) AS credit_non_lettre,
    SUM(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN solde ELSE 0 END) AS solde_non_lettre,
    -- Anciennete
    MIN(ecriture_date) AS date_plus_ancienne,
    MAX(ecriture_date) AS date_plus_recente,
    CURRENT_DATE - MIN(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN ecriture_date END) AS anciennete_max_jours,
    -- Tranche
    CASE
        WHEN CURRENT_DATE - MIN(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN ecriture_date END) IS NULL THEN 'Solde'
        WHEN CURRENT_DATE - MIN(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN ecriture_date END) <= 30 THEN '0-30j'
        WHEN CURRENT_DATE - MIN(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN ecriture_date END) <= 60 THEN '31-60j'
        WHEN CURRENT_DATE - MIN(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN ecriture_date END) <= 90 THEN '61-90j'
        WHEN CURRENT_DATE - MIN(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN ecriture_date END) <= 180 THEN '91-180j'
        ELSE '> 180j'
    END AS tranche_anciennete
FROM grand_livre
WHERE compte_numero LIKE '411%'
GROUP BY entite_code, entite_nom, exercice_label, annee,
    compte_numero, compte_libelle, comp_aux_num, comp_aux_lib
HAVING SUM(debit) != 0 OR SUM(credit) != 0
ORDER BY entite_code, ABS(SUM(solde)) DESC;

COMMENT ON VIEW v_balance_clients IS 'Balance Clients (411xxx) — solde par client, detail lettre/non lettre, anciennete';


-- ============================================
-- 2. BALANCE FOURNISSEURS (comptes 401xxx)
-- Solde par fournisseur, avec detail lettre/non lettre
-- + anciennete de la dette la plus ancienne
-- ============================================

CREATE VIEW v_balance_fournisseurs AS
SELECT
    entite_code,
    entite_nom,
    exercice_label,
    annee,
    compte_numero,
    compte_libelle,
    comp_aux_num AS fournisseur_numero,
    COALESCE(comp_aux_lib, compte_libelle) AS fournisseur_nom,
    COUNT(*) AS nb_ecritures,
    SUM(debit) AS total_debit,
    SUM(credit) AS total_credit,
    SUM(solde) AS solde,
    -- Detail lettre / non lettre
    SUM(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN debit ELSE 0 END) AS debit_non_lettre,
    SUM(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN credit ELSE 0 END) AS credit_non_lettre,
    SUM(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN solde ELSE 0 END) AS solde_non_lettre,
    -- Anciennete
    MIN(ecriture_date) AS date_plus_ancienne,
    MAX(ecriture_date) AS date_plus_recente,
    CURRENT_DATE - MIN(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN ecriture_date END) AS anciennete_max_jours,
    -- Tranche
    CASE
        WHEN CURRENT_DATE - MIN(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN ecriture_date END) IS NULL THEN 'Solde'
        WHEN CURRENT_DATE - MIN(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN ecriture_date END) <= 30 THEN '0-30j'
        WHEN CURRENT_DATE - MIN(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN ecriture_date END) <= 60 THEN '31-60j'
        WHEN CURRENT_DATE - MIN(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN ecriture_date END) <= 90 THEN '61-90j'
        WHEN CURRENT_DATE - MIN(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN ecriture_date END) <= 180 THEN '91-180j'
        ELSE '> 180j'
    END AS tranche_anciennete
FROM grand_livre
WHERE compte_numero LIKE '401%'
GROUP BY entite_code, entite_nom, exercice_label, annee,
    compte_numero, compte_libelle, comp_aux_num, comp_aux_lib
HAVING SUM(debit) != 0 OR SUM(credit) != 0
ORDER BY entite_code, ABS(SUM(solde)) DESC;

COMMENT ON VIEW v_balance_fournisseurs IS 'Balance Fournisseurs (401xxx) — solde par fournisseur, detail lettre/non lettre, anciennete';
