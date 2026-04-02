-- ============================================
-- Table: fec_import
-- Tracabilite des imports Pennylane
-- ============================================

CREATE TABLE IF NOT EXISTS fec_import (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entite_id UUID NOT NULL REFERENCES entite(id),
    exercice_id UUID NOT NULL REFERENCES exercice(id),
    source TEXT DEFAULT 'pennylane',
    date_import TIMESTAMPTZ DEFAULT now(),
    nb_lignes_brut INTEGER,
    nb_lignes_inserees INTEGER,
    duree_secondes NUMERIC,
    statut TEXT DEFAULT 'en_cours',  -- en_cours, termine, erreur
    erreur TEXT
);

-- Index
CREATE INDEX IF NOT EXISTS idx_fec_import_entite ON fec_import(entite_id);
CREATE INDEX IF NOT EXISTS idx_fec_import_statut ON fec_import(statut);
