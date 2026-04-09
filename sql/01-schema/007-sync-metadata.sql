-- ============================================
-- Table: sync_metadata
-- Suivi de l'etat de synchronisation par structure/endpoint
-- Permet le sync incremental intelligent et le refresh conditionnel
-- ============================================

CREATE TABLE IF NOT EXISTS sync_metadata (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entite_id       UUID NOT NULL REFERENCES entite(id),
    structure_code  TEXT NOT NULL,
    endpoint        TEXT NOT NULL,           -- 'ledger_entry_lines', 'journals', 'ledger_accounts'
    last_sync_at    TIMESTAMPTZ,             -- dernier sync reussi
    last_refresh_at TIMESTAMPTZ,             -- dernier refresh des vues apres ce sync
    row_count_local INTEGER DEFAULT 0,       -- nb lignes en local apres sync
    row_count_remote INTEGER,                -- nb lignes cote Pennylane (si dispo)
    last_cursor     TEXT,                    -- dernier cursor Pennylane
    sync_duration_s NUMERIC(8,1),            -- duree du dernier sync en secondes
    status          TEXT DEFAULT 'pending',  -- 'pending', 'running', 'done', 'error', 'skipped'
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),

    UNIQUE(structure_code, endpoint)
);

CREATE INDEX IF NOT EXISTS idx_sync_metadata_status ON sync_metadata(status);
CREATE INDEX IF NOT EXISTS idx_sync_metadata_last_sync ON sync_metadata(last_sync_at);

COMMENT ON TABLE sync_metadata IS
    'Suivi incremental : etat de sync par structure/endpoint, count check, refresh conditionnel';

-- Trigger pour mettre a jour updated_at
CREATE OR REPLACE FUNCTION update_sync_metadata_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_metadata_updated ON sync_metadata;
CREATE TRIGGER trg_sync_metadata_updated
    BEFORE UPDATE ON sync_metadata
    FOR EACH ROW EXECUTE FUNCTION update_sync_metadata_timestamp();
