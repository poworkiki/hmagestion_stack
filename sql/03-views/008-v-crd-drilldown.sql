DROP VIEW IF EXISTS v_crd_drilldown CASCADE;

CREATE VIEW v_crd_drilldown AS
WITH base AS (
    SELECT
        bg.entite_id,
        ent.nom AS entite_nom,
        bg.exercice_id,
        ex.label AS exercice_label,
        bg.mois,
        TO_CHAR(bg.mois, 'MM - Mon') AS mois_label,
        EXTRACT(YEAR FROM bg.mois)::int AS annee,
        CASE
            WHEN EXTRACT(MONTH FROM bg.mois) <= 3 THEN 'T1'
            WHEN EXTRACT(MONTH FROM bg.mois) <= 6 THEN 'T2'
            WHEN EXTRACT(MONTH FROM bg.mois) <= 9 THEN 'T3'
            ELSE 'T4'
        END AS trimestre,
        p.numero AS compte_numero,
        p.libelle AS compte_libelle,
        p.nature_defaut,
        CASE
            WHEN p.numero ~ '^70[1-8]' OR p.numero LIKE '707%' OR p.numero ~ '^709' THEN '01. Chiffre d affaires'
            WHEN p.classe IN (6, 7) AND p.nature_defaut = 'variable' THEN '02. Charges variables'
            WHEN p.classe = 6 AND p.nature_defaut = 'fixe'
                AND p.numero NOT LIKE '66%' AND p.numero NOT LIKE '67%'
                AND p.numero NOT LIKE '695%' AND p.numero NOT LIKE '691%'
                AND p.numero NOT LIKE '681%' AND p.numero NOT LIKE '686%' AND p.numero NOT LIKE '687%'
                AND p.numero NOT LIKE '675%' THEN '04. Charges fixes exploitation'
            WHEN p.numero LIKE '76%' OR p.numero LIKE '66%' THEN '06. Resultat financier'
            WHEN p.numero LIKE '77%' OR p.numero LIKE '67%' THEN '08. Resultat exceptionnel'
            WHEN p.numero LIKE '695%' OR p.numero LIKE '691%' THEN '09. Impot sur les societes'
            WHEN p.numero LIKE '681%' OR p.numero LIKE '686%' OR p.numero LIKE '687%' THEN '11. DAP (dotations)'
            WHEN p.numero LIKE '781%' OR p.numero LIKE '786%' OR p.numero LIKE '787%' THEN '12. RAP (reprises)'
            WHEN p.numero LIKE '675%' THEN '13. VCEAC (cessions)'
            WHEN p.numero LIKE '775%' THEN '14. PCEA (produits cessions)'
            ELSE '99. Autres'
        END AS crd_rubrique,
        COALESCE(p.cr_rubrique, 'Autre') AS sous_rubrique,
        CASE
            WHEN p.numero ~ '^70' THEN bg.total_credit - bg.total_debit
            WHEN p.numero LIKE '76%' OR p.numero LIKE '77%'
                OR p.numero LIKE '781%' OR p.numero LIKE '786%' OR p.numero LIKE '787%'
                OR p.numero LIKE '775%' THEN bg.total_credit - bg.total_debit
            ELSE bg.total_debit - bg.total_credit
        END AS montant
    FROM mv_balance_generale bg
    JOIN pcg_analytique p ON p.numero = bg.pcg_numero
    JOIN entite ent ON ent.id = bg.entite_id
    JOIN exercice ex ON ex.id = bg.exercice_id
    WHERE p.classe IN (6, 7)
)
SELECT
    entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label,
    crd_rubrique, sous_rubrique,
    compte_numero, compte_libelle, nature_defaut,
    SUM(montant) AS montant
FROM base
GROUP BY entite_id, entite_nom, exercice_id, exercice_label,
    annee, trimestre, mois, mois_label,
    crd_rubrique, sous_rubrique, compte_numero, compte_libelle, nature_defaut
HAVING SUM(montant) != 0;
