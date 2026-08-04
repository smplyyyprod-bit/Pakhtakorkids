"""Screen renderers.

Each screen is reachable from both a slash command and an inline button, so the
rendering lives here once and both entry points call it.
"""

from datetime import date

from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import Role, User
from app.infrastructure.services import (
    BranchService,
    CoachService,
    DailyReportService,
    StatisticsService,
)
from app.presentation.telegram.handlers.common import respond
from app.presentation.telegram.keyboards import (
    branches_keyboard,
    coaches_keyboard,
    menu_for,
    menu_title,
    months_keyboard,
    only_home,
)
from app.presentation.telegram.utils import (
    ManagerFlow,
    ReportForm,
    esc,
    format_dashboard,
    format_rankings,
    month_name,
)

logger = get_logger()


async def show_main_menu(
    event: TelegramObject, user: User, state: FSMContext | None = None
) -> None:
    if state is not None:
        await state.clear()
    keyboard = menu_for(user)
    if keyboard is None:
        await respond(
            event,
            "⏳ Ваша учётная запись зарегистрирована, но роль ещё не назначена.\n"
            "Обратитесь к руководителю.",
        )
        return
    await respond(event, menu_title(user), keyboard)


async def show_branches(
    event: TelegramObject,
    session: AsyncSession,
    user: User,
    state: FSMContext,
    page: int = 0,
) -> None:
    """Branch picker. Administrators land in the report flow, managers in stats."""
    branches = await BranchService(session).list_branches()
    if not branches:
        await respond(
            event,
            "🏢 Отделения не найдены.\n\nСоздайте отделение через раздел «Администрирование».",
            only_home(),
        )
        return

    if user.role is Role.ADMIN:
        await state.set_state(ReportForm.choosing_branch)
        title = "🏢 <b>Выберите отделение</b>\n\nДалее вы заполните отчёты по тренерам."
        action = "pick"
    else:
        await state.set_state(ManagerFlow.choosing_branch)
        title = "🏢 <b>Выберите отделение</b>"
        action = "stats"

    await respond(event, title, branches_keyboard(branches, action=action, page=page))


async def show_branch_coaches(
    event: TelegramObject,
    session: AsyncSession,
    branch_id: int,
    state: FSMContext,
    *,
    action: str = "fill",
    page: int = 0,
    report_date: date | None = None,
) -> None:
    """Coach list for a branch, marking who already has a completed report."""
    branch = await BranchService(session).get_branch(branch_id)
    if branch is None:
        await respond(event, "❌ Отделение не найдено.", only_home())
        return

    coaches = await CoachService(session).list_by_branch(branch_id)
    if not coaches:
        await respond(
            event,
            f"🏢 <b>{esc(branch.name)}</b>\n\nВ этом отделении нет активных тренеров.",
            only_home(),
        )
        return

    completed: set[int] = set()
    day = report_date or date.today()
    if action == "fill":
        reports = await DailyReportService(session).branch_reports(branch_id, day)
        completed = {r.coach_id for r in reports if r.is_completed}

    remaining = len(coaches) - len(completed)
    header = f"🏢 <b>{esc(branch.name)}</b>"
    if action == "fill":
        header += (
            f"\n📅 {day.strftime('%d.%m.%Y')}\n\n"
            f"Заполнено: <b>{len(completed)}</b> из <b>{len(coaches)}</b>"
        )
        if remaining == 0:
            header += "\n\n✅ Все отчёты за сегодня заполнены."
    else:
        header += f"\n\nТренеров: <b>{len(coaches)}</b>"

    await state.update_data(branch_id=branch_id, page=page)
    await respond(
        event,
        header,
        coaches_keyboard(
            coaches, action=action, page=page, branch_id=branch_id, completed_ids=completed
        ),
    )


async def show_dashboard(
    event: TelegramObject,
    session: AsyncSession,
    year: int | None = None,
    month: int | None = None,
) -> None:
    today = date.today()
    year = year or today.year
    month = month or today.month

    overview = await StatisticsService(session).company_overview(year, month)
    await respond(event, format_dashboard(overview, year, month), only_home())


async def show_analytics(
    event: TelegramObject,
    session: AsyncSession,
    year: int | None = None,
    month: int | None = None,
) -> None:
    today = date.today()
    year = year or today.year
    month = month or today.month

    rankings = await StatisticsService(session).rankings(year, month)
    await respond(event, format_rankings(rankings, year, month), only_home())


async def show_month_picker(
    event: TelegramObject, action: str, ref_id: int = 0, title: str | None = None
) -> None:
    await respond(
        event,
        title or "📅 <b>Выберите месяц</b>",
        months_keyboard(action=action, ref_id=ref_id),
    )
