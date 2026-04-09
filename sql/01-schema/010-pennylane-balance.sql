-- ============================================
-- Table: pennylane_balance
-- Snapshot de la trial_balance Pennylane
-- Source de verite pour controle de coherence
-- ============================================

CREATE TABLE IF NOT EXISTS pennylane_balance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entite_id UUID NOT NULL REFERENCES entite(id),
    structure_code TEXT NOT NULL,       -- HMA, STIVMAT, STA, ETPA
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    compte_numero TEXT NOT NULL,
    compte_libelle TEXT,
    total_debit NUMERIC DEFAULT 0,
    total_credit NUMERIC DEFAULT 0,
    solde NUMERIC DEFAULT 0,           -- credit - debit (convention Pennylane)
    imported_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(entite_id, period_start, period_end, compte_numero)
);

CREATE INDEX IF NOT EXISTS idx_pb_entite ON pennylane_balance(entite_id);
CREATE INDEX IF NOT EXISTS idx_pb_structure ON pennylane_balance(structure_code);
CREATE INDEX IF NOT EXISTS idx_pb_periode ON pennylane_balance(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_pb_compte ON pennylane_balance(compte_numero);

-- ============================================
-- Vue: v_controle_balance
-- Compare GL (fec_ecriture) vs Pennylane (pennylane_balance)
-- Detecte les ecarts automatiquement
-- ============================================

CREATE OR REPLACE VIEW v_controle_balance AS
SELECT
    pb.structure_code,
    pb.period_start,
    pb.period_end,
    pb.compte_numero,
    pb.compte_libelle,
    -- Pennylane (source de verite)
    pb.total_debit AS pl_debit,
    pb.total_credit AS pl_credit,
    pb.solde AS pl_solde,
    -- PostgreSQL (GL recalcule)
    COALESCE(gl.gl_debit, 0) AS gl_debit,
    COALESCE(gl.gl_credit, 0) AS gl_credit,
    COALESCE(gl.gl_solde, 0) AS gl_solde,
    -- Ecarts
    COALESCE(gl.gl_solde, 0) - pb.solde AS ecart_solde,
    CASE
        WHEN ABS(COALESCE(gl.gl_solde, 0) - pb.solde) < 0.01 THEN 'OK'
        WHEN ABS(COALESCE(gl.gl_solde, 0) - pb.solde) < 1.00 THEN 'ARRONDI'
        ELSE 'ECART'
    END AS statut
FROM pennylane_balance pb
LEFT JOIN (
    SELECT
        e.entite_id,
        e.pcg_numero AS compte_numero,
        SUM(e.debit) AS gl_debit,
        SUM(e.credit) AS gl_credit,
        SUM(e.credit - e.debit) AS gl_solde
    FROM fec_ecriture e
    WHERE e.journal_code NOT IN ('AN', 'OD-AN', 'RAN')
      AND e.ecriture_date >= (SELECT MIN(period_start) FROM pennylane_balance)
      AND e.ecriture_date <= (SELECT MAX(period_end) FROM pennylane_balance)
    GROUP BY e.entite_id, e.pcg_numero
) gl ON gl.entite_id = pb.entite_id AND gl.compte_numero = pb.compte_numero;

-- Vue resumee des ecarts
CREATE OR REPLACE VIEW v_controle_resume AS
SELECT
    structure_code,
    COUNT(*) AS nb_comptes,
    COUNT(*) FILTER (WHERE statut = 'OK') AS nb_ok,
    COUNT(*) FILTER (WHERE statut = 'ARRONDI') AS nb_arrondi,
    COUNT(*) FILTER (WHERE statut = 'ECART') AS nb_ecart,
    ROUND(SUM(ABS(ecart_solde))::numeric, 2) AS ecart_total
FROM v_controle_balance
GROUP BY structure_code
ORDER BY structure_code;
