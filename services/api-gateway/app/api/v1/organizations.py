from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from contextclaw.db.models import Membership, Organization, Project, User

router = APIRouter()


class OrgCreate(BaseModel):
    slug: str
    name: str


class OrgOut(BaseModel):
    id: str
    slug: str
    name: str
    plan: str
    created_at: str


class ProjectCreate(BaseModel):
    slug: str
    name: str
    description: str | None = None


class ProjectOut(BaseModel):
    id: str
    org_id: str
    slug: str
    name: str
    description: str | None
    created_at: str


@router.get("/me")
async def get_my_orgs(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Return all orgs the current user belongs to."""
    result = await session.execute(
        select(Membership).where(Membership.user_id == user.id)
    )
    memberships = result.scalars().all()

    org_ids = [m.org_id for m in memberships]
    if not org_ids:
        return {"organizations": []}

    result = await session.execute(
        select(Organization).where(Organization.id.in_(org_ids))  # type: ignore[arg-type]
    )
    orgs = result.scalars().all()
    return {
        "organizations": [
            OrgOut(
                id=str(o.id),
                slug=o.slug,
                name=o.name,
                plan=o.plan,
                created_at=o.created_at.isoformat(),
            )
            for o in orgs
        ]
    }


@router.post("")
async def create_org(
    body: OrgCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Create a new org and add the current user as owner."""
    existing = await session.execute(
        select(Organization).where(Organization.slug == body.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Org slug already taken")

    org = Organization(slug=body.slug, name=body.name)
    session.add(org)
    await session.flush()

    membership = Membership(org_id=org.id, user_id=user.id, role="owner")
    session.add(membership)

    return OrgOut(
        id=str(org.id),
        slug=org.slug,
        name=org.name,
        plan=org.plan,
        created_at=org.created_at.isoformat(),
    )


@router.get("/{org_id}/projects")
async def list_projects(
    org_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List projects in an org (verify membership)."""
    await _verify_org_membership(session, org_id, user.id)

    result = await session.execute(
        select(Project).where(Project.org_id == org_id)
    )
    projects = result.scalars().all()

    return {
        "projects": [
            ProjectOut(
                id=str(p.id),
                org_id=str(p.org_id),
                slug=p.slug,
                name=p.name,
                description=p.description,
                created_at=p.created_at.isoformat(),
            )
            for p in projects
        ]
    }


@router.post("/{org_id}/projects")
async def create_project(
    org_id: str,
    body: ProjectCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Create a project in an org."""
    await _verify_org_membership(session, org_id, user.id)

    existing = await session.execute(
        select(Project).where(
            Project.org_id == org_id, Project.slug == body.slug
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Project slug already taken")

    project = Project(
        org_id=org_id,
        slug=body.slug,
        name=body.name,
        description=body.description,
    )
    session.add(project)

    return ProjectOut(
        id=str(project.id),
        org_id=str(project.org_id),
        slug=project.slug,
        name=project.name,
        description=project.description,
        created_at=project.created_at.isoformat(),
    )


async def _verify_org_membership(
    session: AsyncSession, org_id: str, user_id: str
) -> None:
    result = await session.execute(
        select(Membership).where(
            Membership.org_id == org_id, Membership.user_id == user_id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )
