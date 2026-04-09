-- ============================================
-- Fonction: refresh_views_if_needed()
-- Rafraichit les vues UNIQUEMENT si des donnees
-- ont change depuis le dernier refresh
-- ============================================

CREATE OR REPLACE FUNCTION refresh_views_if_needed()
RETURNS TABLE(refreshed BOOLEAN, reason TEXT) AS $$
DECLARE
    needs_refresh BOOLEAN := false;
    _reason TEXT := 'aucun changement detecte';
BEGIN
    -- Verifier si au moins un endpoint a ete synce depuis le dernier refresh
    SELECT EXISTS(
        SELECT 1 FROM sync_metadata
        WHERE endpoint = 'ledger_entry_lines'
          AND status = 'done'
          AND (last_refresh_at IS NULL OR last_sync_at > last_refresh_at)
    ) INTO needs_refresh;

    IF NOT needs_refresh THEN
        -- Fallback : verifier s'il y a des fec_import termines sans refresh
        SELECT EXISTS(
            SELECT 1 FROM fec_import fi
            WHERE fi.statut = 'termine'
              AND fi.date_import > COALESCE(
                  (SELECT MAX(last_refresh_at) FROM sync_metadata WHERE endpoint = 'ledger_entry_lines'),
                  '1970-01-01'::timestamptz
              )
        ) INTO needs_refresh;

        IF needs_refresh THEN
            _reason := 'fec_import detecte sans refresh';
        END IF;
    ELSE
        _reason := 'sync_metadata indique des changements';
    END IF;

    IF needs_refresh THEN
        -- Rafraichir toutes les vues dans l'ordre
        PERFORM refresh_all_views();

        -- Marquer le refresh dans sync_metadata
        UPDATE sync_metadata
        SET last_refresh_at = now()
        WHERE endpoint = 'ledger_entry_lines'
          AND status = 'done';

        RETURN QUERY SELECT true, _reason;
    ELSE
        RETURN QUERY SELECT false, _reason;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_views_if_needed() IS
    'Refresh conditionnel : ne rafraichit les vues que si des donnees ont change depuis le dernier refresh';
