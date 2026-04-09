-- ============================================
-- Vues de base comptables
-- Grand Livre, Journal, Balance Auxiliaire, Balance Agee
-- Ces vues servent de fondation a tous les etats financiers
-- ============================================

-- ============================================
-- 1. GRAND LIVRE (v_grand_livre)
-- Toutes les ecritures par compte, triees chronologiquement
-- avec solde progressif par compte
-- ============================================

CREATE OR REPLACE VIEW v_grand_livre AS
SELECT
    e.id AS ecriture_id,
    ent.nom AS entite_nom,
    ex.label AS exercice_label,
    e.ecriture_date,
    EXTRACT(YEAR FROM e.ecriture_date)::int AS annee,
    TO_CHAR(e.ecriture_date, 'MM - Mon') AS mois_label,
    CASE
        WHEN EXTRACT(MONTH FROM e.ecriture_date) <= 3 THEN 'T1'
        WHEN EXTRACT(MONTH FROM e.ecriture_date) <= 6 THEN 'T2'
        WHEN EXTRACT(MONTH FROM e.ecriture_date) <= 9 THEN 'T3'
        ELSE 'T4'
    END AS trimestre,
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
    e.debit - e.credit AS mouvement,
    -- Solde progressif par compte, entite, exercice
    SUM(e.debit - e.credit) OVER (
        PARTITION BY e.entite_id, e.exercice_id, e.pcg_numero
        ORDER BY e.ecriture_date, e.ecriture_num
        ROWS UNBOUNDED PRECEDING
    ) AS solde_progressif,
    e.ecriture_let,
    e.date_let,
    -- Mapping PCG analytique
    p.sig_solde,
    p.cr_rubrique,
    p.bilan_poste,
    p.bilan_section,
    p.nature_defaut,
    e.entite_id,
    e.exercice_id
FROM fec_ecriture e
JOIN entite ent ON ent.id = e.entite_id
JOIN exercice ex ON ex.id = e.exercice_id
LEFT JOIN pcg_analytique p ON p.numero = e.pcg_numero
ORDER BY e.entite_id, e.pcg_numero, e.ecriture_date, e.ecriture_num;

-- ============================================
-- 2. JOURNAL CENTRALISATEUR (v_journal)
-- Ecritures groupees par journal comptable
-- Totaux debit/credit par journal et par mois
-- ============================================

CREATE OR REPLACE VIEW v_journal AS
SELECT
    ent.nom AS entite_nom,
    ex.label AS exercice_label,
    e.journal_code,
    e.journal_lib,
    EXTRACT(YEAR FROM e.ecriture_date)::int AS annee,
    TO_CHAR(e.ecriture_date, 'MM - Mon') AS mois_label,
    DATE_TRUNC('month', e.ecriture_date)::date AS mois,
    COUNT(*) AS nb_ecritures,
    SUM(e.debit) AS total_debit,
    SUM(e.credit) AS total_credit,
    SUM(e.debit) - SUM(e.credit) AS solde,
    e.entite_id,
    e.exercice_id
FROM fec_ecriture e
JOIN entite ent ON ent.id = e.entite_id
JOIN exercice ex ON ex.id = e.exercice_id
GROUP BY ent.nom, ex.label, e.journal_code, e.journal_lib,
    e.ecriture_date, e.entite_id, e.exercice_id
ORDER BY e.journal_code, e.ecriture_date;

-- Correction: grouper par mois, pas par date
DROP VIEW IF EXISTS v_journal;
CREATE VIEW v_journal AS
SELECT
    ent.nom AS entite_nom,
    ex.label AS exercice_label,
    e.journal_code,
    e.journal_lib,
    EXTRACT(YEAR FROM e.ecriture_date)::int AS annee,
    TO_CHAR(DATE_TRUNC('month', e.ecriture_date), 'MM - Mon') AS mois_label,
    DATE_TRUNC('month', e.ecriture_date)::date AS mois,
    COUNT(*) AS nb_ecritures,
    SUM(e.debit) AS total_debit,
    SUM(e.credit) AS total_credit,
    SUM(e.debit) - SUM(e.credit) AS solde,
    e.entite_id,
    e.exercice_id
FROM fec_ecriture e
JOIN entite ent ON ent.id = e.entite_id
JOIN exercice ex ON ex.id = e.exercice_id
GROUP BY ent.nom, ex.label, e.journal_code, e.journal_lib,
    DATE_TRUNC('month', e.ecriture_date), e.entite_id, e.exercice_id
ORDER BY e.journal_code, DATE_TRUNC('month', e.ecriture_date);

-- ============================================
-- 3. BALANCE AUXILIAIRE (v_balance_auxiliaire)
-- Detail des comptes tiers (401 fournisseurs, 411 clients)
-- Solde par tiers
-- ============================================

DROP VIEW IF EXISTS v_balance_auxiliaire CASCADE;
CREATE VIEW v_balance_auxiliaire AS
SELECT
    ent.nom AS entite_nom,
    ex.label AS exercice_label,
    e.pcg_numero AS compte_numero,
    COALESCE(p.libelle, e.compte_lib) AS compte_libelle,
    CASE
        WHEN e.pcg_numero LIKE '401%' THEN 'Fournisseur'
        WHEN e.pcg_numero LIKE '411%' THEN 'Client'
        WHEN e.pcg_numero LIKE '421%' THEN 'Personnel'
        WHEN e.pcg_numero LIKE '43%'  THEN 'Organismes sociaux'
        WHEN e.pcg_numero LIKE '44%'  THEN 'Etat et collectivites'
        ELSE 'Autre tiers'
    END AS type_tiers,
    e.comp_aux_num AS tiers_numero,
    COALESCE(e.comp_aux_lib, 'Sans auxiliaire') AS tiers_nom,
    COUNT(*) AS nb_ecritures,
    SUM(e.debit) AS total_debit,
    SUM(e.credit) AS total_credit,
    SUM(e.debit) - SUM(e.credit) AS solde,
    SUM(CASE WHEN e.ecriture_let IS NULL OR e.ecriture_let = '' THEN e.debit ELSE 0 END) AS debit_non_lettre,
    SUM(CASE WHEN e.ecriture_let IS NULL OR e.ecriture_let = '' THEN e.credit ELSE 0 END) AS credit_non_lettre,
    SUM(CASE WHEN e.ecriture_let IS NULL OR e.ecriture_let = ''
        THEN e.debit - e.credit ELSE 0 END) AS solde_non_lettre,
    e.entite_id,
    e.exercice_id
FROM fec_ecriture e
JOIN entite ent ON ent.id = e.entite_id
JOIN exercice ex ON ex.id = e.exercice_id
LEFT JOIN pcg_analytique p ON p.numero = e.pcg_numero
WHERE e.pcg_numero LIKE '40%'
   OR e.pcg_numero LIKE '41%'
   OR e.pcg_numero LIKE '42%'
   OR e.pcg_numero LIKE '43%'
   OR e.pcg_numero LIKE '44%'
GROUP BY ent.nom, ex.label, e.pcg_numero, p.libelle, e.compte_lib,
    e.comp_aux_num, e.comp_aux_lib, e.entite_id, e.exercice_id
HAVING SUM(e.debit) != 0 OR SUM(e.credit) != 0
ORDER BY e.pcg_numero, e.comp_aux_num;

-- ============================================
-- 4. BALANCE AGEE (v_balance_agee)
-- Creances clients (411) et dettes fournisseurs (401)
-- ventilees par anciennete
-- ============================================

CREATE OR REPLACE VIEW v_balance_agee AS
WITH ecritures_ouvertes AS (
    SELECT
        e.entite_id,
        ent.nom AS entite_nom,
        e.exercice_id,
        ex.label AS exercice_label,
        e.pcg_numero AS compte_numero,
        CASE
            WHEN e.pcg_numero LIKE '401%' THEN 'Fournisseur'
            WHEN e.pcg_numero LIKE '411%' THEN 'Client'
            ELSE 'Autre'
        END AS type_tiers,
        e.comp_aux_num AS tiers_numero,
        COALESCE(e.comp_aux_lib, e.compte_lib) AS tiers_nom,
        e.ecriture_date,
        e.debit - e.credit AS montant,
        -- Anciennete en jours par rapport a aujourd'hui
        CURRENT_DATE - e.ecriture_date AS anciennete_jours,
        -- Tranche d'anciennete
        CASE
            WHEN CURRENT_DATE - e.ecriture_date <= 30 THEN '01. 0-30 jours'
            WHEN CURRENT_DATE - e.ecriture_date <= 60 THEN '02. 31-60 jours'
            WHEN CURRENT_DATE - e.ecriture_date <= 90 THEN '03. 61-90 jours'
            WHEN CURRENT_DATE - e.ecriture_date <= 180 THEN '04. 91-180 jours'
            ELSE '05. > 180 jours'
        END AS tranche_age
    FROM fec_ecriture e
    JOIN entite ent ON ent.id = e.entite_id
    JOIN exercice ex ON ex.id = e.exercice_id
    WHERE (e.pcg_numero LIKE '401%' OR e.pcg_numero LIKE '411%')
      -- Ecritures non lettrees uniquement (= ouvertes)
      AND (e.ecriture_let IS NULL OR e.ecriture_let = '')
)
SELECT
    entite_id, entite_nom, exercice_label,
    type_tiers,
    tiers_numero,
    tiers_nom,
    compte_numero,
    tranche_age,
    COUNT(*) AS nb_ecritures,
    SUM(montant) AS montant,
    MIN(ecriture_date) AS date_plus_ancienne,
    MAX(anciennete_jours) AS anciennete_max_jours
FROM ecritures_ouvertes
GROUP BY entite_id, entite_nom, exercice_label,
    type_tiers, tiers_numero, tiers_nom, compte_numero, tranche_age
HAVING SUM(montant) != 0
ORDER BY type_tiers, tranche_age DESC, ABS(SUM(montant)) DESC;
