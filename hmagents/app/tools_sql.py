"""Outils LlamaIndex SQL — QueryEngine sur PostgreSQL HMA (vues matérialisées + FEC)."""

from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from sqlalchemy import create_engine

from app.config import settings

# ── Connexion PostgreSQL HMA ─────────────────────────────────────────
pg_engine = create_engine(settings.hma_db_url)

sql_database = SQLDatabase(
    pg_engine,
    include_tables=[
        # Vues (balance matérialisée, autres simples)
        "mv_balance_generale",
        "v_sig", "v_sig_drilldown",
        "v_compte_resultat",
        "v_bilan", "v_bilan_fonctionnel",
        "v_resultat_differentiel", "v_crd_drilldown",
        "v_grand_livre", "v_balance_auxiliaire",
        # Tables de référence
        "entite", "exercice", "pcg_analytique",
        # Données
        "fec_ecriture",
    ],
)


# ── Outils SQL ───────────────────────────────────────────────────────

tool_sql_balance = QueryEngineTool(
    query_engine=NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["mv_balance_generale", "v_balance_auxiliaire", "entite", "exercice"],
    ),
    metadata=ToolMetadata(
        name="sql_balance",
        description=(
            "Requête SQL sur la balance générale et balance auxiliaire. "
            "Soldes par compte, entité, exercice et mois. "
            "Colonnes principales : entite_id, exercice_id, pcg_numero, mois, debit, credit, solde."
        ),
    ),
)

tool_sql_sig = QueryEngineTool(
    query_engine=NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["v_sig", "v_sig_drilldown", "entite", "exercice"],
    ),
    metadata=ToolMetadata(
        name="sql_sig",
        description=(
            "Requête SQL sur les 9 Soldes Intermédiaires de Gestion + CAF. "
            "Soldes : Marge commerciale, Production, Valeur ajoutée, EBE, "
            "Résultat exploitation, RCAI, Résultat exceptionnel, Résultat exercice, CAF. "
            "Drilldown par compte via v_sig_drilldown."
        ),
    ),
)

tool_sql_bilan = QueryEngineTool(
    query_engine=NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["v_bilan", "entite", "exercice"],
    ),
    metadata=ToolMetadata(
        name="sql_bilan",
        description=(
            "Requête SQL sur le bilan comptable. Actif/Passif structurés "
            "(brut, amortissements, net) par bilan_section et bilan_poste."
        ),
    ),
)

tool_sql_bilan_fonctionnel = QueryEngineTool(
    query_engine=NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["v_bilan_fonctionnel", "entite", "exercice"],
    ),
    metadata=ToolMetadata(
        name="sql_bilan_fonctionnel",
        description=(
            "Requête SQL sur le bilan fonctionnel. FRNG, BFR exploitation, "
            "BFR hors exploitation, Trésorerie nette."
        ),
    ),
)

tool_sql_cr = QueryEngineTool(
    query_engine=NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["v_compte_resultat", "entite", "exercice"],
    ),
    metadata=ToolMetadata(
        name="sql_compte_resultat",
        description=(
            "Requête SQL sur le compte de résultat structuré. "
            "Produits et charges par cr_rubrique avec cr_signe."
        ),
    ),
)

tool_sql_crd = QueryEngineTool(
    query_engine=NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["v_resultat_differentiel", "v_crd_drilldown", "entite", "exercice"],
    ),
    metadata=ToolMetadata(
        name="sql_resultat_differentiel",
        description=(
            "Requête SQL sur le Compte de Résultat Différentiel. "
            "CA, charges variables, MCV, taux MCV, charges fixes, "
            "seuil de rentabilité, point mort en jours."
        ),
    ),
)

tool_sql_fec = QueryEngineTool(
    query_engine=NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["fec_ecriture", "v_grand_livre", "entite", "exercice", "pcg_analytique"],
    ),
    metadata=ToolMetadata(
        name="sql_ecritures_fec",
        description=(
            "Requête SQL sur les écritures comptables FEC et le grand livre. "
            "25 000+ écritures normalisées avec solde progressif. "
            "Colonnes : journal_code, ecriture_num, ecriture_date, compte_num, "
            "piece_ref, ecriture_lib, debit, credit, pcg_numero."
        ),
    ),
)

# Export pour crew.py
ALL_SQL_TOOLS = [
    tool_sql_balance, tool_sql_sig, tool_sql_bilan,
    tool_sql_bilan_fonctionnel, tool_sql_cr, tool_sql_crd, tool_sql_fec,
]
