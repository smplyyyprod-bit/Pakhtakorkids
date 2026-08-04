"""Branch queries."""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Branch
from app.infrastructure.repositories.base import BaseRepository


class BranchRepository(BaseRepository[Branch]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Branch)

    async def get_by_name(self, name: str) -> Branch | None:
        stmt = select(Branch).where(Branch.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_active(self) -> Sequence[Branch]:
        stmt = (
            select(Branch).where(Branch.is_active.is_(True)).order_by(Branch.name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_with_coaches(self, branch_id: int) -> Branch | None:
        stmt = (
            select(Branch)
            .where(Branch.id == branch_id)
            .options(selectinload(Branch.coaches))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
