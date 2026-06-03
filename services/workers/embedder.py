"""
ContextClaw Embedding Worker.

Consumes embedding generation messages and pushes vectors to Qdrant.

Usage:
    python -m workers.embedder
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any
from uuid import UUID

from contextclaw.embeddings.router import get_embedding_provider
from contextclaw.queue.rabbitmq import QUEUE_EMBEDDING, QueueConsumer
from contextclaw.settings import settings
from contextclaw.vector.qdrant import ensure_collection, upsert_batch


async def handle_embedding_job(body: dict) -> None:
    chunk_ids = body.get("chunk_ids", [])
    contents = body.get("contents", [])
    languages = body.get("languages", [])
    symbols = body.get("symbols", [])
    project_id = body.get("project_id")
    document_id = body.get("document_id")
    source_type = body.get("source_type", "code")

    if not chunk_ids or not contents:
        return

    provider = get_embedding_provider()
    ensure_collection(dim=provider.dim)

    try:
        vectors = provider.embed(contents)
    except Exception as exc:
        print(f"[embed-worker] embedding failed: {exc}")
        return

    points: list[tuple[UUID, list[float], dict[str, Any]]] = []
    for idx, (cid, vec) in enumerate(zip(chunk_ids, vectors)):
        lang = languages[idx] if idx < len(languages) else None
        sym = symbols[idx] if idx < len(symbols) else None
        points.append((
            UUID(cid),
            vec,
            {
                "chunk_id": cid,
                "project_id": str(project_id) if project_id else "",
                "document_id": str(document_id) if document_id else "",
                "language": lang or "text",
                "symbol": sym or "",
                "source_type": source_type,
            },
        ))

    try:
        n = upsert_batch(points)
        print(f"[embed-worker] stored {n} vectors for doc {document_id}")
    except Exception as exc:
        print(f"[embed-worker] batch upsert failed: {exc}")


async def main() -> None:
    url = settings.rabbitmq_url
    if not url or url == "amqp://guest:guest@localhost:5672/":
        print("[embed-worker] RabbitMQ not configured, exiting")
        sys.exit(0)

    print(f"[embed-worker] connecting to {url}")
    consumer = QueueConsumer(
        queue_name=QUEUE_EMBEDDING,
        handler=handle_embedding_job,
        url=url,
        prefetch_count=10,
    )
    await consumer.start()


if __name__ == "__main__":
    asyncio.run(main())
