"""Couche acces donnees — requetes SQL vers PostgreSQL HMA (lecture seule)."""

import os
import pandas as pd
import psycopg2
import psycopg2.extras

HMA_DB_URL = os.environ.get("HMA_DB_URL", "")


def _get_conn():
    """Retourne une connexion PostgreSQL."""
    return psycopg2.connect(HMA_DB_URL)


def _query(sql, params=None):
    """Execute une requete SELECT et retourne un DataFrame pandas."""
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return pd.DataFrame(rows) if rows else pd.DataFrame()


# ── Listes de reference ──────────────────────────────────────────

def get_entites():
    """Retourne la liste des structures (id, nom)."""
    return _query("SELECT id, nom FROM entite ORDER BY id")


def get_annees():
    """Retourne les annees disponibles (distinctes depuis v_crd)."""
    df = _query("SELECT DISTINCT annee FROM v_crd ORDER BY annee DESC")
    return df["annee"].tolist()


def get_trimestres():
    """Retourne les trimestres disponibles."""
    return [1, 2, 3, 4]


# ── CRD (KPI + tableau) ─────────────────────────────────────────

def get_crd(entite_id, annee, trimestre=None):
    """CRD agrege depuis v_crd. Si trimestre=None, agrega l'annee entiere."""
    if trimestre:
        sql = """
            SELECT * FROM v_crd
            WHERE entite_id = %s::uuid AND annee = %s AND trimestre = %s
        """
        return _query(sql, (str(entite_id), annee, trimestre))
    else:
        sql = """
            SELECT entite_id, entite_nom, exercice_id, exercice_label, annee,
                SUM(ca) AS ca,
                SUM(charges_variables) AS charges_variables,
                SUM(mcv) AS mcv,
                SUM(charges_fixes) AS charges_fixes,
                SUM(resultat_exploitation) AS resultat_exploitation,
                SUM(resultat_financier) AS resultat_financier,
                SUM(rcai) AS rcai,
                SUM(resultat_exceptionnel) AS resultat_exceptionnel,
                SUM(impot_sur_societes) AS impot_sur_societes,
                SUM(resultat_net) AS resultat_net,
                SUM(dap) AS dap, SUM(rap) AS rap,
                SUM(vceac) AS vceac, SUM(pcea) AS pcea,
                SUM(caf) AS caf,
                CASE WHEN SUM(ca) != 0
                    THEN ROUND(SUM(charges_variables)/SUM(ca)*100, 1)
                    ELSE 0 END AS pct_charges_var,
                CASE WHEN SUM(ca) != 0
                    THEN ROUND(SUM(mcv)/SUM(ca)*100, 1)
                    ELSE 0 END AS pct_mcv,
                CASE WHEN SUM(ca) != 0
                    THEN ROUND(SUM(charges_fixes)/SUM(ca)*100, 1)
                    ELSE 0 END AS pct_charges_fixes,
                CASE WHEN SUM(ca) != 0
                    THEN ROUND(SUM(resultat_exploitation)/SUM(ca)*100, 1)
                    ELSE 0 END AS pct_res_exploit,
                CASE WHEN SUM(ca) != 0
                    THEN ROUND(SUM(rcai)/SUM(ca)*100, 1)
                    ELSE 0 END AS pct_rcai,
                CASE WHEN SUM(ca) != 0
                    THEN ROUND(SUM(resultat_net)/SUM(ca)*100, 1)
                    ELSE 0 END AS pct_res_net,
                CASE WHEN SUM(ca) != 0
                    THEN ROUND(SUM(caf)/SUM(ca)*100, 1)
                    ELSE 0 END AS pct_caf,
                CASE WHEN SUM(ca) != 0 AND SUM(mcv) != 0
                    THEN ROUND(SUM(charges_fixes)/(SUM(mcv)/SUM(ca)), 2)
                    ELSE 0 END AS seuil_rentabilite,
                CASE WHEN SUM(ca) != 0 AND SUM(mcv) != 0
                    THEN ROUND((SUM(charges_fixes)/(SUM(mcv)/SUM(ca)))/SUM(ca)*365, 1)
                    ELSE 0 END AS point_mort_jours,
                CASE WHEN SUM(ca) != 0 AND SUM(mcv) != 0
                    THEN SUM(ca) - ROUND(SUM(charges_fixes)/(SUM(mcv)/SUM(ca)), 2)
                    ELSE 0 END AS marge_securite,
                CASE WHEN SUM(ca) != 0 AND SUM(mcv) != 0
                    THEN ROUND((SUM(ca) - ROUND(SUM(charges_fixes)/(SUM(mcv)/SUM(ca)), 2))/SUM(ca)*100, 1)
                    ELSE 0 END AS pct_marge_securite
            FROM v_crd
            WHERE entite_id = %s::uuid AND annee = %s
            GROUP BY entite_id, entite_nom, exercice_id, exercice_label, annee
        """
        return _query(sql, (str(entite_id), annee))


def get_crd_reference(entite_id, annee, trimestre, ref_type):
    """Retourne le CRD de la periode de reference pour calcul d'evolution.

    ref_type: "trim_prec", "n-1", "n-2", "mois_prec"
    """
    if ref_type == "n-1":
        return get_crd(entite_id, annee - 1, trimestre)
    elif ref_type == "n-2":
        return get_crd(entite_id, annee - 2, trimestre)
    elif ref_type == "trim_prec":
        if trimestre and trimestre > 1:
            return get_crd(entite_id, annee, trimestre - 1)
        elif trimestre == 1:
            return get_crd(entite_id, annee - 1, 4)
        else:
            return get_crd(entite_id, annee - 1)
    else:
        return get_crd(entite_id, annee - 1, trimestre)


# ── CRD Drilldown ───────────────────────────────────────────────

def get_crd_drilldown(entite_id, annee, trimestre=None,
                      categorie=None, rubrique=None):
    """Detail CRD depuis v_crd_drilldown. Filtres optionnels par categorie/rubrique."""
    conditions = ["entite_id = %s::uuid", "annee = %s"]
    params = [str(entite_id), annee]

    if trimestre:
        conditions.append("trimestre = %s")
        params.append(trimestre)
    if categorie:
        conditions.append("crd_categorie = %s")
        params.append(categorie)
    if rubrique:
        conditions.append("crd_rubrique = %s")
        params.append(rubrique)

    where = " AND ".join(conditions)

    if rubrique:
        # Niveau 3 : comptes PCG
        sql = f"""
            SELECT compte_numero, compte_libelle, SUM(montant) AS total
            FROM v_crd_drilldown
            WHERE {where}
            GROUP BY compte_numero, compte_libelle
            ORDER BY ABS(SUM(montant)) DESC
        """
    elif categorie:
        # Niveau 2 : rubriques
        sql = f"""
            SELECT crd_rubrique, SUM(montant) AS total
            FROM v_crd_drilldown
            WHERE {where}
            GROUP BY crd_rubrique
            ORDER BY ABS(SUM(montant)) DESC
        """
    else:
        # Niveau 1 : categories
        sql = f"""
            SELECT crd_ordre, crd_categorie, SUM(montant) AS total
            FROM v_crd_drilldown
            WHERE {where}
            GROUP BY crd_ordre, crd_categorie
            ORDER BY crd_ordre
        """

    return _query(sql, params)


# ── YTD Mensuel (courbes) ───────────────────────────────────────

def get_ytd_mensuel(entite_id, annee):
    """Evolution mensuelle depuis v_ytd_mensuel."""
    sql = """
        SELECT * FROM v_ytd_mensuel
        WHERE entite_id = %s::uuid AND annee = %s
        ORDER BY mois
    """
    return _query(sql, (str(entite_id), annee))


# ── Comparaison multi-structures ────────────────────────────────

def get_crd_multi(entite_ids, annee, trimestre=None):
    """CRD pour plusieurs structures (comparaison)."""
    placeholders = ",".join(["%s::uuid"] * len(entite_ids))
    params = [str(eid) for eid in entite_ids] + [annee]

    if trimestre:
        sql = f"""
            SELECT * FROM v_crd
            WHERE entite_id IN ({placeholders}) AND annee = %s AND trimestre = %s
        """
        params.append(trimestre)
    else:
        sql = f"""
            SELECT entite_id, entite_nom, annee,
                SUM(ca) AS ca, SUM(mcv) AS mcv,
                SUM(resultat_exploitation) AS resultat_exploitation,
                SUM(resultat_net) AS resultat_net, SUM(caf) AS caf
            FROM v_crd
            WHERE entite_id IN ({placeholders}) AND annee = %s
            GROUP BY entite_id, entite_nom, annee
        """

    return _query(sql, params)
