"""Manager screens: statistics, dashboard, analytics, comparison, exports."""

from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import User
from app.infrastructure.services import (
    CoachService,
    DailyReportService,
    ExportService,
    StatisticsService,
)
from app.presentation.telegram.callbacks import (
    AdminActionCB,
    BranchCB,
    CoachCB,
    ExportCB,
    MonthCB,
)
from app.presentation.telegram.filters import IsManager
from app.presentation.telegram.handlers.common import ack, respond
from app.presentation.telegram.handlers.screens import (
    show_analytics,
    show_branch_coaches,
    show_branches,
    show_dashboard,
    show_main_menu,
    show_month_picker,
)
from app.presentation.telegram.keyboards import (
    export_keyboard,
    months_keyboard,
    only_home,
)
from app.presentation.telegram.utils import (
    ManagerFlow,
    esc,
    format_coach_card,
    format_comparison,
    format_completion,
    format_monthly_stats,
    format_trend,
    month_name,
)

logger = get_logger()

router = Router(name="manager")
router.callback_query.filter(IsManager())
router.message.filter(IsManager())


# ------------------------------------------------------------- menu buttons


@router.callback_query(AdminActionCB.filter(F.action == "coaches"))
async def open_coaches(
    callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext
) -> None:
    await ack(callback)
    await show_branches(callback, session, user, state)


@router.callback_query(AdminActionCB.filter(F.action == "monthly"))
async def open_monthly(
    callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext
) -> None:
    await ack(callback)
    await show_branches(callback, session, user, state)


@router.callback_query(AdminActionCB.filter(F.action == "dashboard"))
async def open_dashboard(callback: CallbackQuery, session: AsyncSession) -> None:
    await ack(callback)
    await show_dashboard(callback, session)


@router.callback_query(AdminActionCB.filter(F.action == "analytics"))
async def open_analytics(callback: CallbackQuery, session: AsyncSession) -> None:
    await ack(callback)
    await show_analytics(callback, session)


@router.callback_query(AdminActionCB.filter(F.action == "export"))
async def open_export(
    callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext
) -> None:
    await ack(callback)
    await state.set_state(ManagerFlow.choosing_branch)
    await show_branches(callback, session, user, state)


@router.callback_query(AdminActionCB.filter(F.action == "trend"))
async def open_trend(callback: CallbackQuery, session: AsyncSession) -> None:
    await ack(callback)
    await show_month_picker(callback, action="trend", title="📉 Динамика за месяц")


@router.callback_query(AdminActionCB.filter(F.action == "compare"))
async def open_compare(callback: CallbackQuery) -> None:
    await ack(callback)
    await show_month_picker(callback, action="compare", title="⚖️ Сравнение тренеров")


# --------------------------------------------------------------- navigation


@router.callback_query(BranchCB.filter(F.action == "stats"))
async def branch_selected(
    callback: CallbackQuery,
    callback_data: BranchCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await ack(callback)
    await state.set_state(ManagerFlow.choosing_coach)
    await show_branch_coaches(
        callback, session, callback_data.branch_id, state, action="stats"
    )


@router.callback_query(CoachCB.filter(F.action == "stats"))
async def coach_selected(
    callback: CallbackQuery,
    callback_data: CoachCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Coach card plus a month picker for their statistics."""
    await ack(callback)
    coach = await CoachService(session).get_coach(callback_data.coach_id)
    if coach is None:
        await respond(callback, "❌ Тренер не найден.", only_home())
        return

    await state.update_data(coach_id=coach.id)
    await state.set_state(ManagerFlow.choosing_month)
    await respond(
        callback,
        format_coach_card(coach) + "\n\n📅 <b>Выберите месяц</b>",
        months_keyboard(action="stats", ref_id=coach.id),
    )


@router.callback_query(MonthCB.filter(F.action == "stats"))
async def show_coach_month(
    callback: CallbackQuery,
    callback_data: MonthCB,
    session: AsyncSession,
) -> None:
    await ack(callback)
    coach_id = callback_data.ref_id
    coach = await CoachService(session).get_coach(coach_id)
    if coach is None:
        await respond(callback, "❌ Тренер не найден.", only_home())
        return

    stats = await DailyReportService(session).monthly_stats(
        coach_id, callback_data.year, callback_data.month
    )
    text = format_monthly_stats(
        stats, coach.full_name, callback_data.year, callback_data.month
    )
    await respond(
        callback,
        text,
        export_keyboard(coach_id, callback_data.year, callback_data.month),
    )


@router.callback_query(MonthCB.filter(F.action == "compare"))
async def show_comparison(
    callback: CallbackQuery, callback_data: MonthCB, session: AsyncSession
) -> None:
    await ack(callback)
    rows = await StatisticsService(session).compare_coaches(
        callback_data.year, callback_data.month
    )
    await respond(
        callback,
        format_comparison(rows, callback_data.year, callback_data.month),
        only_home(),
    )


@router.callback_query(MonthCB.filter(F.action == "trend"))
async def show_trend(
    callback: CallbackQuery, callback_data: MonthCB, session: AsyncSession
) -> None:
    await ack(callback)
    service = StatisticsService(session)
    rows = await service.attendance_trend(callback_data.year, callback_data.month)
    completion = await service.completion(callback_data.year, callback_data.month)

    label = f"{month_name(callback_data.month)} {callback_data.year}"
    text = (
        format_trend(rows, callback_data.year, callback_data.month)
        + "\n\n"
        + format_completion(completion, label)
    )
    await respond(callback, text, only_home())


# ------------------------------------------------------------------ exports


@router.callback_query(ExportCB.filter())
async def export_report(
    callback: CallbackQuery, callback_data: ExportCB, session: AsyncSession
) -> None:
    """Generate and send an Excel or PDF report."""
    await ack(callback, "Готовлю файл…")

    coach = await CoachService(session).get_coach(callback_data.coach_id)
    if coach is None or callback.message is None:
        await respond(callback, "❌ Тренер не найден.", only_home())
        return

    service = ExportService(session)
    period = f"{callback_data.year}-{callback_data.month:02d}"
    safe_name = coach.unique_id or str(coach.id)

    try:
        if callback_data.fmt == "xlsx":
            payload = await service.export_excel(
                coach.id, callback_data.year, callback_data.month
            )
            filename = f"report_{safe_name}_{period}.xlsx"
        else:
            payload = await service.export_pdf(
                coach.id, callback_data.year, callback_data.month
            )
            filename = f"report_{safe_name}_{period}.pdf"
    except RuntimeError as exc:
        # Missing font for PDF - tell the operator what to fix.
        logger.error("Export failed: {}", exc)
        await callback.message.answer(f"❌ Не удалось сформировать файл: {exc}")
        return

    await callback.message.answer_document(
        BufferedInputFile(payload, filename=filename),
        caption=(
            f"📄 {esc(coach.full_name)} — "
            f"{month_name(callback_data.month)} {callback_data.year}"
        ),
        parse_mode="HTML",
    )
    logger.info(
        "Sent {} export for coach={} period={}",
        callback_data.fmt,
        coach.id,
        period,
    )
