"""
ContextClaw Repo Sync Worker.

Consumes indexing job messages from RabbitMQ, clones repos,
chunks code, and generates embeddings.

Usage:
    python -m workers.repo_sync
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select
from contextclaw.db.engine import get_session
from contextclaw.db.models import Repository
from contextclaw.indexer.index import index_repository
from contextclaw.queue.rabbitmq import QUEUE_INDEXING, QueueConsumer
from contextclaw.settings import settings


async def handle_indexing_job(body: dict) -> None:
    repo_id = body.get("repository_id")
    commit_sha = body.get("commit_sha")

    if not repo_id:
        print("[repo-sync] missing repository_id")
        return

    session_gen = get_session()
    async with session_gen as session:
        result = await session.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        repo = result.scalar_one_or_none()

    if repo is None:
        print(f"[repo-sync] repository not found: {repo_id}")
        return

    print(f"[repo-sync] indexing {repo.full_name} (sha={commit_sha or 'latest'})")

    def _run():
        return index_repository(repo, commit_sha=commit_sha)

    loop = asyncio.get_running_loop()
    summary = await loop.run_in_executor(None, _run)
    print(f"[repo-sync] done {repo.full_name}: {summary}")


async def main() -> None:
    url = settings.rabbitmq_url
    if not url or url == "amqp://guest:guest@localhost:5672/":
        print("[repo-sync] RabbitMQ not configured, exiting")
        sys.exit(0)

    print(f"[repo-sync] connecting to {url}")
    consumer = QueueConsumer(
        queue_name=QUEUE_INDEXING,
        handler=handle_indexing_job,
        url=url,
        prefetch_count=1,
    )
    await consumer.start()


if __name__ == "__main__":
    asyncio.run(main())
