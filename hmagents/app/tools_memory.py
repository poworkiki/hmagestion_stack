"""Outils mem0 — Mémoire long terme des agents via Qdrant."""

from mem0 import Memory
from crewai.tools import tool

from app.config import settings

# ── Configuration mem0 → Qdrant + OpenAI embeddings ─────────────────
mem0_config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "url": settings.qdrant_url,
            "api_key": settings.qdrant_api_key,
            "port": settings.qdrant_port,
        },
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": settings.embedding_model,
            "api_key": settings.openai_api_key,
        },
    },
    "llm": {
        "provider": "anthropic",
        "config": {
            "model": "claude-sonnet-4-6",
            "api_key": settings.anthropic_api_key,
            "max_tokens": 4096,
        },
    },
}

mem0_memory = Memory.from_config(mem0_config)


# ── Fonctions utilitaires ────────────────────────────────────────────

def memorize(agent_id: str, content: str, metadata: dict | None = None):
    """Stocker un output d'agent en mémoire long terme."""
    mem0_memory.add(
        content,
        user_id=agent_id,
        metadata=metadata or {},
    )


def recall(agent_id: str, query: str, limit: int = 5) -> list[dict]:
    """Retrouver les souvenirs pertinents d'un agent."""
    results = mem0_memory.search(query, user_id=agent_id, limit=limit)
    return results.get("results", [])


def _format_memories(memories: list[dict]) -> str:
    """Formate les souvenirs en texte lisible."""
    if not memories:
        return "Aucun souvenir pertinent trouvé."
    return "\n---\n".join(m["memory"] for m in memories)


# ── Outils CrewAI wrappant mem0 ─────────────────────────────────────

@tool("memoire_expert_comptable")
def tool_mem0_expert_comptable(query: str) -> str:
    """Recherche dans la mémoire long terme de l'Expert-Comptable.
    Retrouve les analyses passées similaires (écritures, révisions, paie)."""
    try:
        return _format_memories(recall("expert_comptable", query))
    except Exception as e:
        return f"Erreur mémoire expert_comptable : {e}"


@tool("memoire_juriste")
def tool_mem0_juriste(query: str) -> str:
    """Recherche dans la mémoire long terme du Juriste Senior.
    Retrouve les avis juridiques, montages et articles cités passés."""
    try:
        return _format_memories(recall("juriste", query))
    except Exception as e:
        return f"Erreur mémoire juriste : {e}"


@tool("memoire_analyste")
def tool_mem0_analyste(query: str) -> str:
    """Recherche dans la mémoire long terme de l'Analyste Financier.
    Retrouve les analyses SIG, ratios et simulations passées."""
    try:
        return _format_memories(recall("analyste_financier", query))
    except Exception as e:
        return f"Erreur mémoire analyste : {e}"


@tool("memoire_reviseur")
def tool_mem0_reviseur(query: str) -> str:
    """Recherche dans la mémoire long terme du Réviseur Qualité.
    Retrouve les patterns d'erreur et alertes détectés."""
    try:
        return _format_memories(recall("reviseur", query))
    except Exception as e:
        return f"Erreur mémoire reviseur : {e}"


# Export pour crew.py
ALL_MEMORY_TOOLS = {
    "expert_comptable": tool_mem0_expert_comptable,
    "juriste": tool_mem0_juriste,
    "analyste_financier": tool_mem0_analyste,
    "reviseur": tool_mem0_reviseur,
}
