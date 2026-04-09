-- ============================================
-- TABLE grand_livre
-- Données brutes Pennylane enrichies (PCG + calendrier)
-- Remplace fec_ecriture comme source unique
-- ============================================

CREATE TABLE IF NOT EXISTS grand_livre (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identifiants Pennylane (bruts, sans transformation FEC)
    pennylane_line_id   BIGINT NOT NULL,          -- /ledger_entry_lines.id (clé de dédup)
    pennylane_entry_id  BIGINT,                   -- /ledger_entry_lines.ledger_entry.id

    -- Entité / Exercice (dénormalisé)
    entite_id           UUID NOT NULL REFERENCES entite(id),
    exercice_id         UUID NOT NULL REFERENCES exercice(id),
    entite_nom          TEXT NOT NULL,
    exercice_label      TEXT NOT NULL,

    -- Calendrier (pré-jointé depuis dim_calendrier)
    ecriture_date       DATE NOT NULL,
    annee               SMALLINT NOT NULL,
    trimestre           TEXT NOT NULL,             -- 'T1', 'T2', 'T3', 'T4'
    mois                SMALLINT NOT NULL,
    mois_label          TEXT NOT NULL,             -- '2026-01', '2026-02'...
    mois_nom            TEXT NOT NULL,             -- 'Janvier', 'Février'...
    semaine             SMALLINT NOT NULL,
    debut_mois          DATE NOT NULL,

    -- Écriture comptable
    journal_code        TEXT NOT NULL,
    journal_lib         TEXT,
    ecriture_num        TEXT,
    compte_numero       TEXT,                      -- pcg_numero résolu
    compte_libelle      TEXT,
    classe              SMALLINT,
    comp_aux_num        TEXT,
    comp_aux_lib        TEXT,
    piece_ref           TEXT,
    piece_date          DATE,
    ecriture_lib        TEXT,
    debit               NUMERIC(15,2) NOT NULL DEFAULT 0,
    credit              NUMERIC(15,2) NOT NULL DEFAULT 0,
    solde               NUMERIC(15,2) GENERATED ALWAYS AS (debit - credit) STORED,
    ecriture_let        TEXT,
    date_let            DATE,

    -- Mapping PCG analytique (pré-jointé depuis pcg_analytique)
    sig_solde           TEXT,
    sig_signe           SMALLINT,
    cr_rubrique         TEXT,
    cr_signe            SMALLINT,
    bilan_poste         TEXT,
    bilan_section       TEXT,
    bf_categorie        TEXT,
    nature_defaut       TEXT,
    crd_ordre           SMALLINT,
    crd_categorie       TEXT,
    crd_rubrique        TEXT,
    crd_signe           SMALLINT,

    -- Flags
    is_a_nouveau        BOOLEAN NOT NULL DEFAULT false,

    -- Métadonnées
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Contrainte unicité : 1 ligne Pennylane = 1 ligne grand_livre par entité
    CONSTRAINT uq_grand_livre_pennylane UNIQUE (entite_id, pennylane_line_id)
);

-- Index pour les requêtes Superset
CREATE INDEX IF NOT EXISTS idx_gl_entite          ON grand_livre (entite_id);
CREATE INDEX IF NOT EXISTS idx_gl_exercice        ON grand_livre (exercice_id);
CREATE INDEX IF NOT EXISTS idx_gl_date            ON grand_livre (ecriture_date);
CREATE INDEX IF NOT EXISTS idx_gl_compte          ON grand_livre (compte_numero);
CREATE INDEX IF NOT EXISTS idx_gl_annee_mois      ON grand_livre (annee, mois);
CREATE INDEX IF NOT EXISTS idx_gl_journal         ON grand_livre (journal_code);
CREATE INDEX IF NOT EXISTS idx_gl_entite_annee    ON grand_livre (entite_id, annee);
CREATE INDEX IF NOT EXISTS idx_gl_sig             ON grand_livre (sig_solde) WHERE sig_solde IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_gl_crd             ON grand_livre (crd_ordre) WHERE crd_ordre IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_gl_bilan           ON grand_livre (bilan_poste) WHERE bilan_poste IS NOT NULL;

COMMENT ON TABLE grand_livre IS 'Grand Livre — données brutes Pennylane enrichies PCG + calendrier. Source unique pour toutes les vues.';
COMMENT ON COLUMN grand_livre.pennylane_line_id IS 'ID original de /ledger_entry_lines (clé de déduplication)';
COMMENT ON COLUMN grand_livre.solde IS 'Calculé automatiquement : debit - credit';
