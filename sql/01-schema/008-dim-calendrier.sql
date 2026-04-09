-- ============================================
-- Table de dimension : dim_calendrier
-- Mapping date → annee, trimestre, mois, semaine
-- Generee pour 2020-2030 (couvre tous les exercices)
-- ============================================

CREATE TABLE IF NOT EXISTS dim_calendrier (
    date_jour DATE PRIMARY KEY,
    annee INT NOT NULL,
    trimestre TEXT NOT NULL,          -- 'T1', 'T2', 'T3', 'T4'
    mois INT NOT NULL,               -- 1..12
    mois_label TEXT NOT NULL,         -- '01 - Jan', '02 - Fev', ...
    mois_nom TEXT NOT NULL,           -- 'Janvier', 'Fevrier', ...
    semaine INT NOT NULL,             -- 1..53
    jour_semaine INT NOT NULL,        -- 1=lundi..7=dimanche (ISO)
    jour_semaine_nom TEXT NOT NULL,   -- 'Lundi', 'Mardi', ...
    debut_mois DATE NOT NULL,         -- 1er jour du mois
    fin_mois DATE NOT NULL,           -- dernier jour du mois
    debut_trimestre DATE NOT NULL,
    fin_trimestre DATE NOT NULL
);

-- Peupler : 2020-01-01 → 2030-12-31
INSERT INTO dim_calendrier
SELECT
    d::date AS date_jour,
    EXTRACT(YEAR FROM d)::int AS annee,
    'T' || EXTRACT(QUARTER FROM d)::int AS trimestre,
    EXTRACT(MONTH FROM d)::int AS mois,
    TO_CHAR(d, 'MM') || ' - ' || INITCAP(TO_CHAR(d, 'Mon')) AS mois_label,
    INITCAP(TO_CHAR(d, 'Month')) AS mois_nom,
    EXTRACT(WEEK FROM d)::int AS semaine,
    EXTRACT(ISODOW FROM d)::int AS jour_semaine,
    INITCAP(TO_CHAR(d, 'Day')) AS jour_semaine_nom,
    DATE_TRUNC('month', d)::date AS debut_mois,
    (DATE_TRUNC('month', d) + INTERVAL '1 month - 1 day')::date AS fin_mois,
    DATE_TRUNC('quarter', d)::date AS debut_trimestre,
    (DATE_TRUNC('quarter', d) + INTERVAL '3 months - 1 day')::date AS fin_trimestre
FROM generate_series('2020-01-01'::date, '2030-12-31'::date, '1 day') d
ON CONFLICT (date_jour) DO NOTHING;

-- Index
CREATE INDEX IF NOT EXISTS idx_cal_annee ON dim_calendrier(annee);
CREATE INDEX IF NOT EXISTS idx_cal_mois ON dim_calendrier(annee, mois);
CREATE INDEX IF NOT EXISTS idx_cal_trimestre ON dim_calendrier(annee, trimestre);
