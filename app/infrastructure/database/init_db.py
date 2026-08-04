from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import Base, engine, Role, User, Branch, Coach
from app.infrastructure.database.session import SessionLocal

logger = get_logger()


async def init_db() -> None:
    """Initialize database with tables and seed data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created successfully")

    # Seed default data
    async with SessionLocal() as session:
        await seed_default_data(session)


async def seed_default_data(session: AsyncSession) -> None:
    """Seed default data into the database."""
    from sqlalchemy import select

    # Check if default branch exists
    stmt = select(Branch).where(Branch.name == "Главное отделение")
    result = await session.execute(stmt)
    if not result.scalar():
        default_branch = Branch(
            name="Главное отделение",
            description="Основное отделение",
            is_active=True,
        )
        session.add(default_branch)
        await session.commit()
        logger.info("Default branch created")

    logger.info("Database seeding completed")
