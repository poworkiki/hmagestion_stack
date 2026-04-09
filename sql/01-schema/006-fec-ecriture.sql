-- ============================================
-- Table: fec_ecriture
-- Ecritures comptables au format FEC normalise
-- (Art. A.47 A-1 LPF — 18 colonnes + champs calcules)
-- ============================================

CREATE TABLE IF NOT EXISTS fec_ecriture (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entite_id UUID NOT NULL REFERENCES entite(id),
    exercice_id UUID NOT NULL REFERENCES exercice(id),
    fec_import_id UUID REFERENCES fec_import(id),

    -- 18 colonnes FEC normalisees
    journal_code TEXT NOT NULL,         -- JournalCode
    journal_lib TEXT,                   -- JournalLib
    ecriture_num TEXT NOT NULL,         -- EcritureNum
    ecriture_date DATE NOT NULL,        -- EcritureDate
    compte_num TEXT NOT NULL,           -- CompteNum (auxiliaire possible)
    compte_lib TEXT,                    -- CompteLib
    comp_aux_num TEXT,                  -- CompAuxNum
    comp_aux_lib TEXT,                  -- CompAuxLib
    piece_ref TEXT,                     -- PieceRef
    piece_date DATE,                    -- PieceDate
    ecriture_lib TEXT,                  -- EcritureLib
    debit NUMERIC(15,2) DEFAULT 0,     -- Debit
    credit NUMERIC(15,2) DEFAULT 0,    -- Credit
    ecriture_let TEXT,                  -- EcritureLet (lettrage)
    date_let DATE,                      -- DateLet
    valid_date DATE,                    -- ValidDate
    montant_devise NUMERIC(15,2),      -- MontantDevise
    idevise TEXT,                       -- Idevise (code ISO)

    -- Champs calcules
    pcg_numero TEXT,                    -- Numero PCG resolu via resolve_compte()
    hash_md5 TEXT UNIQUE NOT NULL,      -- Hash anti-doublons : MD5(entite_id || journal_code || ecriture_num || ecriture_date || compte_num || debit || credit)

    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_fec_entite_exercice ON fec_ecriture(entite_id, exercice_id);
CREATE INDEX IF NOT EXISTS idx_fec_compte ON fec_ecriture(compte_num);
CREATE INDEX IF NOT EXISTS idx_fec_pcg ON fec_ecriture(pcg_numero);
CREATE INDEX IF NOT EXISTS idx_fec_date ON fec_ecriture(ecriture_date);
-- hash_md5 a deja un index UNIQUE implicite via la contrainte

-- ============================================
-- Table: _staging_fec
-- Table temporaire pour import staging
-- Meme structure que fec_ecriture, sans contraintes
-- TRUNCATE a chaque run
-- ============================================

CREATE TABLE IF NOT EXISTS _staging_fec (
    entite_id UUID,
    exercice_id UUID,
    fec_import_id UUID,
    journal_code TEXT,
    journal_lib TEXT,
    ecriture_num TEXT,
    ecriture_date DATE,
    compte_num TEXT,
    compte_lib TEXT,
    comp_aux_num TEXT,
    comp_aux_lib TEXT,
    piece_ref TEXT,
    piece_date DATE,
    ecriture_lib TEXT,
    debit NUMERIC(15,2) DEFAULT 0,
    credit NUMERIC(15,2) DEFAULT 0,
    ecriture_let TEXT,
    date_let DATE,
    valid_date DATE,
    montant_devise NUMERIC(15,2),
    idevise TEXT,
    pcg_numero TEXT,
    hash_md5 TEXT
);
