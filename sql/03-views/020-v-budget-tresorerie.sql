-- ════════════════════════════════════════════════════════════════════════════
-- 020-v-budget-tresorerie.sql
--
-- Projection de tresorerie nette basee sur un scenario budgetaire.
--
-- 3 modes supportes (budget_tresorerie_parametres.mode_projection) :
--   1. taux_jours     : projection BFR via DSO/DPO/DIO appliques sur CA/achats budget
--   2. montant_direct : l'utilisateur saisit directement un BFR cible et/ou TN cible
--   3. hybride        : taux_jours + override montant direct si renseigne
--
-- Formule TN projetee (mode taux_jours) :
--   TN_projete = FRNG_reel_N-1 + Resultat_budget - BFR_projete
--
--   avec BFR_projete =
--       (CA_HT_budget  × 1.20 / 365 × DSO)    → creances clients TTC
--     + (Achats_HT     / 365 × DIO)            → stocks
--     - (Achats_HT     × 1.20 / 365 × DPO)    → dettes fournisseurs TTC
--
-- Hypothese simplifiee : TVA 20%. A affiner si entite en regime reel / franchise.
-- ════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE VIEW v_budget_tresorerie AS
WITH
budget_agrege AS (
    SELECT
        scenario_id,
        entite_id,
        annee,
        annee_reference,
        SUM(CASE WHEN compte_numero LIKE '70%' THEN montant_budget ELSE 0 END)   AS ca_ht_budget,
        SUM(CASE WHEN compte_numero LIKE '60%'
                   OR compte_numero LIKE '61%'
                   OR compte_numero LIKE '62%' THEN montant_budget ELSE 0 END)    AS achats_ht_budget,
        SUM(CASE WHEN classe = 7 THEN montant_budget ELSE 0 END)                  AS produits_total,
        SUM(CASE WHEN classe = 6 THEN montant_budget ELSE 0 END)                  AS charges_total
    FROM v_budget_crd
    GROUP BY scenario_id, entite_id, annee, annee_reference
),
bfr_reference AS (
    SELECT
        entite_id,
        annee,
        SUM(CASE WHEN bf_categorie = 'bfr_exploit'       THEN montant ELSE 0 END) AS bfr_exploit,
        SUM(CASE WHEN bf_categorie = 'bfr_hors_exploit'  THEN montant ELSE 0 END) AS bfr_hors_exploit,
        SUM(CASE WHEN bf_categorie = 'tresorerie_active' THEN montant ELSE 0 END) AS tresorerie_active,
        SUM(CASE WHEN bf_categorie = 'tresorerie_passive' THEN montant ELSE 0 END) AS tresorerie_passive,
        SUM(CASE WHEN bf_categorie = 'ressources_stables' THEN montant ELSE 0 END) AS ressources_stables,
        SUM(CASE WHEN bf_categorie = 'emplois_stables'   THEN montant ELSE 0 END) AS emplois_stables
    FROM v_bilan_fonctionnel
    GROUP BY entite_id, annee
),
calcul AS (
    SELECT
        bs.id AS scenario_id,
        bs.entite_id,
        bs.annee,
        bs.annee_reference,
        COALESCE(btp.mode_projection, 'taux_jours') AS mode_projection,
        COALESCE(btp.dso_jours, 60)  AS dso_jours,
        COALESCE(btp.dpo_jours, 45)  AS dpo_jours,
        COALESCE(btp.dio_jours, 0)   AS dio_jours,
        btp.tn_cible_annuelle,
        btp.bfr_cible_annuel,
        -- Montants reels N-1 (reference)
        COALESCE(br.bfr_exploit + br.bfr_hors_exploit, 0)       AS bfr_reel,
        COALESCE(br.tresorerie_active - br.tresorerie_passive, 0) AS tn_reel,
        COALESCE(br.ressources_stables - br.emplois_stables, 0)   AS frng_reel,
        -- Budget N
        COALESCE(ba.ca_ht_budget, 0)      AS ca_budget,
        COALESCE(ba.achats_ht_budget, 0)  AS achats_budget,
        COALESCE(ba.produits_total - ba.charges_total, 0) AS resultat_budget,
        -- BFR calcule via delais
        ROUND(
            (COALESCE(ba.ca_ht_budget, 0) * 1.20 / 365.0 * COALESCE(btp.dso_jours, 60))
          + (COALESCE(ba.achats_ht_budget, 0) / 365.0 * COALESCE(btp.dio_jours, 0))
          - (COALESCE(ba.achats_ht_budget, 0) * 1.20 / 365.0 * COALESCE(btp.dpo_jours, 45))
        , 2) AS bfr_calcule_delais
    FROM budget_scenario bs
    LEFT JOIN budget_tresorerie_parametres btp ON btp.scenario_id = bs.id
    LEFT JOIN budget_agrege ba                  ON ba.scenario_id = bs.id
    LEFT JOIN bfr_reference br                  ON br.entite_id = bs.entite_id
                                                AND br.annee = bs.annee_reference
)
SELECT
    scenario_id,
    entite_id,
    annee,
    annee_reference,
    mode_projection,
    dso_jours, dpo_jours, dio_jours,
    bfr_reel,
    tn_reel,
    frng_reel,
    ca_budget,
    achats_budget,
    resultat_budget,
    bfr_calcule_delais,
    tn_cible_annuelle,
    bfr_cible_annuel,
    -- BFR retenu selon le mode
    CASE
        WHEN mode_projection = 'montant_direct' AND bfr_cible_annuel IS NOT NULL
            THEN bfr_cible_annuel
        WHEN mode_projection = 'hybride'        AND bfr_cible_annuel IS NOT NULL
            THEN bfr_cible_annuel
        ELSE bfr_calcule_delais
    END AS bfr_budget,
    -- TN retenue selon le mode
    CASE
        WHEN mode_projection = 'montant_direct' AND tn_cible_annuelle IS NOT NULL
            THEN tn_cible_annuelle
        WHEN mode_projection = 'hybride'        AND tn_cible_annuelle IS NOT NULL
            THEN tn_cible_annuelle
        ELSE frng_reel + resultat_budget - (
            CASE
                WHEN mode_projection = 'montant_direct' AND bfr_cible_annuel IS NOT NULL
                    THEN bfr_cible_annuel
                WHEN mode_projection = 'hybride'        AND bfr_cible_annuel IS NOT NULL
                    THEN bfr_cible_annuel
                ELSE bfr_calcule_delais
            END
        )
    END AS tn_budget,
    -- Variation de tresorerie vs reel N-1
    (
        CASE
            WHEN mode_projection = 'montant_direct' AND tn_cible_annuelle IS NOT NULL
                THEN tn_cible_annuelle
            WHEN mode_projection = 'hybride'        AND tn_cible_annuelle IS NOT NULL
                THEN tn_cible_annuelle
            ELSE frng_reel + resultat_budget - (
                CASE
                    WHEN mode_projection = 'montant_direct' AND bfr_cible_annuel IS NOT NULL
                        THEN bfr_cible_annuel
                    WHEN mode_projection = 'hybride'        AND bfr_cible_annuel IS NOT NULL
                        THEN bfr_cible_annuel
                    ELSE bfr_calcule_delais
                END
            )
        END - tn_reel
    ) AS variation_tn
FROM calcul;

COMMENT ON VIEW v_budget_tresorerie IS
    'Projection de la tresorerie nette par scenario budgetaire (3 modes : delais, montants, hybride)';
