-- ============================================
-- v_resultat_trimestriel + v_resultat_annuel
-- Nommage propre pour les agregations (les v_ytd_* sont mal nommees)
-- Les anciennes v_ytd_mensuel/trimestriel/annuel sont gardees en alias deprecated
-- ============================================

CREATE OR REPLACE VIEW v_resultat_trimestriel AS
SELECT entite_id, entite_nom, exercice_id, exercice_label, annee, trimestre,
    SUM(ca) AS ca, SUM(charges) AS charges, SUM(produits) AS produits, SUM(resultat) AS resultat
FROM v_resultat_mensuel
GROUP BY entite_id, entite_nom, exercice_id, exercice_label, annee, trimestre;

CREATE OR REPLACE VIEW v_resultat_annuel AS
SELECT entite_id, entite_nom, exercice_id, exercice_label, annee,
    SUM(ca) AS ca, SUM(charges) AS charges, SUM(produits) AS produits, SUM(resultat) AS resultat
FROM v_resultat_mensuel
GROUP BY entite_id, entite_nom, exercice_id, exercice_label, annee;

COMMENT ON VIEW v_resultat_trimestriel IS 'Agregation trimestrielle du CA/charges/resultat (remplace v_ytd_trimestriel mal nomme)';
COMMENT ON VIEW v_resultat_annuel IS 'Agregation annuelle du CA/charges/resultat (remplace v_ytd_annuel mal nomme)';
COMMENT ON VIEW v_ytd_mensuel IS 'DEPRECATED - utiliser v_resultat_mensuel ou v_ytd_cumule';
COMMENT ON VIEW v_ytd_trimestriel IS 'DEPRECATED - utiliser v_resultat_trimestriel';
COMMENT ON VIEW v_ytd_annuel IS 'DEPRECATED - utiliser v_resultat_annuel';
