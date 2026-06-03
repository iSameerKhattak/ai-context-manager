from __future__ import annotations

from typing import Any


class Tool:
    """Base class for agent tools."""

    name: str
    description: str

    async def run(self, **kwargs: Any) -> Any:
        raise NotImplementedError


class SearchTool(Tool):
    """Search indexed codebase using hybrid search."""

    name = "search"
    description = "Search the indexed codebase. Returns ranked code chunks with paths and scores."

    async def run(
        self,
        query: str,
        project_id: str,
        k: int = 10,
    ) -> list[dict[str, Any]]:
        import asyncio
        from contextclaw.embeddings.router import get_embedding_provider
        from contextclaw.search.hybrid import hybrid_search, HybridSearchConfig

        provider = get_embedding_provider()
        loop = asyncio.get_running_loop()

        query_vector = await loop.run_in_executor(None, provider.embed_one, query)
        raw = hybrid_search(
            project_id=project_id,
            query_text=query,
            query_vector=query_vector,
            config=HybridSearchConfig(final_k=k),
        )

        return [
            {
                "chunk_id": str(r.chunk_id),
                "score": r.score,
                "path": r.source.get("path", ""),
                "snippet": r.snippet[:300],
                "language": r.source.get("language", ""),
                "symbol": r.source.get("symbol", ""),
            }
            for r in raw
        ]


class MemoryReadTool(Tool):
    """Read memory facts for a project."""

    name = "memory_read"
    description = "Read stored memory facts about a project."

    async def run(
        self,
        project_id: str,
        scope: str | None = None,
    ) -> list[dict[str, Any]]:
        from sqlalchemy import select
        from contextclaw.db.engine import get_session
        from contextclaw.db.models import MemoryFact

        session_gen = get_session()
        async with session_gen as session:
            query = select(MemoryFact).where(
                MemoryFact.project_id == project_id,
                MemoryFact.superseded_by.is_(None),
            )
            if scope:
                query = query.where(MemoryFact.scope == scope)
            query = query.order_by(MemoryFact.created_at.desc())

            result = await session.execute(query)
            facts = result.scalars().all()

            return [
                {
                    "id": str(f.id),
                    "statement": f.statement,
                    "scope": f.scope,
                    "confidence": f.confidence,
                    "source": f.source,
                }
                for f in facts
            ]


class MemoryWriteTool(Tool):
    """Write a new memory fact about a project."""

    name = "memory_write"
    description = "Store a new fact about the project that ContextClaw will remember."

    async def run(
        self,
        project_id: str,
        statement: str,
        scope: str = "project",
        confidence: float = 0.8,
    ) -> dict[str, Any]:
        from contextclaw.db.engine import get_session
        from contextclaw.db.models import MemoryFact

        session_gen = get_session()
        async with session_gen as session:
            fact = MemoryFact(
                project_id=project_id,
                statement=statement,
                scope=scope,
                source="agent",
                confidence=confidence,
            )
            session.add(fact)
            await session.commit()

            return {
                "id": str(fact.id),
                "statement": fact.statement,
                "scope": fact.scope,
                "confidence": fact.confidence,
            }


class ListFilesTool(Tool):
    """List files in a repository at a given path."""

    name = "list_files"
    description = "List files and directories in a repository."

    async def run(
        self,
        repo_path: str,
        path: str = ".",
    ) -> list[dict[str, str]]:
        import os
        full = os.path.join(repo_path, path)
        if not os.path.isdir(full):
            return [{"error": f"Not a directory: {path}"}]

        entries: list[dict[str, str]] = []
        for name in os.listdir(full):
            abs_path = os.path.join(full, name)
            entries.append({
                "name": name,
                "type": "dir" if os.path.isdir(abs_path) else "file",
            })

        return entries


class ReadFileTool(Tool):
    """Read the contents of a file."""

    name = "read_file"
    description = "Read the contents of a specific file."

    async def run(self, repo_path: str, file_path: str) -> str | None:
        import os
        full = os.path.join(repo_path, file_path)
        if not os.path.isfile(full):
            return None
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None


# ── Registry ───────────────────────────────────────────────────────

def get_tools() -> dict[str, Tool]:
    return {
        "search": SearchTool(),
        "memory_read": MemoryReadTool(),
        "memory_write": MemoryWriteTool(),
        "list_files": ListFilesTool(),
        "read_file": ReadFileTool(),
    }
