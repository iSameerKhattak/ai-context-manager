"""
ContextClaw – Clerk JWT authentication wrapper.

Provides verify_clerk_token() and async_get_or_create_user()
used by FastAPI dependency injection in the API gateway.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx

_JWKS_CACHE: dict[str, Any] = {}


@dataclass
class ClerkUser:
    """Verified Clerk session user."""

    sub: str  # Clerk user ID
    email: str | None
    name: str | None
    avatar_url: str | None
    org_id: str | None = None
    org_role: str | None = None


async def get_jwks_client() -> Any:
    """Fetch and cache Clerk JWKS keys."""
    global _JWKS_CACHE
    jwks_url = os.environ.get(
        "CLERK_JWKS_URL",
        "https://clerk.contextclaw.dev/.well-known/jwks.json",
    )
    if not _JWKS_CACHE:
        async with httpx.AsyncClient() as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            _JWKS_CACHE = resp.json()
    return _JWKS_CACHE


async def verify_clerk_token(token: str) -> ClerkUser | None:
    """
    Verify a Clerk session token and extract user info.

    For MVP we call Clerk's /v1/sessions/verify endpoint.
    In production we would verify the JWT locally using JWKS.
    """
    secret_key = os.environ.get("CLERK_SECRET_KEY", "")
    if not secret_key:
        return None

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.clerk.com/v1/sessions/verify",
            headers={"Authorization": f"Bearer {secret_key}"},
            json={"token": token},
        )
        if resp.status_code != 200:
            return None
        data = resp.json()

    return ClerkUser(
        sub=data.get("user_id", ""),
        email=data.get("email", None),
        name=data.get("name", None),
        avatar_url=data.get("avatar_url", None),
        org_id=data.get("org_id", None),
        org_role=data.get("org_role", None),
    )


async def resolve_clerk_user(sub: str) -> dict[str, Any] | None:
    """Fetch full user details from Clerk API."""
    secret_key = os.environ.get("CLERK_SECRET_KEY", "")
    if not secret_key:
        return None
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.clerk.com/v1/users/{sub}",
            headers={"Authorization": f"Bearer {secret_key}"},
        )
        if resp.status_code != 200:
            return None
        return resp.json()


async def get_or_create_db_user(
    session: Any, clerk_user: ClerkUser
) -> tuple[Any, bool]:
    """
    Look up a User by external_id, create if not found.
    Returns (user, was_created).
    """
    from sqlalchemy import select

    from contextclaw.db.models import User

    result = await session.execute(
        select(User).where(User.external_id == clerk_user.sub)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            external_id=clerk_user.sub,
            email=clerk_user.email or "",
            name=clerk_user.name,
            avatar_url=clerk_user.avatar_url,
        )
        session.add(user)
        await session.flush()
        return user, True

    # Update fields that may have changed
    if clerk_user.email and user.email != clerk_user.email:
        user.email = clerk_user.email
    if clerk_user.name:
        user.name = clerk_user.name
    if clerk_user.avatar_url:
        user.avatar_url = clerk_user.avatar_url

    return user, False
