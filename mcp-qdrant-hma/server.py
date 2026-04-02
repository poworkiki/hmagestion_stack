"""
MCP Server — Qdrant RAG pour HMA Gestion.

Expose la KB comptable Qdrant (18 000+ chunks) comme outils natifs
de Claude Code via le protocole MCP (stdio).

Connexion : HTTPS directe vers qdrant.hma.business.
Embeddings : OpenAI text-embedding-3-small (1536 dims).
"""

import os
import json
from typing import Optional

from fastmcp import FastMCP
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# === Configuration ===

QDRANT_URL = os.environ.get("QDRANT_URL", "https://qdrant.hma.business:443")
QDRANT_API_KEY = os.environ.get(
    "QDRANT_API_KEY", "ToUjevnV22HxWSqFiCdVVhPl3uJNj4AX"
)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-3-small"

# === Globals ===

mcp = FastMCP("hma-qdrant-rag")
_qdrant: Optional[QdrantClient] = None
_openai: Optional[OpenAI] = None


def _get_qdrant() -> QdrantClient:
    """Client Qdrant connecté via HTTPS."""
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=30,
        )
    return _qdrant


def _get_openai() -> OpenAI:
    """Client OpenAI pour les embeddings."""
    global _openai
    if _openai is None:
        if not OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY non définie. "
                "Définir la variable d'environnement avant de lancer le serveur."
            )
        _openai = OpenAI(api_key=OPENAI_API_KEY)
    return _openai


def _embed(text: str) -> list[float]:
    """Génère un embedding pour une requête texte."""
    client = _get_openai()
    response = client.embeddings.create(input=text, model=EMBEDDING_MODEL)
    return response.data[0].embedding


# === MCP Tools ===


@mcp.tool
def list_collections() -> str:
    """Liste toutes les collections Qdrant de la KB HMA.

    Retourne le nom et le nombre de points de chaque collection.
    Collections disponibles :
    - kb_manuels : manuels DCG/DSCG + PCG 2025 (18 000+ chunks)
    - kb_reglementation : LODEOM, ZFANG, Octroi de Mer, CGSS, DEETS
    - kb_conventions : CC BTP/Commerce Guyane, paie Guyane
    - kb_precedents_cabinet : précédents du cabinet (historique dossiers)
    - kb_modeles : templates et modèles comptables
    - kb_jurisprudence : jurisprudence et décisions
    """
    qdrant = _get_qdrant()
    collections = qdrant.get_collections().collections
    result = []
    for col in collections:
        info = qdrant.get_collection(col.name)
        result.append({
            "name": col.name,
            "points_count": info.points_count,
        })
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool
def search_kb(
    query: str,
    collection: str = "kb_manuels",
    top_k: int = 5,
    domaine: Optional[str] = None,
) -> str:
    """Recherche sémantique dans la KB comptable HMA (RAG).

    Utilise les embeddings OpenAI pour trouver les chunks les plus pertinents.

    Args:
        query: Question ou mots-clés en français (ex: "amortissement matériel industriel")
        collection: Collection à interroger. Valeurs possibles :
            - kb_manuels (défaut) : manuels DCG/DSCG, PCG 2025
            - kb_reglementation : lois DOM, LODEOM, ZFANG, octroi de mer
            - kb_conventions : conventions collectives Guyane
            - kb_precedents_cabinet : historique dossiers cabinet
            - kb_modeles : templates comptables
            - kb_jurisprudence : jurisprudence
        top_k: Nombre de résultats (1-20, défaut 5)
        domaine: Filtre optionnel par domaine (ex: "comptabilite", "droit_fiscal",
                 "droit_social", "finance", "controle_gestion")

    Returns:
        Les chunks les plus pertinents avec leur score de similarité et métadonnées.
    """
    top_k = max(1, min(20, top_k))

    query_vector = _embed(query)
    qdrant = _get_qdrant()

    search_filter = None
    if domaine:
        search_filter = Filter(
            must=[FieldCondition(key="domaine", match=MatchValue(value=domaine))]
        )

    results = qdrant.query_points(
        collection_name=collection,
        query=query_vector,
        limit=top_k,
        query_filter=search_filter,
        with_payload=True,
    )

    output = []
    for point in results.points:
        payload = point.payload or {}
        output.append({
            "score": round(point.score, 4),
            "contenu": payload.get("contenu", ""),
            "domaine": payload.get("domaine", ""),
            "matiere": payload.get("matiere", ""),
            "source": payload.get("source_fichier", ""),
            "position": payload.get("position", ""),
            "type": payload.get("type", ""),
        })

    return json.dumps(output, ensure_ascii=False, indent=2)


@mcp.tool
def get_document_chunks(
    collection: str,
    document_id: str,
    limit: int = 20,
) -> str:
    """Récupère tous les chunks d'un document spécifique.

    Utile pour lire un document complet après avoir trouvé un chunk pertinent
    via search_kb.

    Args:
        collection: Nom de la collection (ex: "kb_manuels")
        document_id: ID du document (champ document_id du payload, ex: "kb_manuels__e355b2497f05")
        limit: Nombre max de chunks à retourner (défaut 20)

    Returns:
        Les chunks du document triés par position.
    """
    limit = max(1, min(100, limit))
    qdrant = _get_qdrant()

    results = qdrant.scroll(
        collection_name=collection,
        scroll_filter=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        ),
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    points = results[0]
    points_sorted = sorted(points, key=lambda p: p.payload.get("position", 0))

    output = []
    for point in points_sorted:
        payload = point.payload or {}
        output.append({
            "position": payload.get("position", 0),
            "contenu": payload.get("contenu", ""),
            "chunk_id": payload.get("chunk_id", ""),
        })

    return json.dumps(output, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
