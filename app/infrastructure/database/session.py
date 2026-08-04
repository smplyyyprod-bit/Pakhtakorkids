from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, async_sessionmaker
)

from app.core.config import get_settings

settings = get_settings()

# Convert postgresql:// to postgresql+asyncpg://
database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    database_url,
    echo=settings.database_echo,
    future=True,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncSession:
    """Get database session."""
    async with SessionLocal() as session:
        yield session


@asynccontextmanager
async def get_db_context():
    """Context manager for database session."""
    async with SessionLocal() as session:
        yield session
