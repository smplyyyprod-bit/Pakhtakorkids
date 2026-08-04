"""Pickers for branches, coaches, months and report fields."""

from datetime import date
from typing import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.domain.models import Branch, Coach, DailyReport
from app.presentation.telegram.callbacks import (
    AttendanceCB,
    BranchCB,
    CoachCB,
    ExportCB,
    MonthCB,
    NavCB,
    ReportFieldCB,
    TimeCB,
    UniformCB,
)
from app.presentation.telegram.keyboards.common import (
    PAGE_SIZE,
    builder_with_nav,
    pagination_row,
    paginate,
)

MONTHS_RU = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]


def branches_keyboard(
    branches: Sequence[Branch], action: str = "pick", page: int = 0
) -> InlineKeyboardMarkup:
    items = list(branches)
    builder = InlineKeyboardBuilder()
    for branch in paginate(items, page):
        builder.button(
            text=f"🏢 {branch.name}",
            callback_data=BranchCB(action=action, branch_id=branch.id),
        )
    builder.adjust(1)

    markup = builder.as_markup()
    nav = pagination_row("branches", page, len(items))
    if nav:
        markup.inline_keyboard.append(nav)
    from app.presentation.telegram.keyboards.common import nav_row

    markup.inline_keyboard.append(nav_row())
    return markup


def coaches_keyboard(
    coaches: Sequence[Coach],
    action: str = "fill",
    page: int = 0,
    branch_id: int = 0,
    completed_ids: set[int] | None = None,
) -> InlineKeyboardMarkup:
    """Coach list. A ✅/⬜️ prefix shows at a glance who still needs filling in."""
    items = list(coaches)
    completed_ids = completed_ids or set()

    builder = InlineKeyboardBuilder()
    for coach in paginate(items, page):
        mark = "✅" if coach.id in completed_ids else "⬜️"
        builder.button(
            text=f"{mark} {coach.full_name}",
            callback_data=CoachCB(action=action, coach_id=coach.id),
        )
    builder.adjust(1)

    markup = builder.as_markup()
    nav = pagination_row("coaches", page, len(items), ref_id=branch_id)
    if nav:
        markup.inline_keyboard.append(nav)
    from app.presentation.telegram.keyboards.common import nav_row

    markup.inline_keyboard.append(nav_row())
    return markup


def months_keyboard(
    action: str, ref_id: int = 0, months_back: int = 12
) -> InlineKeyboardMarkup:
    """Recent months, newest first."""
    today = date.today()
    builder = InlineKeyboardBuilder()

    year, month = today.year, today.month
    for _ in range(months_back):
        builder.button(
            text=f"{MONTHS_RU[month - 1]} {year}",
            callback_data=MonthCB(action=action, year=year, month=month, ref_id=ref_id),
        )
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    builder.adjust(2)
    return builder_with_nav(builder)


def attendance_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, value in [
        ("✅ Присутствует", "present"),
        ("🏥 Больничный", "sick"),
        ("🏖 Отпуск", "vacation"),
        ("❌ Неуважительная причина", "absent"),
    ]:
        builder.button(text=text, callback_data=AttendanceCB(value=value))
    builder.adjust(1)
    return builder_with_nav(builder)


def uniform_keyboard(slot: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, value in [("✅ Да", "yes"), ("❌ Нет", "no"), ("❔ Нет данных", "nodata")]:
        builder.button(text=text, callback_data=UniformCB(slot=slot, value=value))
    builder.adjust(3)
    return builder_with_nav(builder)


# Presets chosen to cover a normal training-day shift in one tap.
_START_PRESETS = [(7, 0), (8, 0), (9, 0), (10, 0), (12, 0), (14, 0)]
_END_PRESETS = [(14, 0), (16, 0), (17, 0), (18, 0), (19, 0), (20, 0), (21, 0), (22, 0)]


def time_keyboard(slot: str) -> InlineKeyboardMarkup:
    presets = _START_PRESETS if slot == "start" else _END_PRESETS
    builder = InlineKeyboardBuilder()
    for hour, minute in presets:
        builder.button(
            text=f"{hour:02d}:{minute:02d}",
            callback_data=TimeCB(slot=slot, hour=hour, minute=minute),
        )
    builder.adjust(4)
    # hour=-1 is the sentinel meaning "let me type an exact time".
    builder.row(
        InlineKeyboardButton(
            text="⌨️ Другое время",
            callback_data=TimeCB(slot=slot, hour=-1, minute=-1).pack(),
        )
    )
    return builder_with_nav(builder)


def minutes_keyboard(field: str) -> InlineKeyboardMarkup:
    """Common minute values, so the usual case needs no typing."""
    builder = InlineKeyboardBuilder()
    for value in (0, 5, 10, 15, 20, 30, 45, 60):
        label = "Нет" if value == 0 else f"{value} мин"
        builder.button(text=label, callback_data=ReportFieldCB(field=field, value=value))
    builder.adjust(4)
    # value=-1 is the sentinel meaning "let me type an exact number".
    builder.row(
        InlineKeyboardButton(
            text="⌨️ Другое значение",
            callback_data=ReportFieldCB(field=field, value=-1).pack(),
        )
    )
    return builder_with_nav(builder)


def notes_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⏭ Без примечаний", callback_data=ReportFieldCB(field="notes", value=0)
    )
    builder.adjust(1)
    return builder_with_nav(builder)


def confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💾 Сохранить и перейти к следующему",
        callback_data=ReportFieldCB(field="save", value=1),
    )
    builder.button(
        text="🔄 Заполнить заново", callback_data=ReportFieldCB(field="restart", value=0)
    )
    builder.adjust(1)
    return builder_with_nav(builder)


def export_keyboard(coach_id: int, year: int, month: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📊 Excel (.xlsx)",
        callback_data=ExportCB(fmt="xlsx", coach_id=coach_id, year=year, month=month),
    )
    builder.button(
        text="📄 PDF",
        callback_data=ExportCB(fmt="pdf", coach_id=coach_id, year=year, month=month),
    )
    builder.adjust(2)
    return builder_with_nav(builder)


def report_actions_keyboard(report: DailyReport) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✏️ Заполнить заново",
        callback_data=CoachCB(action="fill", coach_id=report.coach_id),
    )
    builder.adjust(1)
    return builder_with_nav(builder)
