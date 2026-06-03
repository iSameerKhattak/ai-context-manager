"""
ContextClaw – shared domain models.

These Pydantic models define the core entities shared across all
services. They are the source of truth for serialization contracts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID, uuid7

from pydantic import BaseModel, ConfigDict, Field


# ── Primitives ─────────────────────────────────────────────────────

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> UUID:
    return uuid7()


# ── Organizations ──────────────────────────────────────────────────

class PlanTier(StrEnum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Organization(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=new_uuid)
    slug: str
    name: str
    plan: PlanTier = PlanTier.FREE
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    deleted_at: datetime | None = None


# ── Users & Memberships ────────────────────────────────────────────

class UserRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=new_uuid)
    external_id: str
    email: str
    name: str | None = None
    avatar_url: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Membership(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    org_id: UUID
    user_id: UUID
    role: UserRole
    created_at: datetime = Field(default_factory=utcnow)


# ── Projects & Repositories ────────────────────────────────────────

class Project(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=new_uuid)
    org_id: UUID
    slug: str
    name: str
    description: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class RepoProvider(StrEnum):
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


class RepoStatus(StrEnum):
    PENDING = "pending"
    INDEXING = "indexing"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


class Repository(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(default_factory=new_uuid)
    project_id: UUID
    provider: RepoProvider
    external_id: str
    full_name: str
    default_branch: str = "main"
    last_indexed_sha: str | None = None
    last_indexed_at: datetime | None = None
    status: RepoStatus = RepoStatus.PENDING
    json_metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata")


# ── Documents & Chunks ─────────────────────────────────────────────

class SourceType(StrEnum):
    CODE = "code"
    MARKDOWN = "markdown"
    CONFLUENCE = "confluence"
    NOTION = "notion"
    SLACK = "slack"
    JIRA = "jira"
    PDF = "pdf"
    HTML = "html"
    GOOGLE_DOCS = "google_docs"


class Document(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(default_factory=new_uuid)
    project_id: UUID
    repository_id: UUID | None = None
    source_type: SourceType
    source_uri: str
    path: str | None = None
    title: str | None = None
    content_hash: str
    language: str | None = None
    size_bytes: int | None = None
    json_metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata")
    indexed_at: datetime | None = None


class Chunk(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(default_factory=new_uuid)
    document_id: UUID
    project_id: UUID
    ordinal: int
    content: str
    token_count: int | None = None
    start_line: int | None = None
    end_line: int | None = None
    symbol: str | None = None
    json_metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata")


# ── Embeddings ─────────────────────────────────────────────────────

class EmbeddingRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: UUID
    model: str
    dim: int
    qdrant_point_id: str
    created_at: datetime = Field(default_factory=utcnow)


# ── Chat ───────────────────────────────────────────────────────────

class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Citation(BaseModel):
    chunk_id: UUID
    score: float = Field(ge=0, le=1)
    source_type: str = ""
    path: str = ""
    snippet: str = ""


class Message(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=new_uuid)
    conversation_id: UUID
    role: MessageRole
    content: str
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_cents: float | None = None
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


class Conversation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=new_uuid)
    project_id: UUID
    user_id: UUID | None = None
    title: str | None = None
    agent_session_id: UUID | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


# ── Memory Facts ───────────────────────────────────────────────────

class MemoryFact(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=new_uuid)
    project_id: UUID
    scope: str  # org | project | repo | user
    statement: str
    source: str  # user | agent | auto
    confidence: float = Field(default=1.0, ge=0, le=1)
    embedding_id: str | None = None
    asserted_by: UUID | None = None
    superseded_by: UUID | None = None
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime | None = None


# ── Knowledge Graph ────────────────────────────────────────────────

class NodeType(StrEnum):
    SERVICE = "service"
    MODULE = "module"
    PERSON = "person"
    LIBRARY = "library"
    ENDPOINT = "endpoint"
    DECISION = "decision"
    CONCEPT = "concept"


class RelationType(StrEnum):
    OWNS = "OWNS"
    DEPENDS_ON = "DEPENDS_ON"
    DECIDED_BY = "DECIDED_BY"
    DISCUSSED_IN = "DISCUSSED_IN"
    IMPLEMENTS = "IMPLEMENTS"
    REFERENCES = "REFERENCES"
    EXTENDS = "EXTENDS"
    CONTAINS = "CONTAINS"


class KnowledgeNode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=new_uuid)
    project_id: UUID
    type: NodeType
    name: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    embedding_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class KnowledgeEdge(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=new_uuid)
    src_node_id: UUID
    dst_node_id: UUID
    relation: RelationType
    weight: float = Field(default=1.0, ge=0, le=1)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


# ── Agent Sessions ─────────────────────────────────────────────────

class AgentType(StrEnum):
    REPO = "repo"
    DOC = "doc"
    ARCHITECTURE = "architecture"
    GRAPH = "graph"
    ONBOARDING = "onboarding"
    MEMORY = "memory"


class AgentStatus(StrEnum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentSession(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=new_uuid)
    project_id: UUID
    agent_type: AgentType
    status: AgentStatus
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    trace_id: str | None = None
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None


class AgentEventKind(StrEnum):
    STEP = "step"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    LOG = "log"
    ERROR = "error"


class AgentEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None  # BigSerial
    session_id: UUID
    ts: datetime = Field(default_factory=utcnow)
    kind: AgentEventKind
    payload: dict[str, Any]


# ── API / Search Contracts ─────────────────────────────────────────

class SearchResult(BaseModel):
    chunk_id: UUID
    score: float
    source: dict[str, Any]
    snippet: str


class SearchRequest(BaseModel):
    project_id: UUID
    query: str
    k: int = Field(default=10, ge=1, le=100)
    filters: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    results: list[SearchResult]
    took_ms: int


# ── Generic pagination wrapper ─────────────────────────────────────

T = TypeVar("T")


class CursorPage(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    total: int | None = None
