-- ============================================
-- Vue simple: v_controles_coherence
-- Controles de qualite des donnees FEC
-- Ref: docs/compta_analytique.md Annexe B
-- ============================================

-- Controle 1 : Equilibre debit/credit par ecriture
CREATE OR REPLACE VIEW v_ctrl_equilibre AS
SELECT
    entite_id,
    exercice_id,
    ecriture_num,
    ecriture_date,
    SUM(debit) AS total_debit,
    SUM(credit) AS total_credit,
    ABS(SUM(debit) - SUM(credit)) AS ecart
FROM fec_ecriture
GROUP BY entite_id, exercice_id, ecriture_num, ecriture_date
HAVING ABS(SUM(debit) - SUM(credit)) > 0.01;

-- Controle 2 : Doublons hash_md5 (ne devrait jamais arriver)
CREATE OR REPLACE VIEW v_ctrl_doublons AS
SELECT
    hash_md5,
    COUNT(*) AS nb_occurrences
FROM fec_ecriture
GROUP BY hash_md5
HAVING COUNT(*) > 1;

-- Controle 3 : Comptes non resolus (pcg_numero IS NULL)
CREATE OR REPLACE VIEW v_ctrl_comptes_non_resolus AS
SELECT
    entite_id,
    compte_num,
    COUNT(*) AS nb_ecritures,
    SUM(debit) AS total_debit,
    SUM(credit) AS total_credit
FROM fec_ecriture
WHERE pcg_numero IS NULL
GROUP BY entite_id, compte_num
ORDER BY nb_ecritures DESC;

-- Vue synthetique regroupant tous les controles
CREATE OR REPLACE VIEW v_controles_coherence AS
SELECT
    'equilibre_d_c' AS controle,
    (SELECT COUNT(*) FROM v_ctrl_equilibre) AS nb_anomalies,
    CASE WHEN (SELECT COUNT(*) FROM v_ctrl_equilibre) = 0
        THEN 'OK' ELSE 'ALERTE'
    END AS statut

UNION ALL

SELECT
    'doublons_hash' AS controle,
    (SELECT COUNT(*) FROM v_ctrl_doublons) AS nb_anomalies,
    CASE WHEN (SELECT COUNT(*) FROM v_ctrl_doublons) = 0
        THEN 'OK' ELSE 'ALERTE'
    END AS statut

UNION ALL

SELECT
    'comptes_non_resolus' AS controle,
    (SELECT COUNT(DISTINCT compte_num) FROM fec_ecriture WHERE pcg_numero IS NULL) AS nb_anomalies,
    CASE WHEN (SELECT COUNT(*) FROM fec_ecriture WHERE pcg_numero IS NULL) = 0
        THEN 'OK' ELSE 'ALERTE'
    END AS statut;
