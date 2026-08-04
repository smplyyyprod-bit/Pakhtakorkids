"""User and access management."""

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import Role, User
from app.infrastructure.repositories import UserRepository
from app.infrastructure.services.audit_service import AuditService

logger = get_logger()


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = UserRepository(session)
        self.audit = AuditService(session)

    async def get_user(self, telegram_id: int) -> User | None:
        return await self.repository.get_by_telegram_id(telegram_id)

    async def grant_access(
        self,
        *,
        telegram_id: int,
        full_name: str,
        role: Role,
        branch_id: int | None = None,
        actor_id: int | None = None,
    ) -> User:
        """Create or update a user with an explicit role.

        Access is granted deliberately - there is no path that turns an unknown
        Telegram ID into a privileged account by simply messaging the bot.
        """
        user = await self.repository.get_by_telegram_id(telegram_id)
        if user is None:
            user = User(
                telegram_id=telegram_id,
                full_name=full_name,
                role=role,
                branch_id=branch_id,
                is_active=True,
            )
            await self.repository.add(user)
            action = "user.created"
        else:
            user.full_name = full_name or user.full_name
            user.role = role
            user.branch_id = branch_id
            user.is_active = True
            action = "user.updated"

        await self.audit.record(
            action=action,
            entity_type="user",
            entity_id=user.id,
            user_id=actor_id,
            changes={"telegram_id": telegram_id, "role": role.value},
        )
        await self.session.commit()
        return user

    async def set_active(
        self, user_id: int, active: bool, actor_id: int | None = None
    ) -> User | None:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            return None
        user.is_active = active
        await self.audit.record(
            action="user.activated" if active else "user.deactivated",
            entity_type="user",
            entity_id=user.id,
            user_id=actor_id,
        )
        await self.session.commit()
        return user

    async def list_admins(self) -> Sequence[User]:
        return await self.repository.list_by_role(Role.ADMIN)

    async def list_managers(self) -> Sequence[User]:
        return await self.repository.list_by_role(Role.MANAGER)
