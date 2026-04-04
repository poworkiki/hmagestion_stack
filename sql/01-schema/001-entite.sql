-- ============================================
-- Table: entite
-- Les 4 structures du groupe HMA
-- ============================================

CREATE TABLE IF NOT EXISTS entite (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE NOT NULL,
    nom TEXT NOT NULL,
    activite TEXT NOT NULL,
    siren TEXT,
    parent_id UUID REFERENCES entite(id),
    profil TEXT NOT NULL DEFAULT 'general',
    actif BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_entite_code ON entite(code);

-- Données initiales : les 4 structures
-- HMA est la holding (parent des 3 autres)
INSERT INTO entite (code, nom, activite, profil) VALUES
    ('HMA', 'HMA', 'Holding', 'holding')
ON CONFLICT (code) DO NOTHING;

-- Filiales rattachées à HMA
INSERT INTO entite (code, nom, activite, profil, parent_id) VALUES
    ('STIVMAT', 'STIVMAT', 'Transport de personnes', 'transport',
        (SELECT id FROM entite WHERE code = 'HMA')),
    ('STA', 'STA', 'Transport de personnes', 'transport',
        (SELECT id FROM entite WHERE code = 'HMA')),
    ('ETPA', 'ETPA', 'Transformation de produits agricoles', 'agroalimentaire',
        (SELECT id FROM entite WHERE code = 'HMA'))
ON CONFLICT (code) DO NOTHING;
