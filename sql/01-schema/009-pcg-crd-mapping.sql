-- ============================================
-- Extension pcg_analytique : mapping CRD
-- Compte de Resultat Differentiel
-- Categorie → Rubrique → Sous-rubrique
-- ============================================

-- Nouvelles colonnes CRD
ALTER TABLE pcg_analytique ADD COLUMN IF NOT EXISTS crd_categorie TEXT;
ALTER TABLE pcg_analytique ADD COLUMN IF NOT EXISTS crd_rubrique TEXT;
ALTER TABLE pcg_analytique ADD COLUMN IF NOT EXISTS crd_signe SMALLINT;

-- Index
CREATE INDEX IF NOT EXISTS idx_pcg_crd ON pcg_analytique(crd_categorie) WHERE crd_categorie IS NOT NULL;

-- ============================================
-- Peuplement du mapping CRD
-- Logique : CA → Charges variables → MCV → Charges fixes → Res exploit
--           → Res financier → RCAI → Res exceptionnel → IS → Res net
--           → DAP/RAP/VCEAC/PCEA → CAF
-- ============================================

-- 01. Chiffre d'affaires (comptes 70x)
UPDATE pcg_analytique SET
    crd_categorie = 'Chiffre d''affaires',
    crd_rubrique = 'Ventes de marchandises',
    crd_signe = 1
WHERE numero LIKE '707%';

UPDATE pcg_analytique SET
    crd_categorie = 'Chiffre d''affaires',
    crd_rubrique = 'Production vendue',
    crd_signe = 1
WHERE numero ~ '^70[1-6]' OR numero LIKE '708%';

UPDATE pcg_analytique SET
    crd_categorie = 'Chiffre d''affaires',
    crd_rubrique = 'RRR accordes',
    crd_signe = -1
WHERE numero ~ '^709';

-- 02. Charges variables (nature_defaut = 'variable', classes 6-7)
UPDATE pcg_analytique SET
    crd_categorie = 'Charges variables',
    crd_rubrique = CASE
        WHEN numero LIKE '601%' OR numero LIKE '602%' THEN 'Achats matieres premieres'
        WHEN numero LIKE '604%' OR numero LIKE '605%' THEN 'Achats etudes et prestations'
        WHEN numero LIKE '606%' THEN 'Fournitures non stockables'
        WHEN numero LIKE '607%' THEN 'Achats de marchandises'
        WHEN numero LIKE '6037%' OR numero LIKE '6031%' OR numero LIKE '6032%' THEN 'Variation de stocks'
        WHEN numero LIKE '611%' THEN 'Sous-traitance generale'
        WHEN numero LIKE '624%' THEN 'Transports'
        WHEN numero LIKE '713%' THEN 'Variation stocks produits'
        ELSE 'Autres charges variables'
    END,
    crd_signe = -1
WHERE nature_defaut = 'variable' AND classe IN (6, 7)
  AND crd_categorie IS NULL;

-- 04. Charges fixes exploitation
UPDATE pcg_analytique SET
    crd_categorie = 'Charges fixes exploitation',
    crd_rubrique = CASE
        WHEN numero LIKE '613%' THEN 'Locations'
        WHEN numero LIKE '615%' THEN 'Entretien et reparations'
        WHEN numero LIKE '616%' THEN 'Assurances'
        WHEN numero LIKE '622%' OR numero LIKE '626%' THEN 'Honoraires et telecom'
        WHEN numero LIKE '623%' THEN 'Publicite et relations publiques'
        WHEN numero LIKE '625%' THEN 'Deplacements et missions'
        WHEN numero LIKE '627%' OR numero LIKE '628%' THEN 'Services bancaires et divers'
        WHEN numero LIKE '631%' OR numero LIKE '633%' OR numero LIKE '635%' THEN 'Impots et taxes'
        WHEN numero LIKE '641%' OR numero LIKE '642%' OR numero LIKE '643%' OR numero LIKE '644%' THEN 'Remunerations du personnel'
        WHEN numero LIKE '645%' OR numero LIKE '646%' OR numero LIKE '647%' OR numero LIKE '648%' THEN 'Charges sociales'
        WHEN numero LIKE '651%' OR numero LIKE '654%' OR numero LIKE '658%' THEN 'Autres charges de gestion'
        WHEN numero LIKE '74%' THEN 'Subventions exploitation'
        ELSE 'Autres charges fixes'
    END,
    crd_signe = CASE WHEN numero LIKE '74%' THEN 1 ELSE -1 END
WHERE classe = 6 AND nature_defaut = 'fixe'
  AND numero NOT LIKE '66%' AND numero NOT LIKE '67%'
  AND numero NOT LIKE '695%' AND numero NOT LIKE '691%'
  AND numero NOT LIKE '681%' AND numero NOT LIKE '686%' AND numero NOT LIKE '687%'
  AND numero NOT LIKE '675%'
  AND crd_categorie IS NULL;

-- Subventions exploitation (classe 7, fixe)
UPDATE pcg_analytique SET
    crd_categorie = 'Charges fixes exploitation',
    crd_rubrique = 'Subventions exploitation',
    crd_signe = 1
WHERE numero LIKE '74%' AND crd_categorie IS NULL;

-- 06. Resultat financier
UPDATE pcg_analytique SET
    crd_categorie = 'Resultat financier',
    crd_rubrique = CASE
        WHEN numero LIKE '76%' THEN 'Produits financiers'
        WHEN numero LIKE '66%' THEN 'Charges financieres'
        WHEN numero LIKE '686%' THEN 'DAP financieres'
        WHEN numero LIKE '786%' THEN 'RAP financieres'
        ELSE 'Autres financiers'
    END,
    crd_signe = CASE WHEN numero LIKE '76%' OR numero LIKE '786%' THEN 1 ELSE -1 END
WHERE (numero LIKE '66%' OR numero LIKE '76%') AND crd_categorie IS NULL;

-- 08. Resultat exceptionnel
UPDATE pcg_analytique SET
    crd_categorie = 'Resultat exceptionnel',
    crd_rubrique = CASE
        WHEN numero LIKE '77%' AND numero NOT LIKE '775%' AND numero NOT LIKE '777%' THEN 'Produits exceptionnels'
        WHEN numero LIKE '67%' AND numero NOT LIKE '675%' THEN 'Charges exceptionnelles'
        WHEN numero LIKE '687%' THEN 'DAP exceptionnelles'
        WHEN numero LIKE '787%' THEN 'RAP exceptionnelles'
        ELSE 'Autres exceptionnels'
    END,
    crd_signe = CASE WHEN numero LIKE '77%' OR numero LIKE '787%' THEN 1 ELSE -1 END
WHERE (numero LIKE '67%' OR numero LIKE '77%')
  AND numero NOT LIKE '675%' AND numero NOT LIKE '775%'
  AND crd_categorie IS NULL;

-- 09. IS et participation
UPDATE pcg_analytique SET
    crd_categorie = 'Impot sur les societes',
    crd_rubrique = CASE
        WHEN numero LIKE '695%' THEN 'Impot sur les benefices'
        WHEN numero LIKE '691%' THEN 'Participation des salaries'
        ELSE 'Autres impots'
    END,
    crd_signe = -1
WHERE (numero LIKE '695%' OR numero LIKE '691%') AND crd_categorie IS NULL;

-- 11. DAP (dotations amortissements/provisions)
UPDATE pcg_analytique SET
    crd_categorie = 'CAF - Dotations',
    crd_rubrique = CASE
        WHEN numero LIKE '681%' THEN 'DAP exploitation'
        WHEN numero LIKE '686%' THEN 'DAP financieres'
        WHEN numero LIKE '687%' THEN 'DAP exceptionnelles'
        ELSE 'Autres dotations'
    END,
    crd_signe = -1
WHERE (numero LIKE '681%' OR numero LIKE '686%' OR numero LIKE '687%') AND crd_categorie IS NULL;

-- 12. RAP (reprises amortissements/provisions)
UPDATE pcg_analytique SET
    crd_categorie = 'CAF - Reprises',
    crd_rubrique = CASE
        WHEN numero LIKE '781%' THEN 'RAP exploitation'
        WHEN numero LIKE '786%' THEN 'RAP financieres'
        WHEN numero LIKE '787%' THEN 'RAP exceptionnelles'
        ELSE 'Autres reprises'
    END,
    crd_signe = 1
WHERE (numero LIKE '781%' OR numero LIKE '786%' OR numero LIKE '787%') AND crd_categorie IS NULL;

-- 13. VCEAC (valeur comptable elements actif cedes)
UPDATE pcg_analytique SET
    crd_categorie = 'CAF - Cessions',
    crd_rubrique = 'VCEAC',
    crd_signe = -1
WHERE numero LIKE '675%' AND crd_categorie IS NULL;

-- 14. PCEA (produits cessions elements actif)
UPDATE pcg_analytique SET
    crd_categorie = 'CAF - Cessions',
    crd_rubrique = 'PCEA',
    crd_signe = 1
WHERE numero LIKE '775%' AND crd_categorie IS NULL;

-- Quote-part subventions investissement virees
UPDATE pcg_analytique SET
    crd_categorie = 'CAF - Cessions',
    crd_rubrique = 'Quote-part subventions',
    crd_signe = 1
WHERE numero LIKE '777%' AND crd_categorie IS NULL;

-- Verification
SELECT crd_categorie, COUNT(*) AS nb_comptes,
       COUNT(DISTINCT crd_rubrique) AS nb_rubriques
FROM pcg_analytique
WHERE crd_categorie IS NOT NULL
GROUP BY crd_categorie
ORDER BY crd_categorie;
