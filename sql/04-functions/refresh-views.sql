-- ============================================
-- Fonction: refresh_all_views()
-- Rafraichit la vue materialisee mv_balance_generale
-- Toutes les autres vues sont des vues simples
-- derivees du grand livre — pas de refresh necessaire
-- ============================================

CREATE OR REPLACE FUNCTION refresh_all_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_balance_generale;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_all_views() IS
    'Rafraichit mv_balance_generale (seule vue materialisee). Les vues v_sig, v_crd, v_bilan, etc. sont des vues simples sur v_grand_livre.';
