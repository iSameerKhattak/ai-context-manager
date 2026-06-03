from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Coroutine
from uuid import UUID

from contextclaw.settings import settings

# ── Queue names ────────────────────────────────────────────────────

QUEUE_INDEXING = "contextclaw.indexing"
QUEUE_EMBEDDING = "contextclaw.embedding"
EXCHANGE_DEFAULT = "contextclaw.direct"


# ── Message schemas ────────────────────────────────────────────────


@dataclass
class IndexingJobMessage:
    """Published when a repo needs indexing."""

    repository_id: str
    project_id: str
    clone_url: str
    ref: str
    commit_sha: str | None = None
    priority: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "project_id": self.project_id,
            "clone_url": self.clone_url,
            "ref": self.ref,
            "commit_sha": self.commit_sha,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IndexingJobMessage:
        return cls(**data)


@dataclass
class EmbeddingJobMessage:
    """Published after a file is chunked — one per document."""

    document_id: str
    project_id: str
    chunk_ids: list[str]
    contents: list[str]
    languages: list[str | None]
    symbols: list[str | None]
    source_type: str = "code"

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "project_id": self.project_id,
            "chunk_ids": self.chunk_ids,
            "contents": self.contents,
            "languages": self.languages,
            "symbols": self.symbols,
            "source_type": self.source_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmbeddingJobMessage:
        return cls(**data)


# ── Publisher ──────────────────────────────────────────────────────


class QueuePublisher:
    """Publishes messages to RabbitMQ queues."""

    def __init__(self, url: str | None = None) -> None:
        self._url = url or settings.rabbitmq_url
        self._connection = None

    async def connect(self) -> None:
        import aio_pika

        self._connection = await aio_pika.connect_robust(self._url)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def publish_indexing(self, message: IndexingJobMessage) -> None:
        await self._publish(QUEUE_INDEXING, message.to_dict())

    async def publish_embedding(self, message: EmbeddingJobMessage) -> None:
        await self._publish(QUEUE_EMBEDDING, message.to_dict())

    async def _publish(self, queue_name: str, body: dict[str, Any]) -> None:
        import aio_pika

        if self._connection is None:
            await self.connect()

        async with self._connection.channel() as channel:
            queue = await channel.declare_queue(queue_name, durable=True)
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(body).encode("utf-8"),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=queue_name,
            )


# ── Consumer ───────────────────────────────────────────────────────

MessageHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class QueueConsumer:
    """Consumes messages from a RabbitMQ queue and dispatches to a handler."""

    def __init__(
        self,
        queue_name: str,
        handler: MessageHandler,
        url: str | None = None,
        prefetch_count: int = 1,
    ) -> None:
        self._queue_name = queue_name
        self._handler = handler
        self._url = url or settings.rabbitmq_url
        self._prefetch_count = prefetch_count
        self._connection = None

    async def start(self) -> None:
        import aio_pika

        self._connection = await aio_pika.connect_robust(self._url)
        async with self._connection:
            channel = await self._connection.channel()
            await channel.set_qos(prefetch_count=self._prefetch_count)
            queue = await channel.declare_queue(self._queue_name, durable=True)

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        try:
                            body = json.loads(message.body.decode("utf-8"))
                            await self._handler(body)
                        except Exception as exc:
                            print(f"[consumer] error processing {self._queue_name}: {exc}")

    async def stop(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
