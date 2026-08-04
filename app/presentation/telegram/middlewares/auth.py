"""Resolves the Telegram sender into a domain User before handlers run."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User as TgUser

from app.core.logger import get_logger
from app.infrastructure.services import UserService

logger = get_logger()

ACCESS_DENIED = (
    "⛔️ У вас нет доступа к этому боту.\n\n"
    "Обратитесь к руководителю, чтобы вас добавили в систему."
)


class AuthMiddleware(BaseMiddleware):
    """Loads the User row and injects it as `user`.

    Unknown senders are rejected here rather than in each handler, so a missing
    role check in a handler cannot leak access. Users are never auto-created
    with a privileged role - unknown Telegram IDs are simply refused.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        if tg_user is None:
            return None

        session = data["session"]
        service = UserService(session)
        user = await service.get_user(tg_user.id)

        if user is None or not user.is_active:
            logger.warning(
                "Rejected access for telegram_id={} ({})",
                tg_user.id,
                tg_user.full_name,
            )
            await self._deny(event)
            return None

        # Keep the display name fresh without requiring a profile screen.
        display_name = tg_user.full_name or user.full_name
        if display_name and display_name != user.full_name:
            user.full_name = display_name
            await session.commit()

        data["user"] = user
        return await handler(event, data)

    @staticmethod
    async def _deny(event: TelegramObject) -> None:
        if isinstance(event, CallbackQuery):
            await event.answer(ACCESS_DENIED, show_alert=True)
        elif isinstance(event, Message):
            await event.answer(ACCESS_DENIED)
