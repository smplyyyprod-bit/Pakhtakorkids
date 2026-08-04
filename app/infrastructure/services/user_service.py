from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import User, Role
from app.infrastructure.repositories import UserRepository

logger = get_logger()


class UserService:
    """Service for user operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserRepository(session)

    async def get_or_create_user(
        self,
        telegram_id: int,
        full_name: str,
        role: Role = Role.COACH,
    ) -> User:
        """Get existing user or create a new one."""
        user = await self.repository.get_by_telegram_id(telegram_id)

        if user:
            logger.info(f"User found: {telegram_id}")
            return user

        logger.info(f"Creating new user: {telegram_id} {full_name}")
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            role=role,
            is_active=True,
        )
        return await self.repository.create(user)

    async def get_user(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        return await self.repository.get_by_telegram_id(telegram_id)

    async def get_admin_users(self) -> list[User]:
        """Get all admin users."""
        return await self.repository.get_admins()

    async def get_manager_users(self) -> list[User]:
        """Get all manager users."""
        return await self.repository.get_managers()

    async def get_branch_users(self, branch_id: int) -> list[User]:
        """Get users assigned to a branch."""
        return await self.repository.get_by_branch(branch_id)

    async def update_user_branch(self, user_id: int, branch_id: int) -> Optional[User]:
        """Update user's branch."""
        user = await self.repository.get_by_id(user_id)
        if user:
            user.branch_id = branch_id
            return await self.repository.update(user)
        return None

    async def deactivate_user(self, user_id: int) -> Optional[User]:
        """Deactivate a user."""
        user = await self.repository.get_by_id(user_id)
        if user:
            user.is_active = False
            return await self.repository.update(user)
        return None

    async def activate_user(self, user_id: int) -> Optional[User]:
        """Activate a user."""
        user = await self.repository.get_by_id(user_id)
        if user:
            user.is_active = True
            return await self.repository.update(user)
        return None
