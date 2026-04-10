-- ============================================
-- MIGRATION 002 : Simplification du schema
-- Objectif : tout derive de grand_livre, fec_ecriture = archive FEC legale
-- Date : 2026-04-10
-- ============================================

BEGIN;

-- ============================================
-- 1. AJOUT entite_code dans grand_livre
-- ============================================

ALTER TABLE grand_livre ADD COLUMN IF NOT EXISTS entite_code TEXT;

UPDATE grand_livre gl
SET entite_code = e.code
FROM entite e
WHERE gl.entite_id = e.id
  AND gl.entite_code IS NULL;

-- Index pour les filtres par code structure
CREATE INDEX IF NOT EXISTS idx_gl_entite_code ON grand_livre (entite_code);

COMMENT ON COLUMN grand_livre.entite_code IS 'Code structure (HMA, STIVMAT, STA, ETPA) — denormalise depuis entite';


-- ============================================
-- 2. CONTROLES DE COHERENCE (ex 007)
--    Source : grand_livre au lieu de fec_ecriture
-- ============================================

-- Drop les anciennes vues (dependances inversees)
DROP VIEW IF EXISTS v_controles_coherence CASCADE;
DROP VIEW IF EXISTS v_ctrl_equilibre CASCADE;
DROP VIEW IF EXISTS v_ctrl_doublons CASCADE;
DROP VIEW IF EXISTS v_ctrl_comptes_non_resolus CASCADE;

-- Controle 1 : Equilibre debit/credit par ecriture
CREATE VIEW v_ctrl_equilibre AS
SELECT
    entite_id,
    entite_code,
    exercice_id,
    ecriture_num,
    ecriture_date,
    SUM(debit) AS total_debit,
    SUM(credit) AS total_credit,
    ABS(SUM(debit) - SUM(credit)) AS ecart
FROM grand_livre
GROUP BY entite_id, entite_code, exercice_id, ecriture_num, ecriture_date
HAVING ABS(SUM(debit) - SUM(credit)) > 0.01;

-- Controle 2 : Doublons (pennylane_line_id est la cle de dedup dans grand_livre)
CREATE VIEW v_ctrl_doublons AS
SELECT
    entite_id,
    pennylane_line_id,
    COUNT(*) AS nb_occurrences
FROM grand_livre
GROUP BY entite_id, pennylane_line_id
HAVING COUNT(*) > 1;

-- Controle 3 : Comptes non resolus (compte_numero NULL)
CREATE VIEW v_ctrl_comptes_non_resolus AS
SELECT
    entite_id,
    entite_code,
    compte_numero,
    compte_libelle,
    COUNT(*) AS nb_ecritures,
    SUM(debit) AS total_debit,
    SUM(credit) AS total_credit
FROM grand_livre
WHERE compte_numero IS NULL OR classe IS NULL
GROUP BY entite_id, entite_code, compte_numero, compte_libelle
ORDER BY nb_ecritures DESC;

-- Vue synthetique regroupant tous les controles
CREATE VIEW v_controles_coherence AS
SELECT
    'equilibre_d_c' AS controle,
    (SELECT COUNT(*) FROM v_ctrl_equilibre) AS nb_anomalies,
    CASE WHEN (SELECT COUNT(*) FROM v_ctrl_equilibre) = 0
        THEN 'OK' ELSE 'ALERTE'
    END AS statut

UNION ALL

SELECT
    'doublons_pennylane_id' AS controle,
    (SELECT COUNT(*) FROM v_ctrl_doublons) AS nb_anomalies,
    CASE WHEN (SELECT COUNT(*) FROM v_ctrl_doublons) = 0
        THEN 'OK' ELSE 'ALERTE'
    END AS statut

UNION ALL

SELECT
    'comptes_non_resolus' AS controle,
    (SELECT COUNT(*) FROM v_ctrl_comptes_non_resolus) AS nb_anomalies,
    CASE WHEN (SELECT COUNT(*) FROM v_ctrl_comptes_non_resolus) = 0
        THEN 'OK' ELSE 'ALERTE'
    END AS statut;


-- ============================================
-- 3. VUES DE BASE COMPTABLES (ex 009)
--    Source : grand_livre au lieu de fec_ecriture
--    (v_grand_livre deja reecrite dans 011, on ne touche pas)
-- ============================================

-- Journal centralisateur
DROP VIEW IF EXISTS v_journal CASCADE;
CREATE VIEW v_journal AS
SELECT
    entite_code,
    entite_nom,
    exercice_label,
    journal_code,
    journal_lib,
    annee,
    mois,
    mois_label,
    trimestre,
    debut_mois,
    COUNT(*) AS nb_ecritures,
    SUM(debit) AS total_debit,
    SUM(credit) AS total_credit,
    SUM(solde) AS solde,
    entite_id,
    exercice_id
FROM grand_livre
GROUP BY entite_code, entite_nom, exercice_label,
    journal_code, journal_lib, annee, mois, mois_label, trimestre, debut_mois,
    entite_id, exercice_id
ORDER BY journal_code, annee, mois;

-- Balance auxiliaire (tiers : 401, 411, 42x, 43x, 44x)
DROP VIEW IF EXISTS v_balance_auxiliaire CASCADE;
CREATE VIEW v_balance_auxiliaire AS
SELECT
    entite_code,
    entite_nom,
    exercice_label,
    compte_numero,
    compte_libelle,
    CASE
        WHEN compte_numero LIKE '401%' THEN 'Fournisseur'
        WHEN compte_numero LIKE '411%' THEN 'Client'
        WHEN compte_numero LIKE '421%' THEN 'Personnel'
        WHEN compte_numero LIKE '43%'  THEN 'Organismes sociaux'
        WHEN compte_numero LIKE '44%'  THEN 'Etat et collectivites'
        ELSE 'Autre tiers'
    END AS type_tiers,
    comp_aux_num AS tiers_numero,
    COALESCE(comp_aux_lib, 'Sans auxiliaire') AS tiers_nom,
    COUNT(*) AS nb_ecritures,
    SUM(debit) AS total_debit,
    SUM(credit) AS total_credit,
    SUM(solde) AS solde,
    SUM(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN debit ELSE 0 END) AS debit_non_lettre,
    SUM(CASE WHEN ecriture_let IS NULL OR ecriture_let = '' THEN credit ELSE 0 END) AS credit_non_lettre,
    SUM(CASE WHEN ecriture_let IS NULL OR ecriture_let = ''
        THEN solde ELSE 0 END) AS solde_non_lettre,
    entite_id,
    exercice_id
FROM grand_livre
WHERE compte_numero LIKE '40%'
   OR compte_numero LIKE '41%'
   OR compte_numero LIKE '42%'
   OR compte_numero LIKE '43%'
   OR compte_numero LIKE '44%'
GROUP BY entite_code, entite_nom, exercice_label,
    compte_numero, compte_libelle,
    comp_aux_num, comp_aux_lib, entite_id, exercice_id
HAVING SUM(debit) != 0 OR SUM(credit) != 0
ORDER BY compte_numero, comp_aux_num;

-- Balance agee (creances/dettes par anciennete)
DROP VIEW IF EXISTS v_balance_agee CASCADE;
CREATE VIEW v_balance_agee AS
WITH ecritures_ouvertes AS (
    SELECT
        entite_id,
        entite_code,
        entite_nom,
        exercice_id,
        exercice_label,
        compte_numero,
        CASE
            WHEN compte_numero LIKE '401%' THEN 'Fournisseur'
            WHEN compte_numero LIKE '411%' THEN 'Client'
            ELSE 'Autre'
        END AS type_tiers,
        comp_aux_num AS tiers_numero,
        COALESCE(comp_aux_lib, compte_libelle) AS tiers_nom,
        ecriture_date,
        solde AS montant,
        CURRENT_DATE - ecriture_date AS anciennete_jours,
        CASE
            WHEN CURRENT_DATE - ecriture_date <= 30 THEN '01. 0-30 jours'
            WHEN CURRENT_DATE - ecriture_date <= 60 THEN '02. 31-60 jours'
            WHEN CURRENT_DATE - ecriture_date <= 90 THEN '03. 61-90 jours'
            WHEN CURRENT_DATE - ecriture_date <= 180 THEN '04. 91-180 jours'
            ELSE '05. > 180 jours'
        END AS tranche_age
    FROM grand_livre
    WHERE (compte_numero LIKE '401%' OR compte_numero LIKE '411%')
      AND (ecriture_let IS NULL OR ecriture_let = '')
)
SELECT
    entite_id, entite_code, entite_nom, exercice_label,
    type_tiers, tiers_numero, tiers_nom, compte_numero,
    tranche_age,
    COUNT(*) AS nb_ecritures,
    SUM(montant) AS montant,
    MIN(ecriture_date) AS date_plus_ancienne,
    MAX(anciennete_jours) AS anciennete_max_jours
FROM ecritures_ouvertes
GROUP BY entite_id, entite_code, entite_nom, exercice_label,
    type_tiers, tiers_numero, tiers_nom, compte_numero, tranche_age
HAVING SUM(montant) != 0
ORDER BY type_tiers, tranche_age DESC, ABS(SUM(montant)) DESC;


-- ============================================
-- 4. FIX v_bg_display : filtrer a-nouveaux classes 6-7
-- ============================================

DROP VIEW IF EXISTS v_bg_display CASCADE;
CREATE VIEW v_bg_display AS
SELECT
    entite_nom,
    annee,
    classe,
    compte_numero,
    compte_libelle,
    SUM(total_debit) AS total_debit,
    SUM(total_credit) AS total_credit,
    GREATEST(SUM(total_debit) - SUM(total_credit), 0) AS solde_debiteur,
    GREATEST(SUM(total_credit) - SUM(total_debit), 0) AS solde_crediteur,
    SUM(total_debit) - SUM(total_credit) AS solde,
    sig_solde,
    cr_rubrique,
    bilan_poste,
    bilan_section,
    crd_categorie
FROM balance_generale
GROUP BY
    entite_nom, annee, classe,
    compte_numero, compte_libelle,
    sig_solde, cr_rubrique, bilan_poste, bilan_section, crd_categorie;

COMMENT ON VIEW v_bg_display IS 'Balance Generale annuelle — solde debiteur/crediteur separes, 1 ligne par compte/annee';


-- ============================================
-- 5. FIX v_gl_display : pennylane_line_id comme tiebreaker
-- ============================================

DROP VIEW IF EXISTS v_gl_display CASCADE;
CREATE VIEW v_gl_display AS
SELECT
    entite_code,
    entite_nom,
    annee,
    trimestre,
    mois,
    mois_label,
    ecriture_date,
    journal_code,
    journal_lib,
    ecriture_num,
    compte_numero,
    compte_libelle,
    classe,
    ecriture_lib,
    debit,
    credit,
    solde,
    -- Solde cumule progressif par compte (pennylane_line_id = ordre deterministe)
    SUM(solde) OVER (
        PARTITION BY entite_id, annee, compte_numero
        ORDER BY ecriture_date, pennylane_line_id
    ) AS solde_cumule,
    piece_ref,
    comp_aux_num,
    ecriture_let,
    is_a_nouveau,
    CASE WHEN is_a_nouveau THEN 'A-nouveau' ELSE 'Exercice' END AS type_ecriture
FROM grand_livre;

COMMENT ON VIEW v_gl_display IS 'Grand Livre avec solde cumule progressif par compte (ordre deterministe)';


-- ============================================
-- 6. FIX v_gl_bg_combined : ajouter entite_code
-- ============================================

DROP VIEW IF EXISTS v_gl_bg_combined CASCADE;
CREATE VIEW v_gl_bg_combined AS
SELECT
    g.entite_code,
    g.entite_nom,
    g.annee,
    g.trimestre,
    g.mois,
    g.mois_label,
    g.ecriture_date,
    g.journal_code,
    g.ecriture_num,
    g.compte_numero,
    g.compte_libelle,
    g.classe,
    g.ecriture_lib,
    g.debit,
    g.credit,
    g.solde,
    g.piece_ref,
    g.is_a_nouveau,
    CASE WHEN g.is_a_nouveau THEN 'A-nouveau' ELSE 'Exercice' END AS type_ecriture,
    g.sig_solde,
    g.cr_rubrique,
    g.bilan_poste,
    g.bilan_section,
    g.crd_categorie,
    g.compte_numero || ' — ' || g.compte_libelle AS compte_display
FROM grand_livre g;

COMMENT ON VIEW v_gl_bg_combined IS 'GL+BG combine — source unique pour Drill By dans Superset';


-- ============================================
-- 7. DEGRAISSAGE fec_ecriture
--    Garder la table (obligation FEC legale) mais supprimer les index inutiles
-- ============================================

DROP INDEX IF EXISTS idx_fec_entite_exercice;
DROP INDEX IF EXISTS idx_fec_compte;
DROP INDEX IF EXISTS idx_fec_pcg_numero;
DROP INDEX IF EXISTS idx_fec_date;
DROP INDEX IF EXISTS idx_fec_hash;

-- Garder uniquement le PK et le unique hash_md5 (dedup import)
-- fec_ecriture_pkey = PK (garder)
-- idx_fec_hash_md5 = unique pour dedup (garder)

COMMENT ON TABLE fec_ecriture IS 'Archive FEC legale (Art. A.47 A-1 LPF). NE PLUS UTILISER pour les vues — utiliser grand_livre.';


-- ============================================
-- 8. NETTOYAGE _staging_fec
-- ============================================

TRUNCATE TABLE _staging_fec;


-- ============================================
-- 9. VERIFICATION
-- ============================================

DO $$
DECLARE
    v_gl_count INT;
    v_has_code BOOLEAN;
BEGIN
    SELECT COUNT(*) INTO v_gl_count FROM grand_livre WHERE entite_code IS NULL;
    IF v_gl_count > 0 THEN
        RAISE WARNING 'ATTENTION: % lignes dans grand_livre sans entite_code', v_gl_count;
    ELSE
        RAISE NOTICE 'OK: toutes les lignes grand_livre ont un entite_code';
    END IF;

    SELECT EXISTS(
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'grand_livre' AND column_name = 'entite_code'
    ) INTO v_has_code;
    IF v_has_code THEN
        RAISE NOTICE 'OK: colonne entite_code presente dans grand_livre';
    END IF;

    RAISE NOTICE 'Migration 002 terminee — schema simplifie';
END $$;

COMMIT;
