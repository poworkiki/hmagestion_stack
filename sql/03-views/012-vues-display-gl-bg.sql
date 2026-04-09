-- ============================================
-- VUES D'AFFICHAGE : Balance Générale + Grand Livre
-- Convention comptable française :
--   solde_debiteur = MAX(debit - credit, 0)
--   solde_crediteur = MAX(credit - debit, 0)
-- Date : 2026-04-09
-- ============================================

DROP VIEW IF EXISTS v_bg_display CASCADE;
DROP VIEW IF EXISTS v_gl_display CASCADE;
DROP VIEW IF EXISTS v_gl_bg_combined CASCADE;


-- ============================================
-- 1. BALANCE GÉNÉRALE — affichage propre
-- Agrégation par entité/année/compte (pas par mois)
-- Colonnes solde_debiteur / solde_crediteur séparées
-- ============================================

CREATE VIEW v_bg_display AS
SELECT
    entite_nom,
    annee,
    classe,
    compte_numero,
    compte_libelle,
    -- Totaux
    SUM(total_debit) AS total_debit,
    SUM(total_credit) AS total_credit,
    -- Soldes séparés (convention BG française)
    GREATEST(SUM(total_debit) - SUM(total_credit), 0) AS solde_debiteur,
    GREATEST(SUM(total_credit) - SUM(total_debit), 0) AS solde_crediteur,
    -- Solde signé (pour calculs)
    SUM(total_debit) - SUM(total_credit) AS solde,
    -- Mapping PCG (pour filtres)
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


-- ============================================
-- 2. BALANCE GÉNÉRALE MENSUELLE — pour pivot par mois
-- 1 ligne = 1 compte × 1 mois (pas d'agrégation annuelle)
-- ============================================

CREATE VIEW v_bg_mensuelle AS
SELECT
    entite_nom,
    annee,
    trimestre,
    mois,
    mois_label,
    classe,
    compte_numero,
    compte_libelle,
    total_debit,
    total_credit,
    GREATEST(total_debit - total_credit, 0) AS solde_debiteur,
    GREATEST(total_credit - total_debit, 0) AS solde_crediteur,
    total_debit - total_credit AS solde,
    sig_solde,
    cr_rubrique,
    bilan_poste,
    bilan_section,
    crd_categorie
FROM balance_generale;


-- ============================================
-- 3. GRAND LIVRE — affichage propre
-- Écritures individuelles avec flag AN + solde cumulé
-- ============================================

CREATE VIEW v_gl_display AS
SELECT
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
    -- Solde cumulé progressif par compte
    SUM(solde) OVER (
        PARTITION BY entite_nom, annee, compte_numero
        ORDER BY ecriture_date, id
    ) AS solde_cumule,
    piece_ref,
    comp_aux_num,
    ecriture_let,
    is_a_nouveau,
    -- Libellé lisible pour le flag
    CASE WHEN is_a_nouveau THEN 'À-nouveau' ELSE 'Exercice' END AS type_ecriture
FROM grand_livre;


-- ============================================
-- 4. VUE COMBINÉE GL+BG — pour Drill By (Dashboard 3)
-- Niveau 1 = Balance (agrégé), Niveau 2 = GL (détail)
-- Même dataset, drill by ecriture_date/ecriture_lib
-- ============================================

CREATE VIEW v_gl_bg_combined AS
SELECT
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
    CASE WHEN g.is_a_nouveau THEN 'À-nouveau' ELSE 'Exercice' END AS type_ecriture,
    -- Mapping pour filtres et drill
    g.sig_solde,
    g.cr_rubrique,
    g.bilan_poste,
    g.bilan_section,
    g.crd_categorie,
    -- Clé de regroupement pour Balance (drill-by depuis ce niveau)
    g.compte_numero || ' — ' || g.compte_libelle AS compte_display
FROM grand_livre g;


COMMENT ON VIEW v_bg_display IS 'Balance Générale annuelle — solde débiteur/créditeur séparés, 1 ligne par compte/année';
COMMENT ON VIEW v_bg_mensuelle IS 'Balance Générale mensuelle — pour pivot par mois dans Superset';
COMMENT ON VIEW v_gl_display IS 'Grand Livre avec solde cumulé progressif par compte';
COMMENT ON VIEW v_gl_bg_combined IS 'GL+BG combiné — source unique pour Drill By dans Superset';
