from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_admin_keyboard() -> InlineKeyboardMarkup:
    """Get main menu keyboard for administrators."""
    buttons = [
        [
            InlineKeyboardButton(
                text="📋 Ежедневные отчеты",
                callback_data="admin_daily_reports",
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Редактировать отчет",
                callback_data="admin_edit_report",
            )
        ],
        [
            InlineKeyboardButton(
                text="📅 Предыдущие отчеты",
                callback_data="admin_previous_reports",
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Настройки",
                callback_data="admin_settings",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_manager_keyboard() -> InlineKeyboardMarkup:
    """Get main menu keyboard for managers."""
    buttons = [
        [
            InlineKeyboardButton(
                text="👥 Тренеры",
                callback_data="manager_coaches",
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Ежемесячные отчеты",
                callback_data="manager_monthly_reports",
            )
        ],
        [
            InlineKeyboardButton(
                text="📈 Панель управления",
                callback_data="manager_dashboard",
            )
        ],
        [
            InlineKeyboardButton(
                text="📥 Экспорт отчетов",
                callback_data="manager_export",
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Администрирование",
                callback_data="manager_admin_panel",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_button(callback_data: str = "back") -> InlineKeyboardMarkup:
    """Get back button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data)]
        ]
    )


def get_back_and_home_buttons(
    back_callback: str = "back", home_callback: str = "home"
) -> InlineKeyboardMarkup:
    """Get back and home buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback),
                InlineKeyboardButton(text="🏠 Главное меню", callback_data=home_callback),
            ]
        ]
    )
