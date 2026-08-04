"""Coach queries."""

from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Coach
from app.infrastructure.repositories.base import BaseRepository


class CoachRepository(BaseRepository[Coach]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Coach)

    async def get_with_branch(self, coach_id: int) -> Coach | None:
        """Load a coach with its branch, so `coach.branch.name` is safe to read."""
        stmt = (
            select(Coach)
            .where(Coach.id == coach_id)
            .options(selectinload(Coach.branch))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_unique_id(self, unique_id: str) -> Coach | None:
        stmt = select(Coach).where(Coach.unique_id == unique_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_branch(
        self, branch_id: int, active_only: bool = True
    ) -> Sequence[Coach]:
        conditions = [Coach.branch_id == branch_id]
        if active_only:
            conditions.append(Coach.is_active.is_(True))
        stmt = select(Coach).where(*conditions).order_by(Coach.full_name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_all(
        self, active_only: bool = True, with_branch: bool = False
    ) -> Sequence[Coach]:
        stmt = select(Coach)
        if active_only:
            stmt = stmt.where(Coach.is_active.is_(True))
        if with_branch:
            stmt = stmt.options(selectinload(Coach.branch))
        stmt = stmt.order_by(Coach.full_name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_active(self, branch_id: int | None = None) -> int:
        stmt = select(func.count()).select_from(Coach).where(Coach.is_active.is_(True))
        if branch_id is not None:
            stmt = stmt.where(Coach.branch_id == branch_id)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())
