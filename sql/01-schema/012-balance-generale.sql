-- ============================================
-- VUE MATÉRIALISÉE balance_generale
-- Agrégation de la table grand_livre par compte/mois
-- ============================================

DROP MATERIALIZED VIEW IF EXISTS balance_generale CASCADE;

CREATE MATERIALIZED VIEW balance_generale AS
SELECT
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label, debut_mois,
    compte_numero, compte_libelle, classe,
    sig_solde, sig_signe, cr_rubrique, cr_signe,
    bilan_poste, bilan_section, bf_categorie, nature_defaut,
    crd_ordre, crd_categorie, crd_rubrique, crd_signe,
    SUM(debit) AS total_debit,
    SUM(credit) AS total_credit,
    SUM(solde) AS solde
FROM grand_livre
WHERE compte_numero IS NOT NULL
GROUP BY
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label, debut_mois,
    compte_numero, compte_libelle, classe,
    sig_solde, sig_signe, cr_rubrique, cr_signe,
    bilan_poste, bilan_section, bf_categorie, nature_defaut,
    crd_ordre, crd_categorie, crd_rubrique, crd_signe;

-- Index sur la MV pour requêtes rapides Superset
CREATE UNIQUE INDEX idx_bg_pk ON balance_generale
    (entite_id, annee, mois, compte_numero);
CREATE INDEX idx_bg_entite ON balance_generale (entite_id);
CREATE INDEX idx_bg_compte ON balance_generale (compte_numero);
CREATE INDEX idx_bg_annee ON balance_generale (annee, mois);
CREATE INDEX idx_bg_classe ON balance_generale (classe);

COMMENT ON MATERIALIZED VIEW balance_generale IS 'Balance Générale — agrégation par compte/mois depuis grand_livre. REFRESH après chaque sync.';
