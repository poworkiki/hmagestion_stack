-- ============================================
-- MIGRATION 003 : Correction des exercices
-- Probleme : toutes les ecritures rattachees a l'exercice 2025
--   alors que STIVMAT a des donnees 2022-2026
--   et les 4 structures ont des ecritures 2026
-- ============================================

BEGIN;

-- ============================================
-- 1. CREER LES EXERCICES MANQUANTS
-- ============================================

-- STIVMAT : exercices 2022, 2023 (historiques, clotures)
INSERT INTO exercice (entite_id, label, date_debut, date_fin, cloture)
SELECT e.id, '2022', '2022-01-01', '2022-12-31', true
FROM entite e WHERE e.code = 'STIVMAT'
ON CONFLICT DO NOTHING;

INSERT INTO exercice (entite_id, label, date_debut, date_fin, cloture)
SELECT e.id, '2023', '2023-01-01', '2023-12-31', true
FROM entite e WHERE e.code = 'STIVMAT'
ON CONFLICT DO NOTHING;

-- Exercice 2026 pour les 4 structures (en cours)
INSERT INTO exercice (entite_id, label, date_debut, date_fin, cloture)
SELECT e.id, '2026', '2026-01-01', '2026-12-31', false
FROM entite e WHERE e.code IN ('HMA', 'STIVMAT', 'STA', 'ETPA')
ON CONFLICT DO NOTHING;

-- Verification
DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count FROM exercice;
    RAISE NOTICE 'Exercices total : %', v_count;
END $$;


-- ============================================
-- 2. REAFFECTER LES ECRITURES AU BON EXERCICE
--    Logique : annee de l'ecriture = label de l'exercice
-- ============================================

-- Mise a jour exercice_id et exercice_label dans grand_livre
UPDATE grand_livre gl
SET
    exercice_id = ex.id,
    exercice_label = ex.label
FROM exercice ex
WHERE ex.entite_id = gl.entite_id
  AND ex.label = gl.annee::text
  AND (gl.exercice_label != ex.label OR gl.exercice_id != ex.id);


-- ============================================
-- 3. AUSSI CORRIGER fec_ecriture (archive legale)
-- ============================================

UPDATE fec_ecriture fe
SET exercice_id = ex.id
FROM exercice ex
WHERE ex.entite_id = fe.entite_id
  AND ex.label = EXTRACT(YEAR FROM fe.ecriture_date)::text
  AND fe.exercice_id != ex.id;


-- ============================================
-- 4. REFRESH balance_generale (les donnees ont change)
-- ============================================

REFRESH MATERIALIZED VIEW CONCURRENTLY balance_generale;


-- ============================================
-- 5. VERIFICATION
-- ============================================

DO $$
DECLARE
    rec RECORD;
    v_orphans INT;
BEGIN
    RAISE NOTICE '--- Exercices par structure ---';
    FOR rec IN
        SELECT e.code, ex.label, ex.cloture,
               (SELECT COUNT(*) FROM grand_livre gl WHERE gl.exercice_id = ex.id) AS nb
        FROM exercice ex
        JOIN entite e ON e.id = ex.entite_id
        ORDER BY e.code, ex.label
    LOOP
        RAISE NOTICE '  % | % | cloture=% | % ecritures', rec.code, rec.label, rec.cloture, rec.nb;
    END LOOP;

    -- Ecritures orphelines (exercice_label != annee)
    SELECT COUNT(*) INTO v_orphans
    FROM grand_livre
    WHERE exercice_label != annee::text;

    IF v_orphans > 0 THEN
        RAISE WARNING 'ATTENTION: % ecritures avec exercice_label != annee', v_orphans;
    ELSE
        RAISE NOTICE 'OK: toutes les ecritures sont dans le bon exercice';
    END IF;
END $$;

COMMIT;
