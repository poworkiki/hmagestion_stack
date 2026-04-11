-- ════════════════════════════════════════════════════════════════════════════
-- 019-v-budget-crd.sql
--
-- Vue qui applique la cascade d'overrides budget sur les montants reels N-1.
-- Ordre de priorite (du plus specifique au plus general) :
--   1. budget_override_compte.valeur_fixe      (ecrase tout)
--   2. budget_override_compte.taux_override    (applique sur le reel du compte)
--   3. budget_override_categorie.taux_override (applique sur le reel du compte)
--   4. budget_regle_globale.taux_revenus/charges (defaut, selon classe PCG)
--
-- Consommation :
--   SELECT * FROM v_budget_crd WHERE scenario_id = '...' ORDER BY crd_ordre;
-- ════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE VIEW v_budget_crd AS
WITH
-- 1. Montants reels N-1 par compte (classes 6 et 7 seulement)
reel_par_compte AS (
    SELECT
        bs.id                          AS scenario_id,
        bs.entite_id,
        bs.annee,
        bs.annee_reference,
        gl.compte_numero,
        gl.compte_libelle,
        gl.classe,
        pa.crd_ordre,
        pa.crd_categorie,
        pa.crd_rubrique,
        pa.crd_signe,
        SUM(
            CASE
                WHEN gl.classe = 7 THEN gl.credit - gl.debit
                WHEN gl.classe = 6 THEN gl.debit - gl.credit
                ELSE 0
            END
        )::numeric(14,2) AS montant_reel
    FROM budget_scenario bs
    INNER JOIN grand_livre gl
        ON gl.entite_id = bs.entite_id
       AND gl.annee = bs.annee_reference
       AND gl.classe IN (6, 7)
       AND NOT gl.is_a_nouveau
    LEFT JOIN pcg_analytique pa
        ON pa.numero = gl.compte_numero
    GROUP BY bs.id, bs.entite_id, bs.annee, bs.annee_reference,
             gl.compte_numero, gl.compte_libelle, gl.classe,
             pa.crd_ordre, pa.crd_categorie, pa.crd_rubrique, pa.crd_signe
),
-- 2. Application de la cascade d'overrides
avec_overrides AS (
    SELECT
        r.*,
        brg.taux_revenus,
        brg.taux_charges,
        boc.taux_override     AS taux_categorie,
        bocp.taux_override    AS taux_compte,
        bocp.valeur_fixe      AS valeur_fixe_compte,
        -- Taux effectif applique (le plus specifique trouve)
        COALESCE(
            bocp.taux_override,
            boc.taux_override,
            CASE WHEN r.classe = 7 THEN brg.taux_revenus ELSE brg.taux_charges END
        ) AS taux_effectif,
        -- Source de l'override pour debug/UI
        CASE
            WHEN bocp.valeur_fixe IS NOT NULL THEN 'compte_valeur_fixe'
            WHEN bocp.taux_override IS NOT NULL THEN 'compte_taux'
            WHEN boc.taux_override IS NOT NULL THEN 'categorie'
            ELSE 'global'
        END AS source_override
    FROM reel_par_compte r
    LEFT JOIN budget_regle_globale brg
        ON brg.scenario_id = r.scenario_id
    LEFT JOIN budget_override_categorie boc
        ON boc.scenario_id = r.scenario_id
       AND boc.crd_categorie = r.crd_categorie
    LEFT JOIN budget_override_compte bocp
        ON bocp.scenario_id = r.scenario_id
       AND bocp.compte_numero = r.compte_numero
)
SELECT
    scenario_id,
    entite_id,
    annee,
    annee_reference,
    compte_numero,
    compte_libelle,
    classe,
    crd_ordre,
    crd_categorie,
    crd_rubrique,
    crd_signe,
    montant_reel,
    taux_effectif,
    source_override,
    -- Montant budgetaire final
    CASE
        WHEN valeur_fixe_compte IS NOT NULL THEN valeur_fixe_compte
        ELSE (montant_reel * (1 + taux_effectif / 100))::numeric(14,2)
    END AS montant_budget,
    -- Ecart en euros
    CASE
        WHEN valeur_fixe_compte IS NOT NULL
            THEN (valeur_fixe_compte - montant_reel)::numeric(14,2)
        ELSE (montant_reel * taux_effectif / 100)::numeric(14,2)
    END AS ecart_budget
FROM avec_overrides;

COMMENT ON VIEW v_budget_crd IS
    'Budget CRD calcule par application de la cascade d overrides sur le reel N-1';
