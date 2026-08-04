from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Branch
from app.infrastructure.repositories.base import BaseRepository


class BranchRepository(BaseRepository[Branch]):
    """Repository for Branch model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Branch)

    async def get_by_name(self, name: str) -> Optional[Branch]:
        """Get branch by name."""
        stmt = select(Branch).where(Branch.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active_branches(self) -> list[Branch]:
        """Get active branches."""
        stmt = select(Branch).where(Branch.is_active == True).order_by(Branch.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_with_coaches(self, branch_id: int) -> Optional[Branch]:
        """Get branch with all coaches loaded."""
        stmt = (
            select(Branch)
            .where(Branch.id == branch_id)
            .options(selectinload(Branch.coaches))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_with_coaches(self) -> list[Branch]:
        """Get all branches with coaches."""
        stmt = select(Branch).options(selectinload(Branch.coaches))
        result = await self.session.execute(stmt)
        return result.scalars().all()
