-- ============================================
-- MIGRATION 004 : Suppression de fec_ecriture
-- Remplacee par grand_livre + v_fec_export
--
-- fec_ecriture etait un doublon de grand_livre (26 MB).
-- Le FEC legal est maintenant genere a la demande via v_fec_export.
-- ============================================

BEGIN;

-- 1. Creer la vue FEC export AVANT de supprimer la table
DROP VIEW IF EXISTS v_fec_export CASCADE;

CREATE VIEW v_fec_export AS
SELECT
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
    entite_code,
    exercice_label,
    annee
FROM grand_livre
ORDER BY journal_code, ecriture_date, ecriture_num;

-- 2. Supprimer les tables obsoletes
DROP TABLE IF EXISTS _staging_fec CASCADE;
DROP TABLE IF EXISTS fec_ecriture CASCADE;

-- 3. Supprimer la fonction resolve_compte (n'est plus utilisee)
DROP FUNCTION IF EXISTS resolve_compte(text) CASCADE;

-- 4. Supprimer la table compte_resolution (vide, liee a resolve_compte)
DROP TABLE IF EXISTS compte_resolution CASCADE;

-- 5. Verification
DO $$
DECLARE
    v_fec_count INT;
    v_tables TEXT[];
BEGIN
    SELECT COUNT(*) INTO v_fec_count FROM v_fec_export LIMIT 1;
    RAISE NOTICE 'v_fec_export OK (% lignes)', v_fec_count;

    SELECT ARRAY_AGG(tablename ORDER BY tablename) INTO v_tables
    FROM pg_tables WHERE schemaname = 'public';
    RAISE NOTICE 'Tables restantes : %', v_tables;

    IF 'fec_ecriture' = ANY(v_tables) THEN
        RAISE WARNING 'fec_ecriture toujours presente !';
    ELSE
        RAISE NOTICE 'fec_ecriture supprimee avec succes';
    END IF;
END $$;

COMMIT;
