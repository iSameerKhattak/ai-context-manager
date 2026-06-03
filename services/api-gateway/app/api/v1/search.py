from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from contextclaw.db.models import Membership, Project, User

router = APIRouter()


# ── Request / Response schemas ─────────────────────────────────────


class SearchQuery(BaseModel):
    project_id: str
    query: str
    k: int = Field(default=10, ge=1, le=100)
    mode: str = "hybrid"  # "hybrid" | "vector" | "fts"
    filters: dict[str, Any] = Field(default_factory=dict)


class SourceInfo(BaseModel):
    document_id: str
    path: str
    language: str
    symbol: str
    source_type: str


class SearchResultItem(BaseModel):
    chunk_id: str
    score: float
    source: SourceInfo
    snippet: str


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    mode: str
    took_ms: int


class ContextBuildRequest(BaseModel):
    project_id: str
    query: str
    max_chunks: int = Field(default=15, le=50)
    mode: str = "hybrid"


class ContextPreviewItem(BaseModel):
    chunk_id: str
    score: float
    source: SourceInfo
    snippet: str
    relevance: str  # "high" | "medium" | "low"


class ContextPreviewResponse(BaseModel):
    items: list[ContextPreviewItem]
    total_chunks: int
    took_ms: int


# ── Helper: verify project membership ──────────────────────────────


async def _verify_project_access(
    session: AsyncSession, project_id: str, user: User
) -> Project:
    result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify user belongs to the org that owns this project
    result = await session.execute(
        select(Membership).where(
            Membership.org_id == project.org_id,
            Membership.user_id == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Access denied")

    return project


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("")
async def search(
    body: SearchQuery,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Hybrid (vector + FTS) search across all indexed sources."""
    await _verify_project_access(session, body.project_id, user)

    t0 = time.time()

    if body.mode == "vector":
        results = await _vector_only(body)
    elif body.mode == "fts":
        results = await _fts_only(body)
    else:
        results = await _hybrid_search(body)

    took_ms = int((time.time() - t0) * 1000)

    return SearchResponse(
        results=[SearchResultItem(**r) for r in results],
        mode=body.mode,
        took_ms=took_ms,
    )


@router.post("/preview")
async def build_context_preview(
    body: ContextBuildRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ContextPreviewResponse:
    """Preview what context would be sent for a given query."""
    from contextclaw.search.hybrid import hybrid_search, HybridSearchConfig
    from contextclaw.search.vector import embed_and_search

    await _verify_project_access(session, body.project_id, user)

    t0 = time.time()

    if body.mode == "vector":
        raw = embed_and_search(
            project_id=body.project_id,
            query_text=body.query,
            k=body.max_chunks,
        )
    else:
        from contextclaw.embeddings.router import get_embedding_provider

        provider = get_embedding_provider()
        query_vector = provider.embed_one(body.query)
        raw = hybrid_search(
            project_id=body.project_id,
            query_text=body.query,
            query_vector=query_vector,
            config=HybridSearchConfig(final_k=body.max_chunks),
        )

    items: list[ContextPreviewItem] = []
    for r in raw:
        score = r.score
        if score >= 0.6:
            relevance = "high"
        elif score >= 0.3:
            relevance = "medium"
        else:
            relevance = "low"

        items.append(
            ContextPreviewItem(
                chunk_id=str(r.chunk_id),
                score=score,
                source=SourceInfo(**r.source),
                snippet=r.snippet,
                relevance=relevance,
            )
        )

    took_ms = int((time.time() - t0) * 1000)
    return ContextPreviewResponse(items=items, total_chunks=len(items), took_ms=took_ms)


@router.post("/build")
async def build_context(
    body: ContextBuildRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ContextPreviewResponse:
    """Build ranked context for an agent task — alias for preview."""
    return await build_context_preview(body, user, session)


# ── Internal search helpers ────────────────────────────────────────


async def _vector_only(body: SearchQuery) -> list[dict[str, Any]]:
    from contextclaw.search.vector import embed_and_search

    raw = embed_and_search(
        project_id=body.project_id,
        query_text=body.query,
        k=body.k,
        filters=body.filters,
    )
    return [_result_to_dict(r) for r in raw]


async def _fts_only(body: SearchQuery) -> list[dict[str, Any]]:
    import asyncio
    from contextclaw.search.fts import fts_search

    loop = asyncio.get_running_loop()
    raw = await loop.run_in_executor(
        None,
        fts_search,
        body.project_id,
        body.query,
        body.k,
        body.filters,
    )
    return [_result_to_dict(r) for r in raw]


async def _hybrid_search(body: SearchQuery) -> list[dict[str, Any]]:
    import asyncio
    from contextclaw.embeddings.router import get_embedding_provider
    from contextclaw.search.hybrid import hybrid_search, HybridSearchConfig

    provider = get_embedding_provider()
    loop = asyncio.get_running_loop()

    query_vector = await loop.run_in_executor(None, provider.embed_one, body.query)
    raw = hybrid_search(
        project_id=body.project_id,
        query_text=body.query,
        query_vector=query_vector,
        config=HybridSearchConfig(final_k=body.k),
        filters=body.filters,
    )
    return [_result_to_dict(r) for r in raw]


def _result_to_dict(r: Any) -> dict[str, Any]:
    return {
        "chunk_id": str(r.chunk_id),
        "score": r.score,
        "source": {
            "document_id": r.source.get("document_id", ""),
            "path": r.source.get("path", ""),
            "language": r.source.get("language", ""),
            "symbol": r.source.get("symbol", ""),
            "source_type": r.source.get("source_type", "code"),
        },
        "snippet": r.snippet,
    }
