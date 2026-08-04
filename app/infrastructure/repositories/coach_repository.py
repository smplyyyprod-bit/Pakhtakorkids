from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Coach
from app.infrastructure.repositories.base import BaseRepository


class CoachRepository(BaseRepository[Coach]):
    """Repository for Coach model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Coach)

    async def get_by_unique_id(self, unique_id: str) -> Optional[Coach]:
        """Get coach by unique ID."""
        stmt = select(Coach).where(Coach.unique_id == unique_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_branch(self, branch_id: int) -> list[Coach]:
        """Get coaches in a branch."""
        stmt = (
            select(Coach)
            .where(Coach.branch_id == branch_id)
            .order_by(Coach.full_name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_coaches(self) -> list[Coach]:
        """Get all active coaches."""
        stmt = select(Coach).where(Coach.is_active == True).order_by(Coach.full_name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_by_branch(self, branch_id: int) -> list[Coach]:
        """Get active coaches in a branch."""
        stmt = (
            select(Coach)
            .where(Coach.branch_id == branch_id, Coach.is_active == True)
            .order_by(Coach.full_name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_branch(self, branch_id: int) -> int:
        """Count coaches in a branch."""
        stmt = select(Coach).where(Coach.branch_id == branch_id)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
