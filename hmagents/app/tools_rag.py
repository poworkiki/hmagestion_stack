"""Outils LlamaIndex RAG — QueryEngine sur les collections Qdrant KB, wrappés pour CrewAI."""

import qdrant_client
from llama_index.core import VectorStoreIndex, Settings as LlamaSettings
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from crewai.tools import tool

from app.config import settings

# ── LLM pour les QueryEngines (OpenAI — requis par LlamaIndex) ──────
LlamaSettings.llm = LlamaOpenAI(
    model="gpt-4o-mini",
    api_key=settings.openai_api_key,
)

# ── Embeddings partagés ──────────────────────────────────────────────
embed_model = OpenAIEmbedding(
    model_name=settings.embedding_model,
    api_key=settings.openai_api_key,
)
LlamaSettings.embed_model = embed_model

# ── Client Qdrant ────────────────────────────────────────────────────
_is_https = settings.qdrant_url.startswith("https://")
qclient = qdrant_client.QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key or None,
    port=settings.qdrant_port,
    https=_is_https,
)


def _make_query_engine(collection_name: str):
    """Crée un QueryEngine LlamaIndex sur une collection Qdrant."""
    vector_store = QdrantVectorStore(
        client=qclient,
        collection_name=collection_name,
    )
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=embed_model,
    )
    return index.as_query_engine(
        similarity_top_k=10,
        response_mode="tree_summarize",
    )


# ── QueryEngines (initialisés une fois) ─────────────────────────────
_qe_manuels = _make_query_engine(settings.kb_manuels)
_qe_reglementation = _make_query_engine(settings.kb_reglementation)
_qe_conventions = _make_query_engine(settings.kb_conventions)
_qe_pcg = _make_query_engine(settings.kb_pcg_analytique)


# ── 4 outils KB wrappés pour CrewAI ─────────────────────────────────

@tool("kb_manuels")
def tool_kb_manuels(query: str) -> str:
    """Recherche dans les manuels DCG/DSCG (comptabilité, fiscalité, droit, finance).
    18 132 documents. Utiliser pour les questions théoriques et normatives."""
    try:
        return str(_qe_manuels.query(query))
    except Exception as e:
        return f"Erreur kb_manuels : {e}"


@tool("kb_reglementation")
def tool_kb_reglementation(query: str) -> str:
    """Recherche dans les textes de loi : Girardin, LODEOM, dispositifs ultramarins.
    Utiliser pour les questions fiscales et réglementaires spécifiques Guyane/DOM."""
    try:
        return str(_qe_reglementation.query(query))
    except Exception as e:
        return f"Erreur kb_reglementation : {e}"


@tool("kb_conventions")
def tool_kb_conventions(query: str) -> str:
    """Recherche dans les conventions collectives Guyane (Transport, Agroalimentaire).
    Utiliser pour les questions de paie, grilles salariales, indemnités."""
    try:
        return str(_qe_conventions.query(query))
    except Exception as e:
        return f"Erreur kb_conventions : {e}"


@tool("kb_pcg_analytique")
def tool_kb_pcg(query: str) -> str:
    """Recherche dans le mapping des 1 412 comptes PCG avec catégories analytiques
    (SIG, CR, Bilan, BF, V/F). Utiliser pour identifier le rôle d'un compte."""
    try:
        return str(_qe_pcg.query(query))
    except Exception as e:
        return f"Erreur kb_pcg : {e}"


# Export pour crew.py
ALL_KB_TOOLS = [tool_kb_manuels, tool_kb_reglementation, tool_kb_conventions, tool_kb_pcg]
