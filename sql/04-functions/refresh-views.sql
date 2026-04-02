-- ============================================
-- Fonction: refresh_all_views()
-- Rafraichit toutes les vues materialisees
-- dans le bon ordre de dependance
-- ============================================

CREATE OR REPLACE FUNCTION refresh_all_views()
RETURNS void AS $$
BEGIN
    -- Niveau 1 : balance generale (base de toutes les autres)
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_balance_generale;

    -- Niveau 2 : vues qui dependent de la balance (paralleles entre elles)
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_bilan;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_compte_resultat;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_sig;

    -- Niveau 3 : vues qui dependent du bilan ou du CR
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_bilan_fonctionnel;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_resultat_differentiel;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_all_views() IS
    'Rafraichit les 6 vues materialisees dans l''ordre : balance → bilan+CR+SIG → BF+resultat diff';
