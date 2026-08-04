from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import User, Role
from app.infrastructure.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_role(self, role: Role) -> list[User]:
        """Get users by role."""
        stmt = select(User).where(User.role == role).order_by(User.full_name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_branch(self, branch_id: int) -> list[User]:
        """Get users in a branch."""
        stmt = select(User).where(User.branch_id == branch_id).order_by(User.full_name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_users(self) -> list[User]:
        """Get active users."""
        stmt = select(User).where(User.is_active == True).order_by(User.full_name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_admins(self) -> list[User]:
        """Get all admins."""
        return await self.get_by_role(Role.ADMIN)

    async def get_managers(self) -> list[User]:
        """Get all managers."""
        return await self.get_by_role(Role.MANAGER)
