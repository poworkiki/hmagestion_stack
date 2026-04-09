-- ============================================
-- Table: pcg_analytique
-- Plan Comptable Général — 1 412 comptes
-- avec mapping analytique (SIG, CR, Bilan, BF, V/F)
-- ============================================

CREATE TABLE IF NOT EXISTS pcg_analytique (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero TEXT UNIQUE NOT NULL,
    libelle TEXT NOT NULL,
    classe SMALLINT NOT NULL,

    -- Mapping SIG (Soldes Intermédiaires de Gestion)
    sig_solde TEXT,          -- Ex: 'Marge commerciale', 'Valeur ajoutée', 'EBE'
    sig_signe SMALLINT,      -- +1 (addition) ou -1 (soustraction) dans le solde

    -- Mapping Compte de Résultat
    cr_rubrique TEXT,        -- Ex: 'Produits d''exploitation', 'Charges financières'
    cr_signe SMALLINT,       -- +1 (produit) ou -1 (charge)

    -- Mapping Bilan
    bilan_poste TEXT,        -- Ex: 'Immobilisations corporelles', 'Dettes fournisseurs'
    bilan_section TEXT,      -- actif_immobilise, actif_circulant, passif_capitaux, passif_dettes

    -- Mapping Bilan Fonctionnel
    bf_categorie TEXT,       -- emplois_stables, ressources_stables, bfr_exploit, bfr_hors_exploit, tresorerie_active, tresorerie_passive

    -- Nature Variable/Fixe (pour résultat différentiel)
    nature_defaut TEXT DEFAULT 'fixe',  -- 'variable' ou 'fixe'

    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_pcg_numero ON pcg_analytique(numero);
CREATE INDEX IF NOT EXISTS idx_pcg_classe ON pcg_analytique(classe);
CREATE INDEX IF NOT EXISTS idx_pcg_sig ON pcg_analytique(sig_solde) WHERE sig_solde IS NOT NULL;
