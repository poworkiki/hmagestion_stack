-- ============================================
-- v_resultat_mensuel + v_ytd_cumule
-- Renommage (v_ytd_mensuel etait mal nomme : pas cumulatif)
-- Ajout d un vrai YTD cumulatif + projection annuelle
-- ============================================

-- 1. v_resultat_mensuel (alias propre de v_ytd_mensuel)
CREATE OR REPLACE VIEW v_resultat_mensuel AS
SELECT
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, mois, mois_label, trimestre, debut_mois,
    ca, charges, produits, resultat
FROM v_ytd_mensuel;

-- 2. v_ytd_cumule (vrai YTD cumulatif + projection)
CREATE OR REPLACE VIEW v_ytd_cumule AS
SELECT
    entite_id,
    entite_nom,
    exercice_id,
    exercice_label,
    annee,
    mois,
    mois_label,
    trimestre,
    debut_mois,
    -- Valeurs du mois isole
    ca          AS ca_mois,
    charges     AS charges_mois,
    produits    AS produits_mois,
    resultat    AS resultat_mois,
    -- Cumul YTD depuis janvier
    SUM(ca)       OVER (PARTITION BY entite_id, annee ORDER BY mois) AS ca_ytd,
    SUM(charges)  OVER (PARTITION BY entite_id, annee ORDER BY mois) AS charges_ytd,
    SUM(produits) OVER (PARTITION BY entite_id, annee ORDER BY mois) AS produits_ytd,
    SUM(resultat) OVER (PARTITION BY entite_id, annee ORDER BY mois) AS resultat_ytd,
    -- CA moyen mensuel et projection annuelle
    ROUND(SUM(ca) OVER (PARTITION BY entite_id, annee ORDER BY mois) / GREATEST(mois, 1), 2)      AS ca_moyen_mensuel,
    ROUND(SUM(ca) OVER (PARTITION BY entite_id, annee ORDER BY mois) / GREATEST(mois, 1) * 12, 2) AS ca_projete_annuel,
    -- Taux de marge YTD en pourcentage
    CASE WHEN SUM(ca) OVER (PARTITION BY entite_id, annee ORDER BY mois) != 0
         THEN ROUND(SUM(resultat) OVER (PARTITION BY entite_id, annee ORDER BY mois) /
                    SUM(ca) OVER (PARTITION BY entite_id, annee ORDER BY mois) * 100, 2)
         ELSE NULL END AS taux_marge_ytd_pct
FROM v_ytd_mensuel;

COMMENT ON VIEW v_resultat_mensuel IS 'Resultat mensuel isole par structure/exercice/mois';
COMMENT ON VIEW v_ytd_cumule IS 'YTD cumulatif + projection annuelle + taux de marge';
