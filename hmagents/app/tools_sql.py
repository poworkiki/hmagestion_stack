"""Outils LlamaIndex SQL wrappés pour CrewAI — PostgreSQL HMA."""

from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from sqlalchemy import create_engine
from crewai.tools import tool

from app.config import settings
import app.tools_rag  # noqa: F401 — force l'initialisation LLM + embeddings

# ── Connexion PostgreSQL HMA ─────────────────────────────────────────
pg_engine = create_engine(settings.hma_db_url)
sql_database = SQLDatabase(pg_engine)


# ── QueryEngines SQL (initialisés une fois) ──────────────────────────
_qe_balance = NLSQLTableQueryEngine(
    sql_database=sql_database,
    tables=["mv_balance_generale", "v_balance_auxiliaire", "entite", "exercice"],
)
_qe_sig = NLSQLTableQueryEngine(
    sql_database=sql_database,
    tables=["v_sig", "v_sig_drilldown", "entite", "exercice"],
)
_qe_bilan = NLSQLTableQueryEngine(
    sql_database=sql_database,
    tables=["v_bilan", "entite", "exercice"],
)
_qe_bf = NLSQLTableQueryEngine(
    sql_database=sql_database,
    tables=["v_bilan_fonctionnel", "entite", "exercice"],
)
_qe_cr = NLSQLTableQueryEngine(
    sql_database=sql_database,
    tables=["v_compte_resultat", "entite", "exercice"],
)
_qe_crd = NLSQLTableQueryEngine(
    sql_database=sql_database,
    tables=["v_resultat_differentiel", "v_crd_drilldown", "entite", "exercice"],
)
_qe_fec = NLSQLTableQueryEngine(
    sql_database=sql_database,
    tables=["fec_ecriture", "v_grand_livre", "entite", "exercice", "pcg_analytique"],
)


# ── 7 outils SQL wrappés pour CrewAI ────────────────────────────────

@tool("sql_balance")
def tool_sql_balance(query: str) -> str:
    """Requête SQL sur la balance générale et balance auxiliaire.
    Soldes par compte, entité, exercice et mois."""
    return str(_qe_balance.query(query))


@tool("sql_sig")
def tool_sql_sig(query: str) -> str:
    """Requête SQL sur les 9 Soldes Intermédiaires de Gestion + CAF.
    Marge commerciale, Production, VA, EBE, Résultat exploitation, RCAI, etc."""
    return str(_qe_sig.query(query))


@tool("sql_bilan")
def tool_sql_bilan(query: str) -> str:
    """Requête SQL sur le bilan comptable. Actif/Passif structurés
    (brut, amortissements, net) par bilan_section et bilan_poste."""
    return str(_qe_bilan.query(query))


@tool("sql_bilan_fonctionnel")
def tool_sql_bilan_fonctionnel(query: str) -> str:
    """Requête SQL sur le bilan fonctionnel. FRNG, BFR exploitation,
    BFR hors exploitation, Trésorerie nette."""
    return str(_qe_bf.query(query))


@tool("sql_compte_resultat")
def tool_sql_cr(query: str) -> str:
    """Requête SQL sur le compte de résultat structuré.
    Produits et charges par cr_rubrique avec cr_signe."""
    return str(_qe_cr.query(query))


@tool("sql_resultat_differentiel")
def tool_sql_crd(query: str) -> str:
    """Requête SQL sur le Compte de Résultat Différentiel.
    CA, charges variables, MCV, taux MCV, charges fixes, seuil de rentabilité."""
    return str(_qe_crd.query(query))


@tool("sql_ecritures_fec")
def tool_sql_fec(query: str) -> str:
    """Requête SQL sur les écritures comptables FEC et le grand livre.
    25 000+ écritures normalisées. Colonnes : journal_code, ecriture_num, etc."""
    return str(_qe_fec.query(query))


ALL_SQL_TOOLS = [
    tool_sql_balance, tool_sql_sig, tool_sql_bilan,
    tool_sql_bilan_fonctionnel, tool_sql_cr, tool_sql_crd, tool_sql_fec,
]
