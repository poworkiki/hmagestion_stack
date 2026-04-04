-- ============================================
-- Table: exercice
-- Exercices comptables par entité
-- Calés sur l'année civile (01/01–31/12)
-- ============================================

CREATE TABLE IF NOT EXISTS exercice (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entite_id UUID NOT NULL REFERENCES entite(id),
    label TEXT NOT NULL,           -- Ex: '2025', '2024'
    date_debut DATE NOT NULL,
    date_fin DATE NOT NULL,
    cloture BOOLEAN DEFAULT false, -- Exercice clôturé ou non
    created_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT uq_exercice_entite_debut UNIQUE (entite_id, date_debut),
    CONSTRAINT ck_exercice_dates CHECK (date_fin > date_debut)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_exercice_entite ON exercice(entite_id);
CREATE INDEX IF NOT EXISTS idx_exercice_actif ON exercice(entite_id, cloture) WHERE cloture = false;
