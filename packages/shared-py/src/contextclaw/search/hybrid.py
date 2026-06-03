from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from contextclaw.models import SearchResult


@dataclass
class HybridSearchConfig:
    """Configuration for hybrid search fusion."""

    vector_weight: float = 0.5
    fts_weight: float = 0.5
    rrf_k: int = 60  # RRF constant (higher = smoother blend)
    top_k: int = 20  # candidates from each pipeline before fusion
    final_k: int = 10  # final results


def hybrid_search(
    project_id: str,
    query_text: str,
    query_vector: list[float],
    config: HybridSearchConfig | None = None,
    filters: dict[str, Any] | None = None,
) -> list[SearchResult]:
    """Run hybrid search combining vector similarity and full-text search.

    1. Vector search via Qdrant
    2. Full-text search via PostgreSQL tsvector
    3. Reciprocal Rank Fusion (RRF) to combine scores
    4. Return deduplicated, ranked results
    """
    cfg = config or HybridSearchConfig()

    from contextclaw.search.fts import fts_search
    from contextclaw.search.vector import vector_search

    vector_results = vector_search(
        project_id=project_id,
        query_vector=query_vector,
        k=cfg.top_k,
        score_threshold=0.0,
        filters=filters,
    )

    fts_results = fts_search(
        project_id=project_id,
        query_text=query_text,
        k=cfg.top_k,
        filters=filters,
    )

    return _fuse(
        vector_results=vector_results,
        fts_results=fts_results,
        k=cfg.rrf_k,
        limit=cfg.final_k,
    )


def _fuse(
    vector_results: list[SearchResult],
    fts_results: list[SearchResult],
    k: int = 60,
    limit: int = 10,
) -> list[SearchResult]:
    """Fuse two ranked result lists using Reciprocal Rank Fusion."""

    # Build per-list ranks (1-indexed)
    seen: dict[str, float] = {}

    for rank, r in enumerate(vector_results, start=1):
        cid = str(r.chunk_id)
        seen[cid] = seen.get(cid, 0.0) + 1.0 / (k + rank)

    for rank, r in enumerate(fts_results, start=1):
        cid = str(r.chunk_id)
        seen[cid] = seen.get(cid, 0.0) + 1.0 / (k + rank)

    if not seen:
        return []

    # Sort by RRF score descending
    ranked = sorted(seen.items(), key=lambda x: -x[1])

    # Build result objects from the higher-scoring source
    vec_by_id = {str(r.chunk_id): r for r in vector_results}
    fts_by_id = {str(r.chunk_id): r for r in fts_results}

    fused: list[SearchResult] = []
    for cid, score in ranked[:limit]:
        src = vec_by_id.get(cid) or fts_by_id.get(cid)
        if src:
            fused.append(
                SearchResult(
                    chunk_id=src.chunk_id,
                    score=score / 2.0,  # Normalize to 0-1
                    source=src.source,
                    snippet=src.snippet,
                )
            )

    return fused
