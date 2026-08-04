from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.models import Coach


async def get_coaches_keyboard(coaches: list[Coach]) -> InlineKeyboardMarkup:
    """Get keyboard with coaches."""
    buttons = []

    for coach in coaches:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"👤 {coach.full_name}",
                    callback_data=f"coach_{coach.id}",
                )
            ]
        )

    buttons.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_coaches_pagination_keyboard(
    coaches: list[Coach],
    page: int = 0,
    per_page: int = 5,
) -> InlineKeyboardMarkup:
    """Get keyboard with paginated coaches."""
    start = page * per_page
    end = start + per_page

    buttons = []

    for coach in coaches[start:end]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"👤 {coach.full_name} ({coach.unique_id})",
                    callback_data=f"coach_{coach.id}",
                )
            ]
        )

    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"coaches_page_{page-1}")
        )
    if end < len(coaches):
        nav_buttons.append(
            InlineKeyboardButton(text="➡️ Вперед", callback_data=f"coaches_page_{page+1}")
        )

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append(
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="home")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
