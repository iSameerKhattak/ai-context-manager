"""GitHub integration API endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from contextclaw.db.models import GithubInstallation, Membership, Organization, User
from contextclaw.integrations.github import get_install_url, list_installation_repos

router = APIRouter()


class InstallUrlResponse(BaseModel):
    install_url: str


class InstalledRepo(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    default_branch: str
    language: str | None = None


class InstallationResponse(BaseModel):
    id: str
    account_login: str
    account_type: str
    repos: list[InstalledRepo]


@router.get("/install-url")
async def get_github_install_url(
    org_slug: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InstallUrlResponse:
    """Get the GitHub App install URL for the current org."""
    app_id = os.environ.get("GITHUB_APP_ID", "")
    if not app_id:
        raise HTTPException(
            status_code=501,
            detail="GitHub integration not configured (missing GITHUB_APP_ID)",
        )
    return InstallUrlResponse(install_url=get_install_url(org_slug))


@router.get("/installations", response_model=list[InstallationResponse])
async def list_installations(
    org_id: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List GitHub App installations and their repos for an org."""
    if org_id:
        await _verify_org_access(session, org_id, user.id)

    query = select(GithubInstallation)
    if org_id:
        query = query.where(GithubInstallation.org_id == org_id)

    result = await session.execute(query)
    installations = result.scalars().all()

    responses = []
    for inst in installations:
        repos = await list_installation_repos(inst.installation_id)
        responses.append(
            InstallationResponse(
                id=str(inst.id),
                account_login=inst.account_login,
                account_type=inst.account_type,
                repos=[
                    InstalledRepo(
                        id=r["id"],
                        name=r["name"],
                        full_name=r["full_name"],
                        private=r.get("private", False),
                        default_branch=r.get("default_branch", "main"),
                        language=r.get("language"),
                    )
                    for r in repos
                ],
            )
        )
    return responses


async def _verify_org_access(
    session: AsyncSession, org_id: str, user_id: str
) -> None:
    result = await session.execute(
        select(Membership).where(
            Membership.org_id == org_id, Membership.user_id == user_id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Not a member of this org")
