"""The daily evaluation form.

Design goals from the spec: no typing in the common case, and the next coach
opens automatically after each save so a branch of 50 can be cleared in a few
minutes.

State holds primitives only (ints, ISO date strings) - never ORM instances.
"""

from datetime import date, time

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import User
from app.domain.models.daily_report import AttendanceStatus, UniformStatus
from app.infrastructure.services import CoachService, DailyReportService
from app.presentation.telegram.callbacks import (
    AttendanceCB,
    BranchCB,
    CoachCB,
    ReportFieldCB,
    TimeCB,
    UniformCB,
)
from app.presentation.telegram.filters import IsAdmin
from app.presentation.telegram.handlers.common import (
    ack,
    parse_minutes_input,
    parse_time_input,
    respond,
)
from app.presentation.telegram.handlers.screens import (
    show_branch_coaches,
    show_main_menu,
)
from app.presentation.telegram.keyboards import (
    attendance_keyboard,
    confirm_keyboard,
    minutes_keyboard,
    notes_keyboard,
    only_home,
    time_keyboard,
    uniform_keyboard,
)
from app.presentation.telegram.utils import ReportForm, esc, format_report

logger = get_logger()

router = Router(name="report-flow")
# Filling in reports is the administrator's job. Managers reach reports
# read-only through their own screens.
router.callback_query.filter(IsAdmin())
router.message.filter(IsAdmin())

ATTENDANCE_MAP = {
    "present": AttendanceStatus.PRESENT,
    "sick": AttendanceStatus.SICK_LEAVE,
    "vacation": AttendanceStatus.VACATION,
    "absent": AttendanceStatus.UNEXCUSED_ABSENCE,
}

UNIFORM_MAP = {
    "yes": UniformStatus.YES,
    "no": UniformStatus.NO,
    "nodata": UniformStatus.NO_DATA,
}

# Statuses that make working hours meaningless - the form skips those steps.
SKIP_HOURS_FOR = {
    AttendanceStatus.SICK_LEAVE,
    AttendanceStatus.VACATION,
    AttendanceStatus.UNEXCUSED_ABSENCE,
}


def _progress(step: int, total: int = 7) -> str:
    filled = "●" * step + "○" * (total - step)
    return f"<code>{filled}</code>  шаг {step}/{total}"


async def _open_coach(
    event: CallbackQuery | Message,
    session: AsyncSession,
    state: FSMContext,
    coach_id: int,
) -> None:
    """Start the form for one coach."""
    coach = await CoachService(session).get_coach(coach_id)
    if coach is None:
        await respond(event, "❌ Тренер не найден.", only_home())
        return

    day = date.today()
    await DailyReportService(session).get_or_create(coach, day)

    await state.update_data(
        coach_id=coach.id,
        branch_id=coach.branch_id,
        report_date=day.isoformat(),
        # Clear any values carried over from the previous coach.
        attendance=None,
        upper_uniform=None,
        lower_uniform=None,
        start_time=None,
        end_time=None,
        late_minutes=0,
        early_minutes=0,
        notes=None,
    )
    await state.set_state(ReportForm.attendance)

    await respond(
        event,
        f"👤 <b>{esc(coach.full_name)}</b>\n"
        f"🏢 {esc(coach.branch.name) if coach.branch else '—'}\n"
        f"📅 {day.strftime('%d.%m.%Y')}\n\n"
        f"{_progress(1)}\n\n<b>Присутствие на работе?</b>",
        attendance_keyboard(),
    )


# ------------------------------------------------------------- entry points


@router.callback_query(BranchCB.filter(F.action == "pick"))
async def pick_branch(
    callback: CallbackQuery,
    callback_data: BranchCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Branch chosen - open the first coach who still needs a report."""
    await ack(callback)
    branch_id = callback_data.branch_id

    coaches = await CoachService(session).list_by_branch(branch_id)
    if not coaches:
        await show_branch_coaches(callback, session, branch_id, state)
        return

    reports = await DailyReportService(session).branch_reports(branch_id, date.today())
    done = {r.coach_id for r in reports if r.is_completed}
    pending = [c for c in coaches if c.id not in done]

    await state.update_data(branch_id=branch_id)

    if not pending:
        await show_branch_coaches(callback, session, branch_id, state)
        return

    # Jump straight into the first outstanding coach rather than making the
    # operator pick from a list they will work through in order anyway.
    await _open_coach(callback, session, state, pending[0].id)


@router.callback_query(CoachCB.filter(F.action == "fill"))
async def pick_coach(
    callback: CallbackQuery,
    callback_data: CoachCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await ack(callback)
    await _open_coach(callback, session, state, callback_data.coach_id)


# ------------------------------------------------------------------- fields


@router.callback_query(AttendanceCB.filter(), ReportForm.attendance)
async def set_attendance(
    callback: CallbackQuery, callback_data: AttendanceCB, state: FSMContext
) -> None:
    await ack(callback)
    attendance = ATTENDANCE_MAP.get(callback_data.value)
    if attendance is None:
        return

    await state.update_data(attendance=attendance.value)
    await state.set_state(ReportForm.upper_uniform)
    await respond(
        callback,
        f"{_progress(2)}\n\n<b>Верхняя форма надета?</b>",
        uniform_keyboard("upper"),
    )


@router.callback_query(UniformCB.filter(F.slot == "upper"), ReportForm.upper_uniform)
async def set_upper_uniform(
    callback: CallbackQuery, callback_data: UniformCB, state: FSMContext
) -> None:
    await ack(callback)
    await state.update_data(upper_uniform=UNIFORM_MAP[callback_data.value].value)
    await state.set_state(ReportForm.lower_uniform)
    await respond(
        callback,
        f"{_progress(3)}\n\n<b>Нижняя форма надета?</b>",
        uniform_keyboard("lower"),
    )


@router.callback_query(UniformCB.filter(F.slot == "lower"), ReportForm.lower_uniform)
async def set_lower_uniform(
    callback: CallbackQuery,
    callback_data: UniformCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await ack(callback)
    await state.update_data(lower_uniform=UNIFORM_MAP[callback_data.value].value)

    data = await state.get_data()
    attendance = AttendanceStatus(data["attendance"])

    if attendance in SKIP_HOURS_FOR:
        # An absent coach has no shift to record - skip to the summary.
        await _show_summary(callback, session, state)
        return

    await state.set_state(ReportForm.start_time)
    await respond(
        callback,
        f"{_progress(4)}\n\n<b>Время начала работы</b>",
        time_keyboard("start"),
    )


@router.callback_query(TimeCB.filter(F.slot == "start"), ReportForm.start_time)
async def set_start_time(
    callback: CallbackQuery, callback_data: TimeCB, state: FSMContext
) -> None:
    await ack(callback)
    if callback_data.hour < 0:
        await state.set_state(ReportForm.start_time_input)
        await respond(
            callback, "⌨️ Введите время начала в формате <code>ЧЧ:ММ</code>, например 09:30"
        )
        return

    await state.update_data(start_time=f"{callback_data.hour:02d}:{callback_data.minute:02d}")
    await state.set_state(ReportForm.end_time)
    await respond(
        callback,
        f"{_progress(5)}\n\n<b>Время окончания работы</b>",
        time_keyboard("end"),
    )


@router.message(ReportForm.start_time_input)
async def input_start_time(message: Message, state: FSMContext) -> None:
    parsed = parse_time_input(message.text or "")
    if parsed is None:
        await respond(message, "❌ Не удалось разобрать время. Пример: <code>09:30</code>")
        return
    hour, minute = parsed
    await state.update_data(start_time=f"{hour:02d}:{minute:02d}")
    await state.set_state(ReportForm.end_time)
    await respond(
        message,
        f"{_progress(5)}\n\n<b>Время окончания работы</b>",
        time_keyboard("end"),
    )


@router.callback_query(TimeCB.filter(F.slot == "end"), ReportForm.end_time)
async def set_end_time(
    callback: CallbackQuery, callback_data: TimeCB, state: FSMContext
) -> None:
    await ack(callback)
    if callback_data.hour < 0:
        await state.set_state(ReportForm.end_time_input)
        await respond(
            callback, "⌨️ Введите время окончания в формате <code>ЧЧ:ММ</code>, например 18:00"
        )
        return

    await state.update_data(end_time=f"{callback_data.hour:02d}:{callback_data.minute:02d}")
    await state.set_state(ReportForm.late_minutes)
    await respond(
        callback,
        f"{_progress(6)}\n\n<b>Опоздание</b>",
        minutes_keyboard("late"),
    )


@router.message(ReportForm.end_time_input)
async def input_end_time(message: Message, state: FSMContext) -> None:
    parsed = parse_time_input(message.text or "")
    if parsed is None:
        await respond(message, "❌ Не удалось разобрать время. Пример: <code>18:00</code>")
        return
    hour, minute = parsed
    await state.update_data(end_time=f"{hour:02d}:{minute:02d}")
    await state.set_state(ReportForm.late_minutes)
    await respond(
        message, f"{_progress(6)}\n\n<b>Опоздание</b>", minutes_keyboard("late")
    )


@router.callback_query(ReportFieldCB.filter(F.field == "late"), ReportForm.late_minutes)
async def set_late_minutes(
    callback: CallbackQuery, callback_data: ReportFieldCB, state: FSMContext
) -> None:
    await ack(callback)
    if callback_data.value < 0:
        await state.set_state(ReportForm.late_minutes_input)
        await respond(callback, "⌨️ Введите количество минут опоздания числом.")
        return

    await state.update_data(late_minutes=callback_data.value)
    await state.set_state(ReportForm.early_minutes)
    await respond(
        callback, f"{_progress(7)}\n\n<b>Ранний уход</b>", minutes_keyboard("early")
    )


@router.message(ReportForm.late_minutes_input)
async def input_late_minutes(message: Message, state: FSMContext) -> None:
    value = parse_minutes_input(message.text or "")
    if value is None:
        await respond(message, "❌ Введите целое число минут, например <code>15</code>")
        return
    await state.update_data(late_minutes=value)
    await state.set_state(ReportForm.early_minutes)
    await respond(
        message, f"{_progress(7)}\n\n<b>Ранний уход</b>", minutes_keyboard("early")
    )


@router.callback_query(
    ReportFieldCB.filter(F.field == "early"), ReportForm.early_minutes
)
async def set_early_minutes(
    callback: CallbackQuery,
    callback_data: ReportFieldCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await ack(callback)
    if callback_data.value < 0:
        await state.set_state(ReportForm.early_minutes_input)
        await respond(callback, "⌨️ Введите количество минут раннего ухода числом.")
        return

    await state.update_data(early_minutes=callback_data.value)
    await _ask_notes(callback, state)


@router.message(ReportForm.early_minutes_input)
async def input_early_minutes(message: Message, state: FSMContext) -> None:
    value = parse_minutes_input(message.text or "")
    if value is None:
        await respond(message, "❌ Введите целое число минут, например <code>10</code>")
        return
    await state.update_data(early_minutes=value)
    await _ask_notes(message, state)


async def _ask_notes(event: CallbackQuery | Message, state: FSMContext) -> None:
    await state.set_state(ReportForm.notes)
    await respond(
        event,
        "📝 <b>Примечания</b>\n\nОтправьте текст или нажмите «Без примечаний».",
        notes_keyboard(),
    )


@router.callback_query(ReportFieldCB.filter(F.field == "notes"), ReportForm.notes)
async def skip_notes(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    await ack(callback)
    await state.update_data(notes=None)
    await _show_summary(callback, session, state)


@router.message(ReportForm.notes)
async def input_notes(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    text = (message.text or "").strip()
    await state.update_data(notes=text[:1000] or None)
    await _show_summary(message, session, state)


# ------------------------------------------------------------------ summary


async def _show_summary(
    event: CallbackQuery | Message, session: AsyncSession, state: FSMContext
) -> None:
    """Preview the record before it is written."""
    data = await state.get_data()
    coach = await CoachService(session).get_coach(data["coach_id"])
    if coach is None:
        await respond(event, "❌ Тренер не найден.", only_home())
        await state.clear()
        return

    from app.infrastructure.services import calculate_worked_hours

    attendance = AttendanceStatus(data["attendance"])
    start = _parse_state_time(data.get("start_time"))
    end = _parse_state_time(data.get("end_time"))
    hours = 0.0 if attendance in SKIP_HOURS_FOR else calculate_worked_hours(start, end)

    from app.presentation.telegram.utils import ATTENDANCE_RU, UNIFORM_RU

    lines = [
        "🔍 <b>Проверьте отчёт</b>",
        "",
        f"👤 {esc(coach.full_name)}",
        f"📅 {date.fromisoformat(data['report_date']).strftime('%d.%m.%Y')}",
        "",
        f"Присутствие: {ATTENDANCE_RU[attendance]}",
        f"Верхняя форма: {UNIFORM_RU[UniformStatus(data['upper_uniform'])]}",
        f"Нижняя форма: {UNIFORM_RU[UniformStatus(data['lower_uniform'])]}",
    ]
    if attendance not in SKIP_HOURS_FOR:
        lines += [
            "",
            f"Начало: {start.strftime('%H:%M') if start else '—'}",
            f"Окончание: {end.strftime('%H:%M') if end else '—'}",
            f"Отработано часов: <b>{hours}</b>",
            f"Опоздание: {data.get('late_minutes', 0)} мин",
            f"Ранний уход: {data.get('early_minutes', 0)} мин",
        ]
    if data.get("notes"):
        lines += ["", f"📝 {esc(data['notes'])}"]

    await state.set_state(ReportForm.confirming)
    await respond(event, "\n".join(lines), confirm_keyboard())


def _parse_state_time(value: str | None) -> time | None:
    if not value:
        return None
    hour, _, minute = value.partition(":")
    return time(hour=int(hour), minute=int(minute))


@router.callback_query(ReportFieldCB.filter(F.field == "restart"), ReportForm.confirming)
async def restart_form(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    await ack(callback)
    data = await state.get_data()
    await _open_coach(callback, session, state, data["coach_id"])


@router.callback_query(ReportFieldCB.filter(F.field == "save"), ReportForm.confirming)
async def save_and_advance(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    state: FSMContext,
) -> None:
    """Persist the report, then open the next unfilled coach automatically."""
    await ack(callback)
    data = await state.get_data()

    coach_service = CoachService(session)
    report_service = DailyReportService(session)

    coach = await coach_service.get_coach(data["coach_id"])
    if coach is None:
        await respond(callback, "❌ Тренер не найден.", only_home())
        await state.clear()
        return

    report_date = date.fromisoformat(data["report_date"])
    await report_service.save_report(
        coach=coach,
        report_date=report_date,
        attendance=AttendanceStatus(data["attendance"]),
        upper_uniform=UniformStatus(data["upper_uniform"]),
        lower_uniform=UniformStatus(data["lower_uniform"]),
        start_time=_parse_state_time(data.get("start_time")),
        end_time=_parse_state_time(data.get("end_time")),
        late_arrival_minutes=data.get("late_minutes", 0),
        early_departure_minutes=data.get("early_minutes", 0),
        notes=data.get("notes"),
        actor_id=user.id,
    )

    branch_id = data["branch_id"]
    coaches = await coach_service.list_by_branch(branch_id)
    reports = await report_service.branch_reports(branch_id, report_date)
    done = {r.coach_id for r in reports if r.is_completed}
    pending = [c for c in coaches if c.id not in done]

    if not pending:
        await state.clear()
        await respond(
            callback,
            f"✅ <b>Готово!</b>\n\nВсе отчёты по отделению за "
            f"{report_date.strftime('%d.%m.%Y')} заполнены "
            f"({len(coaches)} из {len(coaches)}).",
            only_home(),
        )
        return

    remaining = len(pending)
    await respond(
        callback,
        f"✅ Сохранено: {esc(coach.full_name)}\n\nОсталось: <b>{remaining}</b>",
    )
    await _open_coach(callback, session, state, pending[0].id)
