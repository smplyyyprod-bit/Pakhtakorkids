"""Role filters.

The spec draws a hard line: administrators fill in reports but must never see
company-wide analytics. Expressing that as a filter means a manager-only router
simply will not match an administrator's update, so the restriction cannot be
forgotten inside a handler body.
"""

from aiogram.filters import Filter
from aiogram.types import TelegramObject

from app.domain.models import Role, User


class HasRole(Filter):
    """Passes when the authenticated user holds one of the given roles."""

    def __init__(self, *roles: Role) -> None:
        if not roles:
            raise ValueError("HasRole requires at least one role")
        self.roles = frozenset(roles)

    async def __call__(self, event: TelegramObject, user: User | None = None) -> bool:
        return user is not None and user.role in self.roles


class IsAdmin(HasRole):
    """Administrators only."""

    def __init__(self) -> None:
        super().__init__(Role.ADMIN)


class IsManager(HasRole):
    """Managers only - the analytics and administration surface."""

    def __init__(self) -> None:
        super().__init__(Role.MANAGER)
