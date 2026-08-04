"""User queries."""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Role, User
from app.infrastructure.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_role(self, role: Role, active_only: bool = True) -> Sequence[User]:
        stmt = select(User).where(User.role == role)
        if active_only:
            stmt = stmt.where(User.is_active.is_(True))
        stmt = stmt.order_by(User.full_name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_branch(self, branch_id: int) -> Sequence[User]:
        stmt = (
            select(User)
            .where(User.branch_id == branch_id, User.is_active.is_(True))
            .order_by(User.full_name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
