"""Catches unhandled handler exceptions so one bad update cannot kill the bot."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.core.logger import get_logger

logger = get_logger()

GENERIC_ERROR = (
    "⚠️ Произошла ошибка. Попробуйте ещё раз или вернитесь в главное меню: /start"
)


class ErrorMiddleware(BaseMiddleware):
    """Logs the traceback and shows the user a neutral message."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception:
            logger.exception("Unhandled error while processing update")
            try:
                if isinstance(event, CallbackQuery):
                    await event.answer(GENERIC_ERROR, show_alert=True)
                elif isinstance(event, Message):
                    await event.answer(GENERIC_ERROR)
            except Exception:
                logger.exception("Failed to deliver the error notice to the user")
            return None
