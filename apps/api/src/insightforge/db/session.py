from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from insightforge.core.config import Settings, get_settings


@lru_cache
def get_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=1_800,
        pool_size=10,
        max_overflow=20,
    )


@lru_cache
def get_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        get_engine(database_url),
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_session(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[AsyncSession]:
    async with get_session_factory(settings.database_url)() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
