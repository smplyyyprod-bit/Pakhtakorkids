from datetime import date

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.infrastructure.database import SessionLocal
from app.infrastructure.services import (
    UserService,
    BranchService,
    CoachService,
    DailyReportService,
)
from app.presentation.telegram.keyboards import (
    get_back_and_home_buttons,
    get_main_admin_keyboard,
)
from app.presentation.telegram.keyboards.branch_keyboards import (
    get_branches_pagination_keyboard,
)
from app.presentation.telegram.keyboards.coach_keyboards import (
    get_coaches_pagination_keyboard,
)
from app.presentation.telegram.utils import ReportFormStates

logger = get_logger()
router = Router()


@router.callback_query(F.data == "admin_daily_reports")
async def handle_daily_reports(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle daily reports button for admin."""
    async with SessionLocal() as session:
        branch_service = BranchService(session)
        branches = await branch_service.get_all_branches()

        if not branches:
            await callback.message.edit_text(
                "❌ Отделения не найдены.",
                reply_markup=get_back_and_home_buttons(),
            )
        else:
            keyboard = await get_branches_pagination_keyboard(branches)
            await callback.message.edit_text(
                "📋 Выберите отделение для заполнения отчетов:",
                reply_markup=keyboard,
            )
            await state.set_state(ReportFormStates.selecting_branch)

    await callback.answer()


@router.callback_query(F.data.startswith("branch_"), ReportFormStates.selecting_branch)
async def handle_branch_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle branch selection for daily reports."""
    branch_id = int(callback.data.split("_")[1])

    async with SessionLocal() as session:
        branch_service = BranchService(session)
        coach_service = CoachService(session)

        branch = await branch_service.get_branch(branch_id)
        if not branch:
            await callback.answer("❌ Отделение не найдено.", show_alert=True)
            return

        coaches = await coach_service.get_active_branch_coaches(branch_id)

        if not coaches:
            await callback.message.edit_text(
                f"❌ В отделении '{branch.name}' не найдено тренеров.",
                reply_markup=get_back_and_home_buttons(),
            )
        else:
            keyboard = await get_coaches_pagination_keyboard(coaches)
            await callback.message.edit_text(
                f"🏢 **{branch.name}**\n\n👥 Выберите тренера для заполнения отчета:",
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

            await state.update_data(
                branch_id=branch_id,
                coaches=coaches,
                current_coach_index=0,
            )
            await state.set_state(ReportFormStates.selecting_coach)

    await callback.answer()


@router.callback_query(F.data.startswith("coach_"), ReportFormStates.selecting_coach)
async def handle_coach_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle coach selection for daily report."""
    coach_id = int(callback.data.split("_")[1])

    data = await state.get_data()
    branch_id = data.get("branch_id")

    async with SessionLocal() as session:
        coach_service = CoachService(session)
        report_service = DailyReportService(session)

        coach = await coach_service.get_coach(coach_id)
        if not coach:
            await callback.answer("❌ Тренер не найден.", show_alert=True)
            return

        today = date.today()
        report = await report_service.get_report(coach_id, today)

        if not report:
            report = await report_service.create_or_update_report(
                coach_id=coach_id,
                branch_id=branch_id,
                report_date=today,
            )

        report_text = f"""
👤 **Тренер:** {coach.full_name}
📅 **Дата:** {today.strftime('%d.%m.%Y')}
🏢 **Отделение:** {coach.branch.name}

Начинаем заполнение отчета...

**Следующий шаг:** Выберите статус присутствия
"""

        from app.presentation.telegram.keyboards.report_keyboards import (
            get_attendance_keyboard,
        )

        keyboard = get_attendance_keyboard()
        await callback.message.edit_text(
            report_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        await state.update_data(
            coach_id=coach_id,
            report_id=report.id,
            current_report=report,
        )
        await state.set_state(ReportFormStates.filling_attendance)

    await callback.answer()


@router.callback_query(F.data == "admin_edit_report")
async def handle_edit_report(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle edit report button."""
    await callback.message.edit_text(
        "🔄 Редактирование отчетов\n\nЭта функция еще в разработке.",
        reply_markup=get_back_and_home_buttons(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_previous_reports")
async def handle_previous_reports(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle previous reports button."""
    await callback.message.edit_text(
        "📅 Предыдущие отчеты\n\nЭта функция еще в разработке.",
        reply_markup=get_back_and_home_buttons(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_settings")
async def handle_admin_settings(callback: CallbackQuery) -> None:
    """Handle admin settings."""
    await callback.message.edit_text(
        "⚙️ Настройки\n\nЭта функция еще в разработке.",
        reply_markup=get_back_and_home_buttons(),
    )
    await callback.answer()
