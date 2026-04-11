-- ============================================
-- v_resultat_journalier + v_ytd_journalier
-- Cumul au jour le jour : mouvement quotidien + cumul YTD
-- ============================================

-- 1. Resultat journalier (mouvement du jour isole)
CREATE OR REPLACE VIEW v_resultat_journalier AS
SELECT
    entite_id,
    entite_nom,
    exercice_id,
    exercice_label,
    annee,
    trimestre,
    mois,
    mois_label,
    ecriture_date AS date_jour,
    SUM(CASE WHEN compte_numero ~ '^70' THEN credit - debit ELSE 0 END)     AS ca,
    SUM(CASE WHEN classe = 6            THEN debit - credit ELSE 0 END)     AS charges,
    SUM(CASE WHEN classe = 7            THEN credit - debit ELSE 0 END)     AS produits,
    SUM(CASE WHEN classe = 7            THEN credit - debit ELSE 0 END)
    - SUM(CASE WHEN classe = 6          THEN debit - credit ELSE 0 END)     AS resultat
FROM grand_livre
WHERE classe IN (6, 7)
  AND NOT is_a_nouveau
GROUP BY entite_id, entite_nom, exercice_id, exercice_label,
         annee, trimestre, mois, mois_label, ecriture_date;

COMMENT ON VIEW v_resultat_journalier IS 'Mouvements du jour seul : CA/charges/produits/resultat par jour (sans a-nouveaux)';

-- 2. YTD cumul journalier
CREATE OR REPLACE VIEW v_ytd_journalier AS
SELECT
    entite_id,
    entite_nom,
    exercice_id,
    exercice_label,
    annee,
    trimestre,
    mois,
    mois_label,
    date_jour,
    -- Valeurs du jour isole
    ca          AS ca_jour,
    charges     AS charges_jour,
    produits    AS produits_jour,
    resultat    AS resultat_jour,
    -- Cumul YTD depuis le 1er janvier
    SUM(ca)       OVER (PARTITION BY entite_id, annee ORDER BY date_jour) AS ca_ytd,
    SUM(charges)  OVER (PARTITION BY entite_id, annee ORDER BY date_jour) AS charges_ytd,
    SUM(produits) OVER (PARTITION BY entite_id, annee ORDER BY date_jour) AS produits_ytd,
    SUM(resultat) OVER (PARTITION BY entite_id, annee ORDER BY date_jour) AS resultat_ytd,
    -- Jours ecoules depuis le debut de l exercice
    (date_jour - make_date(annee::int, 1, 1) + 1)::int AS jour_exercice,
    -- Run rate : CA moyen journalier et projection annuelle (365 jours)
    ROUND(SUM(ca) OVER (PARTITION BY entite_id, annee ORDER BY date_jour)
          / GREATEST((date_jour - make_date(annee::int, 1, 1) + 1)::int, 1), 2) AS ca_moyen_jour,
    ROUND(SUM(ca) OVER (PARTITION BY entite_id, annee ORDER BY date_jour)
          / GREATEST((date_jour - make_date(annee::int, 1, 1) + 1)::int, 1) * 365, 2) AS ca_projete_annuel,
    -- Taux de marge YTD en pourcentage
    CASE WHEN SUM(ca) OVER (PARTITION BY entite_id, annee ORDER BY date_jour) != 0
         THEN ROUND(SUM(resultat) OVER (PARTITION BY entite_id, annee ORDER BY date_jour) /
                    SUM(ca)       OVER (PARTITION BY entite_id, annee ORDER BY date_jour) * 100, 2)
         ELSE NULL END AS taux_marge_ytd_pct
FROM v_resultat_journalier;

COMMENT ON VIEW v_ytd_journalier IS 'YTD cumulatif au jour le jour + projection annuelle (base 365j) + taux de marge';
