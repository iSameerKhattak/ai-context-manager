from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from contextclaw.db.models import Membership, MemoryFact, Project, User

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────


class FactOut(BaseModel):
    id: str
    project_id: str
    scope: str
    statement: str
    source: str
    confidence: float
    created_at: str
    expires_at: str | None = None


class FactCreate(BaseModel):
    project_id: str
    statement: str
    scope: str = "project"
    confidence: float = 1.0
    source: str = "user"


class FactUpdate(BaseModel):
    statement: str | None = None
    confidence: float | None = None
    scope: str | None = None


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


@router.get("/facts")
async def list_facts(
    project_id: str,
    scope: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await _verify_project_access(session, project_id, user)

    query = select(MemoryFact).where(
        MemoryFact.project_id == project_id,
        MemoryFact.superseded_by.is_(None),
    )
    if scope:
        query = query.where(MemoryFact.scope == scope)
    query = query.order_by(MemoryFact.created_at.desc())

    result = await session.execute(query)
    facts = result.scalars().all()

    return {
        "facts": [
            FactOut(
                id=str(f.id),
                project_id=str(f.project_id),
                scope=f.scope,
                statement=f.statement,
                source=f.source,
                confidence=f.confidence,
                created_at=f.created_at.isoformat(),
                expires_at=f.expires_at.isoformat() if f.expires_at else None,
            )
            for f in facts
        ]
    }


@router.post("/facts")
async def assert_fact(
    body: FactCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FactOut:
    await _verify_project_access(session, body.project_id, user)

    fact = MemoryFact(
        project_id=body.project_id,
        statement=body.statement,
        scope=body.scope,
        source=body.source,
        confidence=body.confidence,
        asserted_by=user.id,
    )
    session.add(fact)
    await session.commit()
    await session.refresh(fact)

    return FactOut(
        id=str(fact.id),
        project_id=str(fact.project_id),
        scope=fact.scope,
        statement=fact.statement,
        source=fact.source,
        confidence=fact.confidence,
        created_at=fact.created_at.isoformat(),
    )


@router.patch("/facts/{fact_id}")
async def update_fact(
    fact_id: str,
    body: FactUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FactOut:
    result = await session.execute(
        select(MemoryFact).where(MemoryFact.id == fact_id)
    )
    fact = result.scalar_one_or_none()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")

    await _verify_project_access(session, str(fact.project_id), user)

    if body.statement is not None:
        fact.statement = body.statement
    if body.confidence is not None:
        fact.confidence = body.confidence
    if body.scope is not None:
        fact.scope = body.scope

    await session.commit()
    await session.refresh(fact)

    return FactOut(
        id=str(fact.id),
        project_id=str(fact.project_id),
        scope=fact.scope,
        statement=fact.statement,
        source=fact.source,
        confidence=fact.confidence,
        created_at=fact.created_at.isoformat(),
    )


@router.delete("/facts/{fact_id}")
async def delete_fact(
    fact_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    result = await session.execute(
        select(MemoryFact).where(MemoryFact.id == fact_id)
    )
    fact = result.scalar_one_or_none()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")

    await _verify_project_access(session, str(fact.project_id), user)

    await session.delete(fact)
    await session.commit()
    return {"status": "deleted"}
