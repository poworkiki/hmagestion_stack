"""Outils LlamaIndex SQL wrappés pour CrewAI — PostgreSQL HMA."""

from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from sqlalchemy import create_engine
from crewai.tools import tool

from app.config import settings
import app.tools_rag  # noqa: F401 — force l'initialisation LLM + embeddings

# ── Connexion PostgreSQL HMA (lazy) ──────────────────────────────────
_sql_db = None
_sql_qe_cache: dict = {}


def _get_sql_db():
    global _sql_db
    if _sql_db is None:
        pg_engine = create_engine(settings.hma_db_url)
        _sql_db = SQLDatabase(pg_engine)
    return _sql_db


def _get_sql_qe(name: str, tables: list[str]):
    if name not in _sql_qe_cache:
        _sql_qe_cache[name] = NLSQLTableQueryEngine(
            sql_database=_get_sql_db(),
            tables=tables,
        )
    return _sql_qe_cache[name]


# ── 9 outils SQL wrappés pour CrewAI ────────────────────────────────

@tool("sql_grand_livre")
def tool_sql_grand_livre(query: str) -> str:
    """Requête SQL sur le Grand Livre (table grand_livre).
    25 800+ écritures comptables brutes Pennylane enrichies PCG + calendrier.
    Colonnes : entite_nom, annee, trimestre, mois, ecriture_date, journal_code,
    compte_numero, compte_libelle, classe, ecriture_lib, debit, credit, solde,
    sig_solde, cr_rubrique, bilan_poste, crd_categorie, is_a_nouveau."""
    try:
        return str(_get_sql_qe("grand_livre", ["grand_livre", "entite", "exercice"]).query(query))
    except Exception as e:
        return f"Erreur SQL grand_livre : {e}"


@tool("sql_balance_generale")
def tool_sql_balance_generale(query: str) -> str:
    """Requête SQL sur la Balance Générale (vue matérialisée balance_generale).
    Agrégation par compte/mois : total_debit, total_credit, solde.
    Inclut mapping PCG : sig_solde, cr_rubrique, bilan_poste, crd_categorie.
    Aussi disponible : v_bg_display (solde débiteur/créditeur séparés, par année)."""
    try:
        return str(_get_sql_qe("balance_generale", ["balance_generale", "v_bg_display", "entite", "exercice"]).query(query))
    except Exception as e:
        return f"Erreur SQL balance_generale : {e}"


@tool("sql_balance")
def tool_sql_balance(query: str) -> str:
    """Requête SQL sur la balance auxiliaire.
    Soldes par tiers (fournisseurs 401xxx, clients 411xxx)."""
    try:
        return str(_get_sql_qe("balance", ["balance_generale", "v_balance_auxiliaire", "entite", "exercice"]).query(query))
    except Exception as e:
        return f"Erreur SQL balance : {e}"


@tool("sql_sig")
def tool_sql_sig(query: str) -> str:
    """Requête SQL sur les 9 Soldes Intermédiaires de Gestion + CAF.
    Marge commerciale, Production, VA, EBE, Résultat exploitation, RCAI, etc."""
    try:
        return str(_get_sql_qe("sig", ["v_sig", "v_sig_drilldown", "entite", "exercice"]).query(query))
    except Exception as e:
        return f"Erreur SQL sig : {e}"


@tool("sql_bilan")
def tool_sql_bilan(query: str) -> str:
    """Requête SQL sur le bilan comptable. Actif/Passif structurés
    (brut, amortissements, net) par bilan_section et bilan_poste."""
    try:
        return str(_get_sql_qe("bilan", ["v_bilan", "entite", "exercice"]).query(query))
    except Exception as e:
        return f"Erreur SQL bilan : {e}"


@tool("sql_bilan_fonctionnel")
def tool_sql_bilan_fonctionnel(query: str) -> str:
    """Requête SQL sur le bilan fonctionnel. FRNG, BFR exploitation,
    BFR hors exploitation, Trésorerie nette."""
    try:
        return str(_get_sql_qe("bf", ["v_bilan_fonctionnel", "entite", "exercice"]).query(query))
    except Exception as e:
        return f"Erreur SQL bilan_fonctionnel : {e}"


@tool("sql_compte_resultat")
def tool_sql_cr(query: str) -> str:
    """Requête SQL sur le compte de résultat structuré.
    Produits et charges par cr_rubrique avec cr_signe."""
    try:
        return str(_get_sql_qe("cr", ["v_compte_resultat", "entite", "exercice"]).query(query))
    except Exception as e:
        return f"Erreur SQL compte_resultat : {e}"


@tool("sql_resultat_differentiel")
def tool_sql_crd(query: str) -> str:
    """Requête SQL sur le Compte de Résultat Différentiel.
    CA, charges variables, MCV, taux MCV, charges fixes, seuil de rentabilité."""
    try:
        return str(_get_sql_qe("crd", ["v_resultat_differentiel", "v_crd_drilldown", "entite", "exercice"]).query(query))
    except Exception as e:
        return f"Erreur SQL resultat_differentiel : {e}"


@tool("sql_ecritures_detail")
def tool_sql_ecritures_detail(query: str) -> str:
    """Requête SQL sur le Grand Livre détaillé, le journal centralisateur,
    la balance auxiliaire par tiers, et la balance âgée par ancienneté."""
    try:
        return str(_get_sql_qe("detail", ["grand_livre", "v_journal", "v_balance_auxiliaire", "v_balance_agee", "entite"]).query(query))
    except Exception as e:
        return f"Erreur SQL ecritures_detail : {e}"


ALL_SQL_TOOLS = [
    tool_sql_grand_livre, tool_sql_balance_generale,
    tool_sql_balance, tool_sql_sig, tool_sql_bilan,
    tool_sql_bilan_fonctionnel, tool_sql_cr, tool_sql_crd, tool_sql_ecritures_detail,
]
