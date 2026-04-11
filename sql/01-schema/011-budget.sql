-- ════════════════════════════════════════════════════════════════════════════
-- 011-budget.sql — Tables budget (chantier C)
--
-- Architecture : cascade d'overrides du plus specifique au plus general
--   compte > categorie > global
--
-- Un scenario = une hypothese budgetaire (brouillon ou valide).
-- Plusieurs scenarios coexistent par entite/annee (ex: central, optimiste...).
-- ════════════════════════════════════════════════════════════════════════════

-- ─── SCENARIOS ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS budget_scenario (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entite_id      uuid NOT NULL REFERENCES entite(id) ON DELETE CASCADE,
    annee          integer NOT NULL,
    nom            text NOT NULL,
    description    text,
    valide         boolean NOT NULL DEFAULT false,
    date_validation date,
    annee_reference integer NOT NULL,  -- annee N-1 utilisee comme base
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE(entite_id, annee, nom)
);

CREATE INDEX IF NOT EXISTS idx_budget_scenario_entite_annee
    ON budget_scenario(entite_id, annee);

COMMENT ON TABLE budget_scenario IS
    'Scenarios budgetaires multi-hypotheses par entite/annee';
COMMENT ON COLUMN budget_scenario.annee_reference IS
    'Annee dont les donnees reelles servent de base au calcul budgetaire';

-- ─── REGLE GLOBALE (taux par defaut revenus/charges) ────────────────────────

CREATE TABLE IF NOT EXISTS budget_regle_globale (
    scenario_id   uuid PRIMARY KEY REFERENCES budget_scenario(id) ON DELETE CASCADE,
    taux_revenus  numeric(6,2) NOT NULL DEFAULT 10.00,  -- +10% sur classe 7
    taux_charges  numeric(6,2) NOT NULL DEFAULT  5.00,  -- +5% sur classe 6
    updated_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE budget_regle_globale IS
    'Taux de variation par defaut applique sur les revenus et les charges du reel N-1';

-- ─── OVERRIDES PAR CATEGORIE CRD ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS budget_override_categorie (
    scenario_id    uuid NOT NULL REFERENCES budget_scenario(id) ON DELETE CASCADE,
    crd_categorie  text NOT NULL,
    taux_override  numeric(6,2) NOT NULL,
    PRIMARY KEY (scenario_id, crd_categorie)
);

COMMENT ON TABLE budget_override_categorie IS
    'Override du taux par categorie CRD (ex: Charges variables a +3% au lieu de +5%)';

-- ─── OVERRIDES PAR COMPTE (taux OU valeur fixe) ─────────────────────────────

CREATE TABLE IF NOT EXISTS budget_override_compte (
    scenario_id    uuid NOT NULL REFERENCES budget_scenario(id) ON DELETE CASCADE,
    compte_numero  text NOT NULL,
    taux_override  numeric(6,2),
    valeur_fixe    numeric(14,2),
    commentaire    text,
    PRIMARY KEY (scenario_id, compte_numero),
    CHECK (taux_override IS NOT NULL OR valeur_fixe IS NOT NULL)
);

COMMENT ON TABLE budget_override_compte IS
    'Override granulaire par compte PCG : soit taux, soit valeur fixe annuelle';

-- ─── PARAMETRES TRESORERIE (DSO/DPO/DIO + mode montant direct) ──────────────

CREATE TABLE IF NOT EXISTS budget_tresorerie_parametres (
    scenario_id          uuid PRIMARY KEY REFERENCES budget_scenario(id) ON DELETE CASCADE,
    mode_projection      text NOT NULL DEFAULT 'taux_jours'
        CHECK (mode_projection IN ('taux_jours', 'montant_direct', 'hybride')),
    -- Mode taux_jours : projection via delais DSO/DPO/DIO
    dso_jours            integer DEFAULT 60,  -- Days Sales Outstanding
    dpo_jours            integer DEFAULT 45,  -- Days Payable Outstanding
    dio_jours            integer DEFAULT 0,   -- Days Inventory Outstanding
    -- Mode montant_direct : cible annuelle en euros (prend le dessus si mode != taux_jours)
    tn_cible_annuelle    numeric(14,2),       -- Tresorerie nette cible fin d'annee
    bfr_cible_annuel     numeric(14,2),       -- Besoin en fonds de roulement cible
    commentaire          text,
    updated_at           timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE budget_tresorerie_parametres IS
    'Parametres projection tresorerie : 3 modes (DSO/DPO/DIO, montants directs, hybride)';
COMMENT ON COLUMN budget_tresorerie_parametres.mode_projection IS
    'taux_jours = simulation via delais (recommande), montant_direct = cible en euros, hybride = utilise delais + override montant si renseigne';

-- ─── TRIGGER updated_at ─────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_budget_scenario_updated ON budget_scenario;
CREATE TRIGGER trg_budget_scenario_updated
    BEFORE UPDATE ON budget_scenario
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_budget_regle_globale_updated ON budget_regle_globale;
CREATE TRIGGER trg_budget_regle_globale_updated
    BEFORE UPDATE ON budget_regle_globale
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_budget_tresorerie_parametres_updated ON budget_tresorerie_parametres;
CREATE TRIGGER trg_budget_tresorerie_parametres_updated
    BEFORE UPDATE ON budget_tresorerie_parametres
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
