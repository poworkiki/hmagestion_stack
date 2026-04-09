-- ============================================
-- MIGRATION : fec_ecriture → grand_livre
-- One-shot : peuple grand_livre depuis les données existantes
-- Exécuter APRÈS 011-grand-livre.sql
-- ============================================

-- Vider grand_livre avant migration
TRUNCATE TABLE grand_livre;

-- Migration : même logique que l'ancienne vue v_grand_livre
-- mais INSERT dans la table au lieu de SELECT à la volée
INSERT INTO grand_livre (
    pennylane_line_id, pennylane_entry_id,
    entite_id, exercice_id, entite_nom, exercice_label,
    ecriture_date, annee, trimestre, mois,
    mois_label, mois_nom, semaine, debut_mois,
    journal_code, journal_lib, ecriture_num,
    compte_numero, compte_libelle, classe,
    comp_aux_num, comp_aux_lib,
    piece_ref, piece_date, ecriture_lib,
    debit, credit,
    ecriture_let, date_let,
    sig_solde, sig_signe,
    cr_rubrique, cr_signe,
    bilan_poste, bilan_section,
    bf_categorie, nature_defaut,
    crd_ordre, crd_categorie,
    crd_rubrique, crd_signe,
    is_a_nouveau
)
SELECT
    -- pennylane_line_id : utilise l'ID fec_ecriture converti en bigint via hashtext
    -- (les anciennes lignes n'ont pas de pennylane_line_id, on génère un ID stable)
    ABS(hashtext(e.hash_md5::text))::bigint AS pennylane_line_id,
    -- pennylane_entry_id : extraire depuis ecriture_num si numérique
    CASE WHEN e.ecriture_num ~ '^\d+$' THEN e.ecriture_num::bigint ELSE NULL END,
    -- Entité / Exercice
    e.entite_id, e.exercice_id,
    ent.nom, ex.label,
    -- Calendrier
    e.ecriture_date,
    cal.annee, cal.trimestre, cal.mois,
    cal.mois_label, cal.mois_nom, cal.semaine, cal.debut_mois,
    -- Écriture
    e.journal_code, e.journal_lib, e.ecriture_num,
    e.pcg_numero,
    COALESCE(p.libelle, e.compte_lib),
    COALESCE(p.classe, CAST(LEFT(e.pcg_numero, 1) AS smallint)),
    e.comp_aux_num, e.comp_aux_lib,
    e.piece_ref, e.piece_date, e.ecriture_lib,
    e.debit, e.credit,
    e.ecriture_let, e.date_let,
    -- PCG analytique
    p.sig_solde, p.sig_signe,
    p.cr_rubrique, p.cr_signe,
    p.bilan_poste, p.bilan_section,
    p.bf_categorie, p.nature_defaut,
    p.crd_ordre, p.crd_categorie,
    p.crd_rubrique, p.crd_signe,
    -- Flag
    CASE WHEN e.journal_code IN ('AN', 'OD-AN', 'RAN') THEN true ELSE false END
FROM fec_ecriture e
JOIN entite ent ON ent.id = e.entite_id
JOIN exercice ex ON ex.id = e.exercice_id
JOIN dim_calendrier cal ON cal.date_jour = e.ecriture_date
LEFT JOIN pcg_analytique p ON p.numero = e.pcg_numero;

-- Statistiques
DO $$
DECLARE
    v_count bigint;
    v_fec_count bigint;
BEGIN
    SELECT COUNT(*) INTO v_count FROM grand_livre;
    SELECT COUNT(*) INTO v_fec_count FROM fec_ecriture;
    RAISE NOTICE '=== MIGRATION TERMINÉE ===';
    RAISE NOTICE 'fec_ecriture: % lignes', v_fec_count;
    RAISE NOTICE 'grand_livre:  % lignes', v_count;
    IF v_count = v_fec_count THEN
        RAISE NOTICE 'OK — count identique';
    ELSE
        RAISE WARNING 'ATTENTION — écart de % lignes (dates hors dim_calendrier ?)', v_fec_count - v_count;
    END IF;
END $$;
