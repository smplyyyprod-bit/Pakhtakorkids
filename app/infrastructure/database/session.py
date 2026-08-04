"""Async engine and session factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.async_database_url,
    echo=settings.database_echo,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_db_context() -> AsyncIterator[AsyncSession]:
    """Session scope for code outside the aiogram middleware chain.

    Handlers should take the session injected by DbSessionMiddleware instead of
    opening their own; this exists for scheduler jobs and startup hooks.
    """
    async with SessionLocal() as session:
        yield session
