"""Home / back / cancel / pagination."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import Role, User
from app.presentation.telegram.callbacks import NavCB, PageCB
from app.presentation.telegram.handlers.common import ack
from app.presentation.telegram.handlers.screens import (
    show_branch_coaches,
    show_branches,
    show_main_menu,
)

logger = get_logger()
router = Router(name="navigation")


@router.callback_query(NavCB.filter(F.target == "noop"))
async def noop(callback: CallbackQuery) -> None:
    """The page-indicator button - acknowledge and do nothing."""
    await ack(callback)


@router.callback_query(NavCB.filter(F.target == "home"))
async def go_home(callback: CallbackQuery, user: User, state: FSMContext) -> None:
    await ack(callback)
    await show_main_menu(callback, user, state)


@router.callback_query(NavCB.filter(F.target == "cancel"))
async def cancel(callback: CallbackQuery, user: User, state: FSMContext) -> None:
    await ack(callback, "Отменено")
    await show_main_menu(callback, user, state)


@router.callback_query(NavCB.filter(F.target == "back"))
async def go_back(
    callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext
) -> None:
    """One step back.

    Rather than maintaining a navigation stack, this returns to the nearest
    sensible parent screen for the current state - which is what users actually
    expect from a menu tree this shallow.
    """
    await ack(callback)
    current = await state.get_state()
    data = await state.get_data()

    if current is None:
        await show_main_menu(callback, user, state)
        return

    branch_id = data.get("branch_id")
    if branch_id and current.startswith("ReportForm"):
        await show_branch_coaches(callback, session, branch_id, state)
        return

    if current.startswith(("ManagerFlow", "ReportForm")):
        await show_branches(callback, session, user, state)
        return

    await show_main_menu(callback, user, state)


@router.callback_query(PageCB.filter(F.scope == "branches"))
async def page_branches(
    callback: CallbackQuery,
    callback_data: PageCB,
    session: AsyncSession,
    user: User,
    state: FSMContext,
) -> None:
    await ack(callback)
    await show_branches(callback, session, user, state, page=callback_data.page)


@router.callback_query(PageCB.filter(F.scope == "coaches"))
async def page_coaches(
    callback: CallbackQuery,
    callback_data: PageCB,
    session: AsyncSession,
    user: User,
    state: FSMContext,
) -> None:
    await ack(callback)
    action = "fill" if user.role is Role.ADMIN else "stats"
    await show_branch_coaches(
        callback,
        session,
        callback_data.ref_id,
        state,
        action=action,
        page=callback_data.page,
    )
