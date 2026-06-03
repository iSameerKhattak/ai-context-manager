from __future__ import annotations

from typing import Any

from contextclaw.models import SearchResult
from contextclaw.settings import settings
from contextclaw.embeddings.router import get_embedding_provider
from contextclaw.vector.qdrant import search as qdrant_search


def vector_search(
    project_id: str,
    query_vector: list[float],
    k: int = 20,
    score_threshold: float = 0.0,
    filters: dict[str, Any] | None = None,
) -> list[SearchResult]:
    """Vector-only search via Qdrant."""
    hits = qdrant_search(
        query_vector=query_vector,
        project_id=project_id,
        k=k,
        score_threshold=score_threshold,
        filters=filters,
    )

    results: list[SearchResult] = []
    for h in hits:
        source = {
            "document_id": h.get("document_id", ""),
            "path": h.get("path", ""),
            "language": h.get("language", ""),
            "symbol": h.get("symbol", ""),
            "source_type": h.get("source_type", "code"),
        }
        results.append(
            SearchResult(
                chunk_id=h["chunk_id"],
                score=h["score"],
                source=source,
                snippet=h.get("content", "")[:500],
            )
        )

    return results


def embed_and_search(
    project_id: str,
    query_text: str,
    k: int = 20,
    score_threshold: float = 0.0,
    filters: dict[str, Any] | None = None,
) -> list[SearchResult]:
    """Embed a query string, then vector search."""
    provider = get_embedding_provider()
    vector = provider.embed_one(query_text)
    return vector_search(
        project_id=project_id,
        query_vector=vector,
        k=k,
        score_threshold=score_threshold,
        filters=filters,
    )
