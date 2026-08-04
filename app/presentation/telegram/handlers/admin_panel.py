"""Administration: coaches, branches and evaluation criteria."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, TelegramObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import User
from app.infrastructure.repositories import EvaluationCriteriaRepository
from app.infrastructure.services import BranchService, CoachService
from app.presentation.telegram.callbacks import AdminActionCB, BranchCB, CoachCB
from app.presentation.telegram.filters import IsManager
from app.presentation.telegram.handlers.common import ack, respond
from app.presentation.telegram.keyboards import (
    branches_keyboard,
    builder_with_nav,
    only_home,
)
from app.presentation.telegram.utils import AdminPanel, esc, format_coach_card

logger = get_logger()

router = Router(name="admin-panel")
router.callback_query.filter(IsManager())
router.message.filter(IsManager())


def _admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, action in [
        ("➕ Добавить тренера", "add_coach"),
        ("👥 Управление тренерами", "manage_coaches"),
        ("➕ Создать отделение", "add_branch"),
        ("🏢 Управление отделениями", "manage_branches"),
        ("📋 Критерии оценки", "criteria"),
        ("⚖️ Сравнить тренеров", "compare"),
        ("📉 Динамика за месяц", "trend"),
    ]:
        builder.button(text=text, callback_data=AdminActionCB(action=action))
    builder.adjust(1)
    return builder_with_nav(builder, back=False)


async def render_admin_menu(event: TelegramObject, session: AsyncSession) -> None:
    coach_count = await CoachService(session).count_active()
    branches = await BranchService(session).list_branches()
    await respond(
        event,
        "⚙️ <b>Администрирование</b>\n\n"
        f"Активных тренеров: <b>{coach_count}</b>\n"
        f"Отделений: <b>{len(branches)}</b>",
        _admin_keyboard(),
    )


@router.callback_query(AdminActionCB.filter(F.action == "admin"))
async def open_admin(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    await ack(callback)
    await state.set_state(AdminPanel.menu)
    await render_admin_menu(callback, session)


# ------------------------------------------------------------- add a branch


@router.callback_query(AdminActionCB.filter(F.action == "add_branch"))
async def add_branch_start(callback: CallbackQuery, state: FSMContext) -> None:
    await ack(callback)
    await state.set_state(AdminPanel.branch_name)
    await respond(
        callback,
        "🏢 <b>Новое отделение</b>\n\nВведите название.\n\n"
        "<i>/cancel — отменить</i>",
    )


@router.message(AdminPanel.branch_name)
async def add_branch_finish(
    message: Message, session: AsyncSession, user: User, state: FSMContext
) -> None:
    name = (message.text or "").strip()
    if not name:
        await respond(message, "❌ Название не может быть пустым.")
        return
    if len(name) > 255:
        await respond(message, "❌ Название слишком длинное (максимум 255 символов).")
        return

    service = BranchService(session)
    if await service.repository.get_by_name(name):
        await respond(message, f"❌ Отделение «{esc(name)}» уже существует.")
        return

    branch = await service.create_branch(name=name, actor_id=user.id)
    await state.set_state(AdminPanel.menu)
    await respond(message, f"✅ Отделение «{esc(branch.name)}» создано.")
    await render_admin_menu(message, session)


# -------------------------------------------------------------- add a coach


@router.callback_query(AdminActionCB.filter(F.action == "add_coach"))
async def add_coach_start(callback: CallbackQuery, state: FSMContext) -> None:
    await ack(callback)
    await state.set_state(AdminPanel.coach_name)
    await respond(
        callback,
        "👤 <b>Новый тренер</b>\n\nВведите ФИО.\n\n<i>/cancel — отменить</i>",
    )


@router.message(AdminPanel.coach_name)
async def add_coach_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await respond(message, "❌ Введите корректное ФИО.")
        return
    await state.update_data(full_name=name[:255])
    await state.set_state(AdminPanel.coach_unique_id)
    await respond(message, "🔢 Введите табельный номер (уникальный).")


@router.message(AdminPanel.coach_unique_id)
async def add_coach_unique_id(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    unique_id = (message.text or "").strip()
    if not unique_id:
        await respond(message, "❌ Табельный номер не может быть пустым.")
        return

    if await CoachService(session).repository.get_by_unique_id(unique_id):
        await respond(
            message, f"❌ Табельный номер «{esc(unique_id)}» уже занят. Введите другой."
        )
        return

    await state.update_data(unique_id=unique_id[:50])
    await state.set_state(AdminPanel.coach_position)
    await respond(message, "💼 Введите должность.")


@router.message(AdminPanel.coach_position)
async def add_coach_position(message: Message, state: FSMContext) -> None:
    position = (message.text or "").strip()
    if not position:
        await respond(message, "❌ Должность не может быть пустой.")
        return
    await state.update_data(position=position[:100])
    await state.set_state(AdminPanel.coach_team)
    await respond(message, "🏅 Введите команду / группу.")


@router.message(AdminPanel.coach_team)
async def add_coach_team(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    team = (message.text or "").strip()
    if not team:
        await respond(message, "❌ Команда не может быть пустой.")
        return

    await state.update_data(team=team[:100])
    branches = await BranchService(session).list_branches()
    if not branches:
        await state.clear()
        await respond(message, "❌ Сначала создайте отделение.", only_home())
        return

    await state.set_state(AdminPanel.coach_branch)
    await respond(
        message,
        "🏢 Выберите отделение для тренера:",
        branches_keyboard(branches, action="assign"),
    )


@router.callback_query(BranchCB.filter(F.action == "assign"), AdminPanel.coach_branch)
async def add_coach_finish(
    callback: CallbackQuery,
    callback_data: BranchCB,
    session: AsyncSession,
    user: User,
    state: FSMContext,
) -> None:
    await ack(callback)
    data = await state.get_data()

    try:
        coach = await CoachService(session).create_coach(
            unique_id=data["unique_id"],
            full_name=data["full_name"],
            position=data["position"],
            team=data["team"],
            branch_id=callback_data.branch_id,
            actor_id=user.id,
        )
    except IntegrityError:
        # Another operator may have claimed the same table number in between.
        await session.rollback()
        await state.clear()
        await respond(
            callback, "❌ Табельный номер уже занят. Попробуйте ещё раз.", only_home()
        )
        return

    await state.set_state(AdminPanel.menu)
    await respond(
        callback,
        f"✅ Тренер добавлен.\n\n{format_coach_card(await CoachService(session).get_coach(coach.id))}",
    )
    await render_admin_menu(callback, session)


# ---------------------------------------------------------------- listings


@router.callback_query(AdminActionCB.filter(F.action == "manage_coaches"))
async def manage_coaches(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    await ack(callback)
    branches = await BranchService(session).list_branches()
    if not branches:
        await respond(callback, "❌ Отделения не найдены.", only_home())
        return
    await respond(
        callback,
        "🏢 Выберите отделение:",
        branches_keyboard(branches, action="manage"),
    )


@router.callback_query(BranchCB.filter(F.action == "manage"))
async def manage_branch_coaches(
    callback: CallbackQuery, callback_data: BranchCB, session: AsyncSession
) -> None:
    await ack(callback)
    coaches = await CoachService(session).list_by_branch(
        callback_data.branch_id, active_only=False
    )
    if not coaches:
        await respond(callback, "В отделении нет тренеров.", only_home())
        return

    builder = InlineKeyboardBuilder()
    for coach in coaches[:40]:
        mark = "✅" if coach.is_active else "⛔️"
        builder.button(
            text=f"{mark} {coach.full_name}",
            callback_data=CoachCB(action="view", coach_id=coach.id),
        )
    builder.adjust(1)
    await respond(callback, "👥 Выберите тренера:", builder_with_nav(builder))


@router.callback_query(CoachCB.filter(F.action == "view"))
async def view_coach(
    callback: CallbackQuery, callback_data: CoachCB, session: AsyncSession
) -> None:
    await ack(callback)
    coach = await CoachService(session).get_coach(callback_data.coach_id)
    if coach is None:
        await respond(callback, "❌ Тренер не найден.", only_home())
        return

    builder = InlineKeyboardBuilder()
    builder.button(
        text="⛔️ Деактивировать" if coach.is_active else "✅ Активировать",
        callback_data=CoachCB(action="toggle", coach_id=coach.id),
    )
    builder.button(
        text="🔀 Перевести в другое отделение",
        callback_data=CoachCB(action="move", coach_id=coach.id),
    )
    builder.adjust(1)
    await respond(callback, format_coach_card(coach), builder_with_nav(builder))


@router.callback_query(CoachCB.filter(F.action == "toggle"))
async def toggle_coach(
    callback: CallbackQuery,
    callback_data: CoachCB,
    session: AsyncSession,
    user: User,
) -> None:
    """Activate or deactivate. Never a hard delete - report history depends on the row."""
    await ack(callback)
    service = CoachService(session)
    coach = await service.get_coach(callback_data.coach_id)
    if coach is None:
        await respond(callback, "❌ Тренер не найден.", only_home())
        return

    await service.set_active(coach.id, not coach.is_active, actor_id=user.id)
    refreshed = await service.get_coach(coach.id)
    await respond(callback, format_coach_card(refreshed), only_home())


@router.callback_query(CoachCB.filter(F.action == "move"))
async def move_coach_start(
    callback: CallbackQuery, callback_data: CoachCB, session: AsyncSession, state: FSMContext
) -> None:
    await ack(callback)
    await state.update_data(moving_coach_id=callback_data.coach_id)
    branches = await BranchService(session).list_branches()
    await respond(
        callback,
        "🔀 Выберите новое отделение:",
        branches_keyboard(branches, action="moveto"),
    )


@router.callback_query(BranchCB.filter(F.action == "moveto"))
async def move_coach_finish(
    callback: CallbackQuery,
    callback_data: BranchCB,
    session: AsyncSession,
    user: User,
    state: FSMContext,
) -> None:
    await ack(callback)
    data = await state.get_data()
    coach_id = data.get("moving_coach_id")
    if not coach_id:
        await respond(callback, "❌ Не выбран тренер.", only_home())
        return

    service = CoachService(session)
    await service.move_to_branch(coach_id, callback_data.branch_id, actor_id=user.id)
    coach = await service.get_coach(coach_id)
    await respond(callback, f"✅ Перевод выполнен.\n\n{format_coach_card(coach)}", only_home())


@router.callback_query(AdminActionCB.filter(F.action == "manage_branches"))
async def manage_branches(callback: CallbackQuery, session: AsyncSession) -> None:
    await ack(callback)
    branches = await BranchService(session).list_branches()
    if not branches:
        await respond(callback, "❌ Отделения не найдены.", only_home())
        return

    lines = ["🏢 <b>Отделения</b>", ""]
    for branch in branches:
        count = await CoachService(session).count_active(branch.id)
        lines.append(f"• {esc(branch.name)} — тренеров: <b>{count}</b>")
    await respond(callback, "\n".join(lines), only_home())


@router.callback_query(AdminActionCB.filter(F.action == "criteria"))
async def list_criteria(callback: CallbackQuery, session: AsyncSession) -> None:
    """Evaluation criteria are data, so new ones need no code change."""
    await ack(callback)
    criteria = await EvaluationCriteriaRepository(session).list_all_with_values()

    if not criteria:
        await respond(callback, "📋 Критерии не заданы.", only_home())
        return

    lines = ["📋 <b>Критерии оценки</b>", ""]
    for item in criteria:
        mark = "✅" if item.is_active else "⛔️"
        lines.append(
            f"{mark} <b>{esc(item.description or item.name)}</b> "
            f"(<code>{esc(item.name)}</code>, тип: {esc(item.field_type)})"
        )
        for value in item.criterion_values:
            lines.append(f"    — {esc(value.label)}")
    await respond(callback, "\n".join(lines), only_home())
