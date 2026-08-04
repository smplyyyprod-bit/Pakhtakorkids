from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.models import Branch


async def get_branches_keyboard(branches: list[Branch]) -> InlineKeyboardMarkup:
    """Get keyboard with branches."""
    buttons = []

    for branch in branches:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🏢 {branch.name}",
                    callback_data=f"branch_{branch.id}",
                )
            ]
        )

    buttons.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_branches_pagination_keyboard(
    branches: list[Branch],
    page: int = 0,
    per_page: int = 5,
) -> InlineKeyboardMarkup:
    """Get keyboard with paginated branches."""
    start = page * per_page
    end = start + per_page

    buttons = []

    for branch in branches[start:end]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🏢 {branch.name}",
                    callback_data=f"branch_{branch.id}",
                )
            ]
        )

    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"branches_page_{page-1}")
        )
    if end < len(branches):
        nav_buttons.append(
            InlineKeyboardButton(text="➡️ Вперед", callback_data=f"branches_page_{page+1}")
        )

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append(
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="home")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
