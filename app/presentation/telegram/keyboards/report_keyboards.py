from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_attendance_keyboard() -> InlineKeyboardMarkup:
    """Get attendance status keyboard."""
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Присутствует",
                callback_data="attendance_present",
            )
        ],
        [
            InlineKeyboardButton(
                text="🏥 Больничный",
                callback_data="attendance_sick",
            )
        ],
        [
            InlineKeyboardButton(
                text="🏖️ Отпуск",
                callback_data="attendance_vacation",
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Неуважительная причина",
                callback_data="attendance_absent",
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="back_to_report",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_uniform_keyboard() -> InlineKeyboardMarkup:
    """Get uniform status keyboard."""
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Да",
                callback_data="uniform_yes",
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Нет",
                callback_data="uniform_no",
            )
        ],
        [
            InlineKeyboardButton(
                text="❓ Нет данных",
                callback_data="uniform_no_data",
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="back_to_report",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_yes_no_keyboard() -> InlineKeyboardMarkup:
    """Get yes/no keyboard."""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data="yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="no"),
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_report_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Get report confirmation keyboard."""
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Сохранить отчет",
                callback_data="save_report",
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Редактировать",
                callback_data="edit_report",
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="cancel_report",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quick_time_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard with quick time options."""
    buttons = [
        [
            InlineKeyboardButton(text="08:00", callback_data="time_0800"),
            InlineKeyboardButton(text="09:00", callback_data="time_0900"),
        ],
        [
            InlineKeyboardButton(text="10:00", callback_data="time_1000"),
            InlineKeyboardButton(text="11:00", callback_data="time_1100"),
        ],
        [
            InlineKeyboardButton(text="17:00", callback_data="time_1700"),
            InlineKeyboardButton(text="18:00", callback_data="time_1800"),
        ],
        [
            InlineKeyboardButton(text="19:00", callback_data="time_1900"),
            InlineKeyboardButton(text="20:00", callback_data="time_2000"),
        ],
        [
            InlineKeyboardButton(text="✏️ Ввести время", callback_data="input_time"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_report"),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)
