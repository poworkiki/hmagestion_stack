-- ============================================
-- Fonction: resolve_compte()
-- Résout un numéro de compte FEC (auxiliaire)
-- vers le numéro PCG racine
-- Ex: "411CLIENT001" → "411"
--     "60110001" → "6011" → "601"
-- ============================================

CREATE OR REPLACE FUNCTION resolve_compte(p_compte_num TEXT)
RETURNS TEXT AS $$
DECLARE
    v_prefix TEXT := p_compte_num;
    v_result TEXT;
BEGIN
    -- Essayer d'abord la table de résolution explicite (prioritaire)
    SELECT pcg_numero INTO v_result
    FROM compte_resolution
    WHERE prefixe = p_compte_num
    LIMIT 1;

    IF v_result IS NOT NULL THEN
        RETURN v_result;
    END IF;

    -- Sinon, résolution par préfixe décroissant dans pcg_analytique
    WHILE length(v_prefix) >= 3 LOOP
        SELECT numero INTO v_result
        FROM pcg_analytique
        WHERE numero = v_prefix
        LIMIT 1;

        IF v_result IS NOT NULL THEN
            RETURN v_result;
        END IF;

        -- Vérifier aussi la table de résolution pour ce préfixe
        SELECT pcg_numero INTO v_result
        FROM compte_resolution
        WHERE prefixe = v_prefix
        LIMIT 1;

        IF v_result IS NOT NULL THEN
            RETURN v_result;
        END IF;

        v_prefix := left(v_prefix, length(v_prefix) - 1);
    END LOOP;

    -- Fallback : retourner les 3 premiers caractères (classe de compte)
    RETURN left(p_compte_num, 3);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Commentaire
COMMENT ON FUNCTION resolve_compte(TEXT) IS
    'Résout un numéro de compte FEC (avec auxiliaire) vers le numéro PCG racine par préfixe décroissant';
