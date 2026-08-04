"""Shared keyboard pieces."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.presentation.telegram.callbacks import NavCB, PageCB

PAGE_SIZE = 8


def home_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="🏠 Главное меню", callback_data=NavCB(target="home").pack()
    )


def back_button(target: str = "back") -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="⬅️ Назад", callback_data=NavCB(target=target).pack()
    )


def cancel_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="✖️ Отмена", callback_data=NavCB(target="cancel").pack()
    )


def nav_row(*, back: bool = True, home: bool = True) -> list[InlineKeyboardButton]:
    row: list[InlineKeyboardButton] = []
    if back:
        row.append(back_button())
    if home:
        row.append(home_button())
    return row


def only_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[home_button()]])


def pagination_row(
    scope: str, page: int, total: int, ref_id: int = 0, page_size: int = PAGE_SIZE
) -> list[InlineKeyboardButton]:
    """Prev / position / next controls, omitted entirely for a single page."""
    last_page = max((total - 1) // page_size, 0)
    if last_page == 0:
        return []

    row: list[InlineKeyboardButton] = []
    if page > 0:
        row.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=PageCB(scope=scope, page=page - 1, ref_id=ref_id).pack(),
            )
        )
    row.append(
        InlineKeyboardButton(
            text=f"{page + 1}/{last_page + 1}",
            callback_data=NavCB(target="noop").pack(),
        )
    )
    if page < last_page:
        row.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=PageCB(scope=scope, page=page + 1, ref_id=ref_id).pack(),
            )
        )
    return row


def paginate(items: list, page: int, page_size: int = PAGE_SIZE) -> list:
    """Return the slice for a page, clamping out-of-range pages."""
    if not items:
        return []
    last_page = max((len(items) - 1) // page_size, 0)
    page = max(0, min(page, last_page))
    start = page * page_size
    return items[start : start + page_size]


def builder_with_nav(
    builder: InlineKeyboardBuilder, *, back: bool = True, home: bool = True
) -> InlineKeyboardMarkup:
    markup = builder.as_markup()
    row = nav_row(back=back, home=home)
    if row:
        markup.inline_keyboard.append(row)
    return markup
