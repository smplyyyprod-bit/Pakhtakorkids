from app.presentation.telegram.keyboards.main_keyboards import (
    get_main_admin_keyboard,
    get_main_manager_keyboard,
)
from app.presentation.telegram.keyboards.branch_keyboards import (
    get_branches_keyboard,
)
from app.presentation.telegram.keyboards.coach_keyboards import (
    get_coaches_keyboard,
)
from app.presentation.telegram.keyboards.report_keyboards import (
    get_attendance_keyboard,
    get_uniform_keyboard,
    get_yes_no_keyboard,
    get_report_confirmation_keyboard,
)

__all__ = [
    "get_main_admin_keyboard",
    "get_main_manager_keyboard",
    "get_branches_keyboard",
    "get_coaches_keyboard",
    "get_attendance_keyboard",
    "get_uniform_keyboard",
    "get_yes_no_keyboard",
    "get_report_confirmation_keyboard",
]
