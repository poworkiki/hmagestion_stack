"""Outils LlamaIndex RAG — QueryEngine sur les collections Qdrant KB."""

import qdrant_client
from llama_index.core import VectorStoreIndex, Settings as LlamaSettings
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI as LlamaOpenAI

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
qclient = qdrant_client.QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key,
    port=settings.qdrant_port,
    https=True,
)


def _make_kb_tool(collection_name: str, description: str) -> QueryEngineTool:
    """Crée un outil RAG sur une collection Qdrant."""
    vector_store = QdrantVectorStore(
        client=qclient,
        collection_name=collection_name,
    )
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=embed_model,
    )
    query_engine = index.as_query_engine(
        similarity_top_k=10,
        response_mode="tree_summarize",
    )
    return QueryEngineTool(
        query_engine=query_engine,
        metadata=ToolMetadata(
            name=f"kb_{collection_name}",
            description=description,
        ),
    )


# ── 4 outils KB ─────────────────────────────────────────────────────

tool_kb_manuels = _make_kb_tool(
    settings.kb_manuels,
    "Recherche dans les manuels DCG/DSCG (comptabilité, fiscalité, droit, finance). "
    "18 132 documents. Utiliser pour les questions théoriques et normatives.",
)

tool_kb_reglementation = _make_kb_tool(
    settings.kb_reglementation,
    "Recherche dans les textes de loi : Girardin, LODEOM, dispositifs ultramarins. "
    "Utiliser pour les questions fiscales et réglementaires spécifiques Guyane/DOM.",
)

tool_kb_conventions = _make_kb_tool(
    settings.kb_conventions,
    "Recherche dans les conventions collectives Guyane (Transport, Agroalimentaire). "
    "Utiliser pour les questions de paie, grilles salariales, indemnités.",
)

tool_kb_pcg = _make_kb_tool(
    settings.kb_pcg_analytique,
    "Recherche dans le mapping des 1 412 comptes PCG avec catégories analytiques "
    "(SIG, CR, Bilan, BF, V/F). Utiliser pour identifier le rôle d'un compte.",
)

# Export pour crew.py
ALL_KB_TOOLS = [tool_kb_manuels, tool_kb_reglementation, tool_kb_conventions, tool_kb_pcg]
