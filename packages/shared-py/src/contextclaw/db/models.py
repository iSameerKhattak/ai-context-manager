"""
ContextClaw – SQLAlchemy ORM models.

Mirrors the Pydantic models in contextclaw.models.
All tables use UUIDv7 primary keys, UTC timestamps, and soft-delete.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid7

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, TSVECTOR, UUID as PUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> UUID:
    return uuid7()


class Base(DeclarativeBase):
    pass


# ── Organizations ──────────────────────────────────────────────────


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    plan: Mapped[str] = mapped_column(String(32), default="free")
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    projects: Mapped[list["Project"]] = relationship(back_populates="organization")
    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")

    __table_args__ = (
        Index("idx_organizations_plan", "plan"),
    )


# ── Users & Memberships ────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    external_id: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(256))
    avatar_url: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")


class Membership(Base):
    __tablename__ = "memberships"

    org_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(
        String(16), default="member"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    organization: Mapped["Organization"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")

    __table_args__ = (
        CheckConstraint(
            "role IN ('owner','admin','member','viewer')", name="ck_membership_role"
        ),
    )


# ── Projects & Repositories ────────────────────────────────────────


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(CITEXT, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    organization: Mapped["Organization"] = relationship(back_populates="projects")
    repositories: Mapped[list["Repository"]] = relationship(back_populates="project")

    __table_args__ = (
        Index("idx_projects_org_id", "org_id"),
        Index("uq_projects_org_slug", "org_id", "slug", unique=True),
    )


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    project_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(256), nullable=False)
    full_name: Mapped[str] = mapped_column(String(512), nullable=False)
    clone_url: Mapped[str | None] = mapped_column(String(1024))
    default_branch: Mapped[str] = mapped_column(String(128), default="main")
    last_indexed_sha: Mapped[str | None] = mapped_column(String(64))
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    current_job_id: Mapped[UUID | None] = mapped_column(
        PUUID, ForeignKey("indexing_jobs.id", ondelete="SET NULL")
    )
    json_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)

    project: Mapped["Project"] = relationship(back_populates="repositories")

    __table_args__ = (
        Index("idx_repositories_project_status", "project_id", "status"),
        Index("uq_repositories_provider_external", "provider", "external_id", unique=True),
    )


class GithubInstallation(Base):
    __tablename__ = "github_installations"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    org_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    installation_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    account_login: Mapped[str] = mapped_column(String(256), nullable=False)
    account_type: Mapped[str] = mapped_column(String(32), nullable=False)
    permissions: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class GithubPullRequest(Base):
    __tablename__ = "github_pull_requests"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    repository_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(512))
    body: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(256))
    state: Mapped[str] = mapped_column(String(32), default="open")
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    files_changed: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    __table_args__ = (
        Index("idx_github_pr_repo_number", "repository_id", "number", unique=True),
    )


# ── Indexing Jobs ──────────────────────────────────────────────────


class IndexingJob(Base):
    __tablename__ = "indexing_jobs"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    repository_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    ref: Mapped[str] = mapped_column(String(128), nullable=False)
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    files_total: Mapped[int | None] = mapped_column(Integer)
    files_indexed: Mapped[int | None] = mapped_column(Integer)
    chunks_created: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    __table_args__ = (
        Index("idx_indexing_jobs_repo_status", "repository_id", "status"),
    )


# ── Documents & Chunks ─────────────────────────────────────────────


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    project_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    repository_id: Mapped[UUID | None] = mapped_column(
        PUUID, ForeignKey("repositories.id", ondelete="SET NULL")
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(512))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str | None] = mapped_column(String(32))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    json_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_documents_project_source", "project_id", "source_type"),
        Index("idx_documents_metadata", "metadata", postgresql_using="gin"),
        Index("uq_documents_source_uri", "project_id", "source_uri", unique=True),
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    document_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(PUUID, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    symbol: Mapped[str | None] = mapped_column(String(256))
    fts: Mapped[str | None] = mapped_column(
        TSVECTOR, server_default=text("to_tsvector('english', content)")
    )
    json_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)

    __table_args__ = (
        Index("idx_chunks_fts", "fts", postgresql_using="gin"),
        Index("idx_chunks_project_document", "project_id", "document_id", "ordinal"),
    )


class EmbeddingRecord(Base):
    __tablename__ = "embeddings"

    chunk_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("chunks.id", ondelete="CASCADE"), primary_key=True
    )
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    dim: Mapped[int] = mapped_column(Integer, nullable=False)
    qdrant_point_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


# ── Conversations & Messages ───────────────────────────────────────


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    project_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(PUUID)
    title: Mapped[str | None] = mapped_column(String(256))
    agent_session_id: Mapped[UUID | None] = mapped_column(PUUID)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")

    __table_args__ = (
        Index("idx_conversations_project_updated", "project_id", "updated_at"),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    conversation_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(String(64))
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    cost_cents: Mapped[float | None] = mapped_column(Float)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("idx_messages_conversation_created", "conversation_id", "created_at"),
    )


# ── Memory Facts ───────────────────────────────────────────────────


class MemoryFact(Base):
    __tablename__ = "memory_facts"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    project_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    embedding_id: Mapped[str | None] = mapped_column(Text)
    asserted_by: Mapped[UUID | None] = mapped_column(PUUID)
    superseded_by: Mapped[UUID | None] = mapped_column(
        PUUID, ForeignKey("memory_facts.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_memory_facts_active", "project_id", "scope"),
    )


# ── Knowledge Graph ────────────────────────────────────────────────


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    project_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    embedding_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    __table_args__ = (
        Index("idx_knowledge_nodes_project_type", "project_id", "type"),
        Index("uq_knowledge_nodes_name", "project_id", "type", "name", unique=True),
    )


class KnowledgeEdge(Base):
    __tablename__ = "knowledge_edges"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    src_node_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False
    )
    dst_node_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False
    )
    relation: Mapped[str] = mapped_column(String(32), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    __table_args__ = (
        Index("idx_knowledge_edges_src", "src_node_id", "relation"),
        Index("idx_knowledge_edges_dst", "dst_node_id", "relation"),
    )


# ── Agent Sessions ─────────────────────────────────────────────────


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id: Mapped[UUID] = mapped_column(PUUID, primary_key=True, default=new_uuid)
    project_id: Mapped[UUID] = mapped_column(PUUID, nullable=False)
    agent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    input: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    trace_id: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[UUID] = mapped_column(
        PUUID, ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)

    __table_args__ = (
        Index("idx_agent_events_session", "session_id", "ts"),
    )
