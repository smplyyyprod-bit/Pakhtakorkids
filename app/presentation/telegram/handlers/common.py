"""Helpers shared by every handler."""

from datetime import date

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, TelegramObject

from app.core.logger import get_logger

logger = get_logger()

NO_ACCESS = "⛔️ Этот раздел доступен только руководителям."


async def respond(
    event: TelegramObject,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
) -> None:
    """Render a screen, editing in place for callbacks and sending for messages.

    Editing keeps the chat from filling up with a new message per tap, which
    matters when an operator walks through 50 coaches in one sitting.
    """
    if isinstance(event, CallbackQuery):
        if event.message is None:
            return
        try:
            await event.message.edit_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
        except TelegramBadRequest as exc:
            # Telegram rejects an edit that would not change anything; that is
            # a no-op, not an error worth surfacing to the user.
            if "message is not modified" in str(exc):
                return
            # The original message may be too old to edit - fall back to a new one.
            await event.message.answer(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
    elif isinstance(event, Message):
        await event.answer(text, reply_markup=keyboard, parse_mode="HTML")


async def ack(event: TelegramObject, text: str | None = None, alert: bool = False) -> None:
    """Acknowledge a callback so the client stops showing a spinner."""
    if isinstance(event, CallbackQuery):
        await event.answer(text, show_alert=alert)


def today() -> date:
    return date.today()


def parse_time_input(raw: str) -> tuple[int, int] | None:
    """Parse '9', '9:30', '09.30', '0930' into (hour, minute)."""
    text = raw.strip().replace(".", ":").replace(" ", "")
    if not text:
        return None

    if ":" in text:
        hour_part, _, minute_part = text.partition(":")
    elif len(text) == 4 and text.isdigit():
        hour_part, minute_part = text[:2], text[2:]
    else:
        hour_part, minute_part = text, "0"

    try:
        hour, minute = int(hour_part), int(minute_part)
    except ValueError:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute


def parse_minutes_input(raw: str) -> int | None:
    """Parse a non-negative minute count, rejecting absurd values."""
    try:
        value = int(raw.strip())
    except (ValueError, AttributeError):
        return None
    if value < 0 or value > 24 * 60:
        return None
    return value
