"""The twelve slash commands.

Manager-only commands are registered on a router carrying the IsManager filter,
so an administrator's `/dashboard` simply does not match a handler. The
restriction is structural rather than a check a future handler could forget.
"""

from datetime import date, timedelta

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import Role, User
from app.infrastructure.services import CoachService, DailyReportService
from app.presentation.telegram.filters import IsManager
from app.presentation.telegram.handlers.common import respond
from app.presentation.telegram.handlers.screens import (
    show_analytics,
    show_branches,
    show_dashboard,
    show_main_menu,
    show_month_picker,
)
from app.presentation.telegram.keyboards import only_home
from app.presentation.telegram.utils import (
    esc,
    format_incomplete_notice,
    ManagerFlow,
)

logger = get_logger()

# Available to every authenticated user.
router = Router(name="commands")
# Manager-only surface: analytics, exports, administration.
manager_router = Router(name="manager-commands")
manager_router.message.filter(IsManager())

HELP_ADMIN = """❓ <b>Справка — администратор</b>

Ваша задача: заполнять ежедневные отчёты по тренерам.

<b>Команды</b>
/start — главное меню
/branches — выбрать отделение и начать заполнение
/today — статус отчётов за сегодня
/edit — изменить уже заполненный отчёт
/cancel — прервать текущее заполнение
/help — эта справка

<b>Как это работает</b>
1. Выберите отделение.
2. Бот открывает первого незаполненного тренера.
3. Отвечайте кнопками — печатать почти не нужно.
4. После сохранения сразу открывается следующий тренер.

Отчёт создаётся автоматически на каждого активного тренера каждый день, поэтому
пропущенных дат в системе не бывает."""

HELP_MANAGER = """❓ <b>Справка — руководитель</b>

<b>Команды</b>
/start — главное меню
/coaches — список тренеров
/monthly — месячная статистика по тренеру
/dashboard — сводка по компании
/analytics — рейтинги и динамика
/export — выгрузка в Excel или PDF
/admin — управление тренерами, отделениями и критериями
/cancel — сбросить текущее действие
/help — эта справка

<b>Незаполненные отчёты</b>
Отчёт создаётся автоматически на каждого активного тренера. Незаполненные
записи видны в сводке и учитываются в месячной статистике."""


# ------------------------------------------------------------------ general


@router.message(CommandStart())
async def cmd_start(message: Message, user: User, state: FSMContext) -> None:
    logger.info("/start from telegram_id={} role={}", user.telegram_id, user.role.value)
    await show_main_menu(message, user, state)


@router.message(Command("help"))
async def cmd_help(message: Message, user: User) -> None:
    text = HELP_MANAGER if user.role is Role.MANAGER else HELP_ADMIN
    await respond(message, text, only_home())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, user: User, state: FSMContext) -> None:
    """Escape hatch out of a half-finished form."""
    current = await state.get_state()
    await state.clear()
    if current is None:
        await respond(message, "Нечего отменять.", only_home())
        return
    await respond(message, "✖️ Действие отменено.")
    await show_main_menu(message, user)


# ------------------------------------------------------------ administrator


@router.message(Command("branches"))
async def cmd_branches(
    message: Message, session: AsyncSession, user: User, state: FSMContext
) -> None:
    await show_branches(message, session, user, state)


@router.message(Command("today"))
async def cmd_today(message: Message, session: AsyncSession, user: User) -> None:
    """Today's completion status.

    Administrators see their own branch; managers see the whole company.
    """
    service = DailyReportService(session)
    day = date.today()
    branch_id = user.branch_id if user.role is Role.ADMIN else None

    incomplete = await service.incomplete_reports(day, branch_id)
    completion = await service.completion(day, day, branch_id)

    if completion.expected == 0:
        await respond(
            message,
            f"📋 На {day.strftime('%d.%m.%Y')} отчётов ещё не создано.\n\n"
            "Записи создаются автоматически по расписанию.",
            only_home(),
        )
        return

    header = (
        f"📋 <b>Отчёты за {day.strftime('%d.%m.%Y')}</b>\n\n"
        f"Заполнено: <b>{completion.completed}</b> из <b>{completion.expected}</b>"
        f" ({completion.percentage}%)"
    )

    if not incomplete:
        await respond(message, header + "\n\n✅ Все отчёты заполнены.", only_home())
        return

    names = [
        f"• {esc(r.coach.full_name)}" for r in incomplete[:25] if r.coach is not None
    ]
    body = "\n".join(names)
    if len(incomplete) > 25:
        body += f"\n<i>…и ещё {len(incomplete) - 25}</i>"

    await respond(
        message,
        f"{header}\n\n⚠️ <b>Не заполнены ({len(incomplete)}):</b>\n{body}",
        only_home(),
    )


@router.message(Command("edit"))
async def cmd_edit(
    message: Message, session: AsyncSession, user: User, state: FSMContext
) -> None:
    """Re-open an existing report for correction."""
    await state.clear()
    await show_branches(message, session, user, state)
    await respond(
        message,
        "✏️ Выберите отделение, затем тренера — отчёт откроется для изменения.",
    )


# ------------------------------------------------------------------ manager


@manager_router.message(Command("coaches"))
async def cmd_coaches(message: Message, session: AsyncSession) -> None:
    coaches = await CoachService(session).list_all()
    if not coaches:
        await respond(message, "👥 Тренеры не заведены.", only_home())
        return

    by_branch: dict[str, list[str]] = {}
    for coach in coaches:
        branch_name = coach.branch.name if coach.branch else "Без отделения"
        by_branch.setdefault(branch_name, []).append(
            f"• {esc(coach.full_name)} — {esc(coach.position)} ({esc(coach.team)})"
        )

    lines = [f"👥 <b>Тренеры ({len(coaches)})</b>", ""]
    for branch_name, entries in sorted(by_branch.items()):
        lines.append(f"🏢 <b>{esc(branch_name)}</b>")
        lines.extend(entries)
        lines.append("")

    text = "\n".join(lines).strip()
    # Telegram rejects messages over 4096 characters.
    if len(text) > 3900:
        text = text[:3900] + "\n\n<i>…список сокращён</i>"
    await respond(message, text, only_home())


@manager_router.message(Command("monthly"))
async def cmd_monthly(
    message: Message, session: AsyncSession, user: User, state: FSMContext
) -> None:
    await state.set_state(ManagerFlow.choosing_branch)
    await show_branches(message, session, user, state)


@manager_router.message(Command("dashboard"))
async def cmd_dashboard(message: Message, session: AsyncSession) -> None:
    await show_dashboard(message, session)


@manager_router.message(Command("analytics"))
async def cmd_analytics(message: Message, session: AsyncSession) -> None:
    await show_analytics(message, session)


@manager_router.message(Command("export"))
async def cmd_export(
    message: Message, session: AsyncSession, user: User, state: FSMContext
) -> None:
    await state.set_state(ManagerFlow.choosing_branch)
    await show_branches(message, session, user, state)
    await respond(message, "📥 Выберите отделение, затем тренера и месяц для выгрузки.")


@manager_router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession) -> None:
    from app.presentation.telegram.handlers.admin_panel import render_admin_menu

    await render_admin_menu(message, session)
