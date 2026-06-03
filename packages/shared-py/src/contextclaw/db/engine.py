from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from contextclaw.db.models import Base

_engine = None
_async_session_maker = None


def get_database_url() -> str:
    return os.environ.get(
        "POSTGRES_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/contextclaw",
    )


async def init_engine(database_url: str | None = None) -> None:
    global _engine, _async_session_maker
    url = database_url or get_database_url()
    _engine = create_async_engine(url, poolclass=NullPool, echo=False)
    _async_session_maker = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )


async def close_engine() -> None:
    global _engine, _async_session_maker
    if _engine:
        await _engine.dispose()
    _engine = None
    _async_session_maker = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _async_session_maker is None:
        await init_engine()
    async with _async_session_maker() as session:  # type: ignore[union-attr]
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    if _engine is None:
        await init_engine()
    async with _engine.begin() as conn:  # type: ignore[union-attr]
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    if _engine is None:
        await init_engine()
    async with _engine.begin() as conn:  # type: ignore[union-attr]
        await conn.run_sync(Base.metadata.drop_all)
