-- ============================================
-- Table: compte_resolution
-- Résolution préfixe FEC → numéro PCG
-- Ex: "411CLIENT001" → "411"
-- ============================================

CREATE TABLE IF NOT EXISTS compte_resolution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prefixe TEXT UNIQUE NOT NULL,
    pcg_numero TEXT NOT NULL REFERENCES pcg_analytique(numero),
    priorite SMALLINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_compte_resolution_prefixe ON compte_resolution(prefixe);
