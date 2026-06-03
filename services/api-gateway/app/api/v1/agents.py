from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from contextclaw.db.models import (
    AgentEvent as DBAgentEvent,
    AgentSession,
    Membership,
    Project,
    User,
)

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────


class AgentRunRequest(BaseModel):
    project_id: str
    agent_type: str = Field(
        default="repo",
        description="repo | doc | memory | architecture",
    )
    input: dict = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    session_id: str
    status: str


class AgentSessionOut(BaseModel):
    id: str
    project_id: str
    agent_type: str
    status: str
    input: dict | None
    output: dict | None
    started_at: str
    ended_at: str | None


class AgentEventOut(BaseModel):
    id: int | None
    session_id: str
    kind: str
    payload: dict
    ts: str


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


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("/run")
async def run_agent(
    body: AgentRunRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AgentRunResponse:
    """Start an agent run."""
    project = await _verify_project_access(session, body.project_id, user)

    agent_session = AgentSession(
        project_id=project.id,
        agent_type=body.agent_type,
        status="running",
        input=body.input,
    )
    session.add(agent_session)
    await session.commit()
    await session.refresh(agent_session)

    import asyncio
    from contextclaw.agent.runner import run_agent as run_agent_engine

    async def _on_event(
        session_id: UUID, kind: str, payload: dict
    ) -> None:
        event = DBAgentEvent(
            session_id=session_id,
            kind=kind,
            payload=payload,
        )
        session.add(event)
        await session.commit()

    # Run agent in background
    asyncio.create_task(_do_run(agent_session.id, body, project.id, _on_event))

    return AgentRunResponse(
        session_id=str(agent_session.id),
        status="running",
    )


async def _do_run(
    session_id: UUID,
    body: AgentRunRequest,
    project_id: UUID,
    on_event: Any,
) -> None:
    import asyncio
    from contextclaw.agent.runner import run_agent as run_agent_engine
    from contextclaw.db.engine import get_session as get_db_session

    # Get a new session for the background task
    async def _on_event_wrapper(
        sid: UUID, kind: str, payload: dict
    ) -> None:
        async with get_db_session() as bg_session:
            event = DBAgentEvent(session_id=sid, kind=kind, payload=payload)
            bg_session.add(event)
            await bg_session.commit()

    result = await run_agent_engine(
        session_id=session_id,
        project_id=str(project_id),
        agent_type=body.agent_type,
        input_data=body.input,
        on_event=_on_event_wrapper,
    )

    # Update session status
    async with get_db_session() as bg_session:
        result_obj = await bg_session.execute(
            select(AgentSession).where(AgentSession.id == session_id)
        )
        agent_session = result_obj.scalar_one_or_none()
        if agent_session:
            agent_session.status = result.get("status", "completed")
            agent_session.output = result
            agent_session.ended_at = datetime.now(timezone.utc)
            await bg_session.commit()


@router.get("/sessions")
async def list_sessions(
    project_id: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    query = select(AgentSession).order_by(AgentSession.started_at.desc())

    if project_id:
        await _verify_project_access(session, project_id, user)
        query = query.where(AgentSession.project_id == project_id)

    result = await session.execute(query)
    sessions = result.scalars().all()

    return {
        "sessions": [
            AgentSessionOut(
                id=str(s.id),
                project_id=str(s.project_id),
                agent_type=s.agent_type,
                status=s.status,
                input=s.input,
                output=s.output,
                started_at=s.started_at.isoformat(),
                ended_at=s.ended_at.isoformat() if s.ended_at else None,
            )
            for s in sessions
        ]
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AgentSessionOut:
    result = await session.execute(
        select(AgentSession).where(AgentSession.id == session_id)
    )
    agent_session = result.scalar_one_or_none()
    if not agent_session:
        raise HTTPException(status_code=404, detail="Session not found")

    await _verify_project_access(session, str(agent_session.project_id), user)

    return AgentSessionOut(
        id=str(agent_session.id),
        project_id=str(agent_session.project_id),
        agent_type=agent_session.agent_type,
        status=agent_session.status,
        input=agent_session.input,
        output=agent_session.output,
        started_at=agent_session.started_at.isoformat(),
        ended_at=agent_session.ended_at.isoformat() if agent_session.ended_at else None,
    )


@router.get("/sessions/{session_id}/events")
async def get_session_events(
    session_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    result = await session.execute(
        select(AgentSession).where(AgentSession.id == session_id)
    )
    agent_session = result.scalar_one_or_none()
    if not agent_session:
        raise HTTPException(status_code=404, detail="Session not found")

    await _verify_project_access(session, str(agent_session.project_id), user)

    events_result = await session.execute(
        select(DBAgentEvent)
        .where(DBAgentEvent.session_id == session_id)
        .order_by(DBAgentEvent.ts)
    )
    events = events_result.scalars().all()

    return {
        "events": [
            AgentEventOut(
                id=e.id,
                session_id=str(e.session_id),
                kind=e.kind,
                payload=e.payload,
                ts=e.ts.isoformat(),
            )
            for e in events
        ]
    }
