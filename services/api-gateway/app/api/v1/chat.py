from __future__ import annotations

import json
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from contextclaw.db.models import (
    Chunk,
    Conversation,
    Document,
    Membership,
    Message,
    Project,
    User,
)
from contextclaw.models import Citation
from contextclaw.search.hybrid import hybrid_search, HybridSearchConfig
from contextclaw.settings import settings

router = APIRouter()


# ── Request / Response schemas ─────────────────────────────────────


class ConversationCreate(BaseModel):
    project_id: str
    title: str | None = None


class ConversationOut(BaseModel):
    id: str
    project_id: str
    title: str | None
    created_at: str
    updated_at: str


class MessageSend(BaseModel):
    content: str
    model: str | None = None


class CitationOut(BaseModel):
    chunk_id: str
    score: float
    source_type: str
    path: str
    snippet: str


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    model: str | None
    tokens_in: int | None
    tokens_out: int | None
    citations: list[CitationOut]
    created_at: str


class ConversationWithMessages(BaseModel):
    id: str
    project_id: str
    title: str | None
    messages: list[MessageOut]
    created_at: str
    updated_at: str


# ── Helpers ────────────────────────────────────────────────────────


async def _verify_project_access(
    session: AsyncSession, project_id: str, user: User
) -> Project:
    result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await session.execute(
        select(Membership).where(
            Membership.org_id == project.org_id, Membership.user_id == user.id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Access denied")

    return project


def _conversation_out(c: Conversation) -> ConversationOut:
    return ConversationOut(
        id=str(c.id),
        project_id=str(c.project_id),
        title=c.title,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


def _message_out(m: Message, citations: list[CitationOut] | None = None) -> MessageOut:
    return MessageOut(
        id=str(m.id),
        conversation_id=str(m.conversation_id),
        role=m.role,
        content=m.content,
        model=m.model,
        tokens_in=m.tokens_in,
        tokens_out=m.tokens_out,
        citations=citations or [],
        created_at=m.created_at.isoformat(),
    )


# ── Conversation endpoints ─────────────────────────────────────────


@router.post("/conversations")
async def create_conversation(
    body: ConversationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ConversationOut:
    project = await _verify_project_access(session, body.project_id, user)

    conv = Conversation(
        project_id=project.id,
        user_id=user.id,
        title=body.title or "New Chat",
    )
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return _conversation_out(conv)


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ConversationWithMessages:
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await _verify_project_access(session, str(conv.project_id), user)

    msg_result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    return ConversationWithMessages(
        id=str(conv.id),
        project_id=str(conv.project_id),
        title=conv.title,
        messages=[_message_out(m) for m in messages],
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: MessageSend,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MessageOut:
    import asyncio
    from contextclaw.embeddings.router import get_embedding_provider
    from contextclaw.llm import router as llm_router

    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await _verify_project_access(session, str(conv.project_id), user)

    # Save user message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=body.content,
    )
    session.add(user_msg)

    # Get conversation history
    msg_result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    history = msg_result.scalars().all()

    # Build history for LLM
    history_msgs = [
        {"role": m.role, "content": m.content}
        for m in history[-10:]  # Last 10 messages
    ]

    # RAG: search relevant context
    loop = asyncio.get_running_loop()

    def _search() -> list[dict]:
        provider = get_embedding_provider()
        query_vector = provider.embed_one(body.content)
        raw = hybrid_search(
            project_id=str(conv.project_id),
            query_text=body.content,
            query_vector=query_vector,
            config=HybridSearchConfig(final_k=8),
        )
        return [
            {
                "chunk_id": str(r.chunk_id),
                "score": r.score,
                "path": r.source.get("path", ""),
                "snippet": r.snippet,
                "source_type": r.source.get("source_type", "code"),
            }
            for r in raw
        ]

    context_chunks = await loop.run_in_executor(None, _search)

    # Generate LLM response
    system_prompt = (
        "You are ContextClaw, an AI assistant for software teams. "
        "Answer the user's question using the provided code context. "
        "Cite specific files and symbols when relevant. "
        "If the context doesn't contain the answer, say so clearly."
    )

    def _complete() -> str | None:
        return llm_router.rag_complete(
            system_prompt=system_prompt,
            context_chunks=context_chunks,
            user_query=body.content,
            conversation_history=history_msgs[:-1],  # exclude current user msg
            model=body.model,
        )

    reply_text = await loop.run_in_executor(None, _complete)
    reply_text = reply_text or "I'm sorry, I couldn't generate a response."

    # Save assistant message
    citations = [
        Citation(
            chunk_id=UUID(c["chunk_id"]),
            score=c["score"],
            source_type=c.get("source_type", "code"),
            path=c.get("path", ""),
            snippet=c.get("snippet", "")[:200],
        )
        for c in context_chunks[:5]
    ]

    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=reply_text,
        model=body.model or "gpt-4o-mini",
        citations=[c.model_dump() for c in citations],
    )
    session.add(assistant_msg)

    # Update conversation timestamp + title from first exchange
    if not conv.title or conv.title == "New Chat":
        conv.title = body.content[:80] + ("..." if len(body.content) > 80 else "")

    await session.commit()
    await session.refresh(assistant_msg)

    return _message_out(
        assistant_msg,
        citations=[
            CitationOut(
                chunk_id=str(c.chunk_id),
                score=c.score,
                source_type=c.source_type,
                path=c.path,
                snippet=c.snippet,
            )
            for c in citations
        ],
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await _verify_project_access(session, str(conv.project_id), user)

    await session.delete(conv)
    await session.commit()
    return {"status": "deleted"}
