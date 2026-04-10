-- ============================================
-- VUE v_fec_export
-- Genere le FEC (Fichier des Ecritures Comptables)
-- au format normalise Art. A.47 A-1 du LPF
-- Source : grand_livre (table denormalisee)
--
-- Usage :
--   COPY (SELECT * FROM v_fec_export WHERE entite_code = 'STIVMAT' AND annee = 2025)
--   TO '/tmp/FEC_STIVMAT_2025.csv' WITH (FORMAT CSV, HEADER, DELIMITER E'\t');
-- ============================================

DROP VIEW IF EXISTS v_fec_export CASCADE;

CREATE VIEW v_fec_export AS
SELECT
    -- 18 colonnes FEC normalisees (Art. A.47 A-1 LPF)
    journal_code                          AS "JournalCode",
    journal_lib                           AS "JournalLib",
    ecriture_num                          AS "EcritureNum",
    TO_CHAR(ecriture_date, 'YYYYMMDD')   AS "EcritureDate",
    compte_numero                         AS "CompteNum",
    compte_libelle                        AS "CompteLib",
    comp_aux_num                          AS "CompAuxNum",
    comp_aux_lib                          AS "CompAuxLib",
    piece_ref                             AS "PieceRef",
    TO_CHAR(piece_date, 'YYYYMMDD')      AS "PieceDate",
    ecriture_lib                          AS "EcritureLib",
    debit                                 AS "Debit",
    credit                                AS "Credit",
    ecriture_let                          AS "EcritureLet",
    TO_CHAR(date_let, 'YYYYMMDD')        AS "DateLet",
    TO_CHAR(ecriture_date, 'YYYYMMDD')   AS "ValidDate",
    NULL::numeric                         AS "Montantdevise",
    NULL::text                            AS "Idevise",
    -- Colonnes supplementaires pour le filtrage (pas dans le FEC final)
    entite_code,
    exercice_label,
    annee
FROM grand_livre
ORDER BY journal_code, ecriture_date, ecriture_num;

COMMENT ON VIEW v_fec_export IS 'FEC normalise (Art. A.47 A-1 LPF) genere depuis grand_livre. Filtrer par entite_code + annee avant export.';
