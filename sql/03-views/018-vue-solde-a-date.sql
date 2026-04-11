-- ============================================
-- v_solde_a_date + v_solde_a_date_journalier
-- Solde cumulatif depuis l ouverture du compte (incluant a-nouveaux)
-- Pour classes 1-5 (bilan) ou cumul YTD n a pas de sens
-- ============================================

-- 1. Solde a date mensuel : solde cumulatif au dernier jour de chaque mois
CREATE OR REPLACE VIEW v_solde_a_date AS
SELECT
    entite_id,
    entite_nom,
    exercice_id,
    exercice_label,
    annee,
    mois,
    mois_label,
    compte_numero,
    compte_libelle,
    classe,
    -- Mouvement du mois seul
    SUM(debit)           AS debit_mois,
    SUM(credit)          AS credit_mois,
    SUM(debit - credit)  AS mouvement_mois,
    -- Solde a date : cumul progressif depuis le debut (incluant a-nouveaux)
    SUM(SUM(debit - credit)) OVER (
        PARTITION BY entite_id, compte_numero
        ORDER BY annee, mois
    ) AS solde_debiteur,
    -- Meme calcul mais en solde crediteur (classes 1, 7, partie 4)
    -SUM(SUM(debit - credit)) OVER (
        PARTITION BY entite_id, compte_numero
        ORDER BY annee, mois
    ) AS solde_crediteur
FROM grand_livre
WHERE compte_numero IS NOT NULL
GROUP BY entite_id, entite_nom, exercice_id, exercice_label,
         annee, mois, mois_label, compte_numero, compte_libelle, classe;

COMMENT ON VIEW v_solde_a_date IS 'Solde cumulatif a date (fin de mois) par compte, incluant a-nouveaux. Pour classes 1-5 (bilan).';

-- 2. Solde a date journalier : pour la treso et les postes sensibles
CREATE OR REPLACE VIEW v_solde_a_date_journalier AS
SELECT
    entite_id,
    entite_nom,
    compte_numero,
    compte_libelle,
    classe,
    ecriture_date AS date_jour,
    SUM(debit)            AS debit_jour,
    SUM(credit)           AS credit_jour,
    SUM(debit - credit)   AS mouvement_jour,
    -- Solde cumul a date
    SUM(SUM(debit - credit)) OVER (
        PARTITION BY entite_id, compte_numero
        ORDER BY ecriture_date
    ) AS solde_debiteur,
    -SUM(SUM(debit - credit)) OVER (
        PARTITION BY entite_id, compte_numero
        ORDER BY ecriture_date
    ) AS solde_crediteur
FROM grand_livre
WHERE compte_numero IS NOT NULL
GROUP BY entite_id, entite_nom, compte_numero, compte_libelle, classe, ecriture_date;

COMMENT ON VIEW v_solde_a_date_journalier IS 'Solde cumulatif au jour le jour par compte. Pour suivi treso (classe 5) et tiers (classe 4).';
