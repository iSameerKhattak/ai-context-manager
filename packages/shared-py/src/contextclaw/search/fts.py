from __future__ import annotations

from typing import Any
from uuid import UUID

from contextclaw.models import SearchResult


def fts_search(
    project_id: str,
    query_text: str,
    k: int = 20,
    filters: dict[str, Any] | None = None,
) -> list[SearchResult]:
    """Full-text search on PostgreSQL chunks using the tsvector column.

    Uses SQLAlchemy text() with the built-in ``chunks.fts`` tsvector column
    and ``plainto_tsquery`` for user-friendly query parsing.
    """
    from sqlalchemy import text
    from contextclaw.db.engine import get_session
    from contextclaw.db.models import Chunk, Document

    session_gen = get_session()

    if hasattr(session_gen, "__aenter__"):
        import asyncio
        raise RuntimeError(
            "fts_search requires a sync session; use the async wrapper instead"
        )

    with session_gen as session:
        stmt = text(
            """
            SELECT
                c.id,
                c.content,
                c.symbol,
                c.ordinal,
                c.start_line,
                c.end_line,
                d.id AS document_id,
                d.path,
                d.language,
                d.source_type,
                ts_rank(c.fts, query) AS rank
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            CROSS JOIN plainto_tsquery('english', :query_text) AS query
            WHERE c.project_id = :project_id
              AND c.fts @@ query
            ORDER BY rank DESC
            LIMIT :k
            """
        )

        params: dict[str, Any] = {
            "query_text": query_text,
            "project_id": project_id,
            "k": k,
        }

        rows = session.execute(stmt, params).mappings().all()

        results: list[SearchResult] = []
        for row in rows:
            source = {
                "document_id": str(row["document_id"]),
                "path": row["path"] or "",
                "language": row["language"] or "",
                "symbol": row["symbol"] or "",
                "source_type": row["source_type"] or "code",
            }
            results.append(
                SearchResult(
                    chunk_id=row["id"],
                    score=float(row["rank"]),
                    source=source,
                    snippet=(row["content"] or "")[:500],
                )
            )

        return results
