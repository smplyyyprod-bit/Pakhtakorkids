"""Role-specific main menus."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.models import Role, User
from app.presentation.telegram.callbacks import AdminActionCB, NavCB


def _btn(text: str, action: str, ref_id: int = 0) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text, callback_data=AdminActionCB(action=action, ref_id=ref_id).pack()
    )


def admin_menu() -> InlineKeyboardMarkup:
    """Administrator menu - reports only, no company analytics."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("🏢 Отделения", "branches")],
            [_btn("📋 Отчёты за сегодня", "today")],
            [_btn("✏️ Редактировать отчёт", "edit")],
            [_btn("❓ Справка", "help")],
        ]
    )


def manager_menu() -> InlineKeyboardMarkup:
    """Manager menu - the full analytics and administration surface."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("👥 Тренеры", "coaches")],
            [_btn("📊 Месячная статистика", "monthly")],
            [_btn("📈 Панель управления", "dashboard")],
            [_btn("🔍 Аналитика и рейтинги", "analytics")],
            [_btn("📥 Экспорт отчётов", "export")],
            [_btn("⚙️ Администрирование", "admin")],
            [_btn("❓ Справка", "help")],
        ]
    )


def menu_for(user: User) -> InlineKeyboardMarkup | None:
    if user.role is Role.ADMIN:
        return admin_menu()
    if user.role is Role.MANAGER:
        return manager_menu()
    return None


def menu_title(user: User) -> str:
    if user.role is Role.ADMIN:
        return "🏠 <b>Главное меню</b>\n\nРежим: администратор"
    if user.role is Role.MANAGER:
        return "🏠 <b>Главное меню</b>\n\nРежим: руководитель"
    return "🏠 <b>Главное меню</b>"
