"""FastAPI dependency injection — auth + DB sessions."""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from contextclaw.auth import ClerkUser, get_or_create_db_user, verify_clerk_token
from contextclaw.db.engine import get_session
from contextclaw.db.models import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Validate Clerk JWT, resolve/create user, return ORM User."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    clerk_user = await verify_clerk_token(credentials.credentials)
    if clerk_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    db_user, _ = await get_or_create_db_user(session, clerk_user)
    return db_user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None if no auth."""
    if credentials is None:
        return None
    clerk_user = await verify_clerk_token(credentials.credentials)
    if clerk_user is None:
        return None
    db_user, _ = await get_or_create_db_user(session, clerk_user)
    return db_user
