from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.infrastructure.database import SessionLocal
from app.infrastructure.services import (
    BranchService,
    CoachService,
    StatisticsService,
)
from app.presentation.telegram.keyboards import get_back_and_home_buttons

logger = get_logger()
router = Router()


@router.callback_query(F.data == "manager_coaches")
async def handle_manager_coaches(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle coaches view for manager."""
    async with SessionLocal() as session:
        coach_service = CoachService(session)
        coaches = await coach_service.get_all_coaches()

        coaches_text = "👥 **Список всех тренеров:**\n\n"
        for coach in coaches:
            status = "✅" if coach.is_active else "❌"
            coaches_text += f"{status} {coach.full_name} ({coach.unique_id})\n"
            coaches_text += f"   Должность: {coach.position}\n"
            coaches_text += f"   Команда: {coach.team}\n"
            coaches_text += f"   Отделение: {coach.branch.name}\n\n"

        await callback.message.edit_text(
            coaches_text,
            reply_markup=get_back_and_home_buttons(),
            parse_mode="Markdown",
        )

    await callback.answer()


@router.callback_query(F.data == "manager_monthly_reports")
async def handle_manager_monthly_reports(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Handle monthly reports view."""
    async with SessionLocal() as session:
        branch_service = BranchService(session)
        branches = await branch_service.get_all_branches()

        if not branches:
            await callback.message.edit_text(
                "❌ Отделения не найдены.",
                reply_markup=get_back_and_home_buttons(),
            )
        else:
            from app.presentation.telegram.keyboards.branch_keyboards import (
                get_branches_pagination_keyboard,
            )

            keyboard = await get_branches_pagination_keyboard(branches)
            await callback.message.edit_text(
                "📊 Выберите отделение для просмотра отчетов:",
                reply_markup=keyboard,
            )

    await callback.answer()


@router.callback_query(F.data == "manager_dashboard")
async def handle_manager_dashboard(callback: CallbackQuery) -> None:
    """Handle dashboard view."""
    async with SessionLocal() as session:
        stats_service = StatisticsService(session)
        overview = await stats_service.get_company_overview()

        dashboard_text = f"""
🏢 **Панель управления**

👥 **Всего тренеров:** {overview['total_coaches']}
⏱️ **Всего отработано часов:** {overview['total_worked_hours']}
📊 **Процент явки:** {overview['attendance_percentage']}%
🏥 **Всего дней болезни:** {overview['total_sick_days']}
❌ **Всего отсутствий:** {overview['total_absences']}

**Статус отчетов:**
✅ Заполнено: {overview['reports_completed']}
📋 Всего: {overview['reports_total']}
📊 Процент заполнения: {round((overview['reports_completed'] / overview['reports_total'] * 100) if overview['reports_total'] > 0 else 0, 1)}%
"""

        await callback.message.edit_text(
            dashboard_text,
            reply_markup=get_back_and_home_buttons(),
            parse_mode="Markdown",
        )

    await callback.answer()


@router.callback_query(F.data == "manager_export")
async def handle_manager_export(callback: CallbackQuery) -> None:
    """Handle export reports."""
    await callback.message.edit_text(
        "📥 Экспорт отчетов\n\nЭта функция еще в разработке.",
        reply_markup=get_back_and_home_buttons(),
    )
    await callback.answer()


@router.callback_query(F.data == "manager_admin_panel")
async def handle_manager_admin_panel(callback: CallbackQuery) -> None:
    """Handle admin panel."""
    admin_panel_text = """
⚙️ **Администрирование**

**Управление тренерами:**
- Добавить тренера
- Изменить информацию
- Деактивировать тренера

**Управление отделениями:**
- Добавить отделение
- Изменить информацию
- Деактивировать отделение

**Управление критериями:**
- Добавить критерий оценки
- Изменить критерий
- Удалить критерий

Эта функция еще в разработке.
"""

    await callback.message.edit_text(
        admin_panel_text,
        reply_markup=get_back_and_home_buttons(),
        parse_mode="Markdown",
    )
    await callback.answer()
