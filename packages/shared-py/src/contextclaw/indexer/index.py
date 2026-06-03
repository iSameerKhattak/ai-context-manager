from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from contextclaw.indexer.chunkers.treesitter import chunker_for_file
from contextclaw.indexer.repo import cleanup, clone_repo, read_file, walk_files
from contextclaw.settings import settings

if TYPE_CHECKING:
    from contextclaw.db.models import Repository


def index_repository(repo: Repository, commit_sha: str | None = None) -> dict[str, Any]:
    """Clone *repo*, chunk every file, upsert Documents & Chunks into the DB.

    Generates embeddings and pushes to Qdrant after chunking.
    Returns a summary dict with file/chunk counts.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import Session as SASession

    from contextclaw.db.engine import get_session
    from contextclaw.db.models import Chunk, Document, IndexingJob

    clone_url = repo.clone_url
    if not clone_url:
        if repo.provider == "github":
            clone_url = f"https://github.com/{repo.full_name}.git"
        else:
            raise ValueError(f"No clone_url for repo {repo.full_name}")

    job = IndexingJob(
        repository_id=repo.id, ref=repo.default_branch, commit_sha=commit_sha
    )

    session_gen = get_session()

    if hasattr(session_gen, "__aenter__"):
        import asyncio

        async def _run() -> dict[str, Any]:
            async with session_gen as session:
                return await _do_index(session, repo, job, clone_url, commit_sha)

        return asyncio.run(_run())

    with session_gen as session:
        return _do_index_sync(session, repo, job, clone_url, commit_sha)


def _do_index_sync(
    session: SASession,
    repo: Any,
    job: Any,
    clone_url: str,
    commit_sha: str | None,
) -> dict[str, Any]:
    from contextclaw.db.models import Chunk, Document, IndexingJob

    session.add(job)
    session.flush()

    repo_path = None
    try:
        job.status = "cloning"
        session.flush()

        repo_path = clone_repo(clone_url, repo.default_branch)

        job.status = "indexing"
        job.started_at = datetime.now(timezone.utc)
        session.flush()

        files_found = 0
        files_indexed = 0
        chunks_created = 0

        # Accumulate batches for embedding generation
        embedding_batch: list[tuple[Any, list[Any], str, str | None, str | None]] = []

        for rel_path in walk_files(repo_path):
            files_found += 1
            source = read_file(repo_path, rel_path)
            if source is None:
                continue

            content_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()

            existing = session.execute(
                select(Document).where(
                    Document.repository_id == repo.id,
                    Document.path == rel_path,
                    Document.content_hash == content_hash,
                )
            ).scalar_one_or_none()

            if existing is not None:
                files_indexed += 1
                continue

            chunker = chunker_for_file(rel_path)
            chunks = chunker.chunk(source, rel_path)
            lang = chunker.language

            doc = Document(
                project_id=repo.project_id,
                repository_id=repo.id,
                source_type="code",
                source_uri=f"https://github.com/{repo.full_name}/blob/{repo.default_branch}/{rel_path}",
                path=rel_path,
                title=os.path.basename(rel_path),
                content_hash=content_hash,
                language=lang if lang != "text" else None,
                size_bytes=len(source.encode("utf-8")),
                json_metadata={"indexing_job_id": str(job.id)},
                indexed_at=datetime.now(timezone.utc),
            )
            session.add(doc)
            session.flush()

            for i, chunk_data in enumerate(chunks):
                db_chunk = Chunk(
                    document_id=doc.id,
                    project_id=repo.project_id,
                    ordinal=i,
                    content=chunk_data.content,
                    token_count=chunk_data.token_count,
                    start_line=chunk_data.start_line,
                    end_line=chunk_data.end_line,
                    symbol=chunk_data.symbol,
                    json_metadata={"language": chunk_data.language} if chunk_data.language else {},
                )
                session.add(db_chunk)

            chunks_created += len(chunks)
            files_indexed += 1

            # Queue for embedding
            embedding_batch.append(
                (doc, chunks, lang, rel_path, repo.project_id)
            )

        # Generate embeddings and push to Qdrant
        if embedding_batch:
            _generate_and_store_embeddings(embedding_batch, job)

        job.status = "completed"
        job.files_total = files_found
        job.files_indexed = files_indexed
        job.chunks_created = chunks_created
        job.finished_at = datetime.now(timezone.utc)

        repo.last_indexed_sha = commit_sha
        repo.last_indexed_at = datetime.now(timezone.utc)
        repo.status = "ready"
        repo.current_job_id = job.id

        session.commit()

        return {
            "job_id": str(job.id),
            "files_total": files_found,
            "files_indexed": files_indexed,
            "chunks_created": chunks_created,
            "status": "completed",
        }

    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        session.commit()
        return {"job_id": str(job.id), "status": "failed", "error": str(exc)}

    finally:
        if repo_path:
            cleanup(repo_path)


def _generate_and_store_embeddings(
    batch: list[tuple[Any, list[Any], str | None, str, str]],
    job: Any,
) -> None:
    """Generate embeddings for a batch of documents and upsert to Qdrant.

    Each tuple is (doc, chunks, language, file_path, project_id).
    """
    from contextclaw.embeddings.router import get_embedding_provider
    from contextclaw.vector.qdrant import ensure_collection, upsert_batch

    provider = get_embedding_provider()
    ensure_collection(dim=provider.dim)

    qdrant_points: list[tuple[UUID, list[float], dict[str, Any]]] = []

    for doc, chunks, lang, rel_path, project_id in batch:
        texts = [c.content for c in chunks]
        if not texts:
            continue

        try:
            vectors = provider.embed(texts)
        except Exception as exc:
            print(f"[embedding] error embedding {rel_path}: {exc}")
            continue

        for idx, (chunk_data, vector) in enumerate(zip(chunks, vectors)):
            ext = os.path.splitext(rel_path)[1].lower()
            qdrant_points.append((
                chunk_data.id if hasattr(chunk_data, "id") else UUID(int=0),
                vector,
                {
                    "chunk_id": str(chunk_data.id) if hasattr(chunk_data, "id") else "",
                    "project_id": str(project_id),
                    "document_id": str(doc.id),
                    "language": lang or "text",
                    "symbol": chunk_data.symbol or "",
                    "source_type": "code",
                    "path": rel_path,
                    "file_extension": ext,
                },
            ))

    if qdrant_points:
        try:
            n = upsert_batch(qdrant_points)
            print(f"[embedding] stored {n} vectors")
        except Exception as exc:
            print(f"[embedding] batch upsert failed: {exc}")


async def _do_index(
    session: Any,
    repo: Any,
    job: Any,
    clone_url: str,
    commit_sha: str | None,
) -> dict[str, Any]:
    """Async version: same logic, sync I/O wrapped in run_in_executor."""
    loop = __import__("asyncio").get_running_loop()
    return await loop.run_in_executor(
        None, _do_index_sync, session, repo, job, clone_url, commit_sha
    )
