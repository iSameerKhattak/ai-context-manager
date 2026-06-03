from __future__ import annotations

from typing import Any
from uuid import UUID

from qdrant_client import QdrantClient as _QdrantClient
from qdrant_client.http import models as qm
from qdrant_client.models import Distance, VectorParams

from contextclaw.settings import settings

# Default collection name
COLLECTION_NAME = "contextclaw_chunks"

# Payload schema keys used across queries
_PAYLOAD_KEYS = {
    "chunk_id": "keyword",
    "document_id": "keyword",
    "project_id": "keyword",
    "language": "keyword",
    "symbol": "keyword",
    "source_type": "keyword",
    "path": "keyword",
    "file_extension": "keyword",
}

_CHUNK_CONTENT_KEY = "content"


def _get_client() -> _QdrantClient:
    return _QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=30,
    )


def ensure_collection(dim: int = 1536, force: bool = False) -> None:
    """Create the Qdrant collection if it doesn't exist.

    *dim* should match the embedding model output dimension
    (1536 for text-embedding-3-small, 1024 for deepseek-text-embedding-v2).
    """
    client = _get_client()
    collections = client.get_collections().collections
    exists = any(c.name == COLLECTION_NAME for c in collections)

    if exists and not force:
        return

    if exists and force:
        client.delete_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )

    # Create payload indexes for filtered search
    for field, field_type in _PAYLOAD_KEYS.items():
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field,
            field_type=field_type,
        )


def upsert_chunk_embedding(
    chunk_id: UUID,
    project_id: UUID,
    document_id: UUID,
    vector: list[float],
    content: str,
    payload: dict[str, Any] | None = None,
) -> str:
    """Upsert a single chunk embedding into Qdrant.

    Returns the Qdrant point ID.
    """
    client = _get_client()
    point_id = str(chunk_id)
    base_payload: dict[str, Any] = {
        "chunk_id": str(chunk_id),
        "project_id": str(project_id),
        "document_id": str(document_id),
        _CHUNK_CONTENT_KEY: content,
    }
    if payload:
        base_payload.update(payload)

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[qm.PointStruct(id=point_id, vector=vector, payload=base_payload)],
    )
    return point_id


def upsert_batch(
    points: list[tuple[UUID, list[float], dict[str, Any]]],
) -> int:
    """Batch upsert chunk embeddings.

    Each tuple is (chunk_id, vector, payload_dict).
    Returns the number of points upserted.
    """
    client = _get_client()
    point_structs = [
        qm.PointStruct(id=str(cid), vector=vec, payload=pl) for cid, vec, pl in points
    ]

    if not point_structs:
        return 0

    # Must ensure collection exists first
    dim = len(point_structs[0].vector)
    ensure_collection(dim=dim)

    client.upsert(collection_name=COLLECTION_NAME, points=point_structs, wait=True)
    return len(point_structs)


def search(
    query_vector: list[float],
    project_id: str,
    k: int = 10,
    score_threshold: float | None = None,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Search for the *k* nearest neighbors of *query_vector*.

    Returns a list of dicts with keys: chunk_id, score, content, and
    any additional payload fields.
    """
    client = _get_client()

    must_filters: list[qm.Filter] = [
        qm.FieldCondition(
            key="project_id",
            match=qm.MatchValue(value=project_id),
        )
    ]

    if filters:
        for key, value in filters.items():
            if key in _PAYLOAD_KEYS:
                must_filters.append(
                    qm.FieldCondition(
                        key=key,
                        match=qm.MatchValue(value=value),
                    )
                )

    query_filter = qm.Filter(must=must_filters) if must_filters else None

    hits = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=query_filter,
        limit=k,
        score_threshold=score_threshold,
        with_payload=True,
    ).points

    results = []
    for hit in hits:
        payload = hit.payload or {}
        results.append({
            "chunk_id": payload.pop("chunk_id", str(hit.id)),
            "score": hit.score,
            "content": payload.pop(_CHUNK_CONTENT_KEY, ""),
            **payload,
        })

    return results


def delete_chunk_embeddings(chunk_ids: list[UUID]) -> int:
    """Delete embeddings for the given chunk IDs.

    Returns number of points deleted.
    """
    client = _get_client()
    result = client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=qm.Filter(
            must=[
                qm.FieldCondition(
                    key="chunk_id",
                    match=qm.MatchAny(any=[str(cid) for cid in chunk_ids]),
                )
            ]
        ),
    )
    return len(chunk_ids)
