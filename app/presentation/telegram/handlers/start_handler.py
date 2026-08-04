from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import Role
from app.infrastructure.database import SessionLocal
from app.infrastructure.services import UserService
from app.presentation.telegram.keyboards import (
    get_main_admin_keyboard,
    get_main_manager_keyboard,
)

logger = get_logger()
router = Router()


@router.message(commands=["start"])
async def handle_start(message: Message, state: FSMContext) -> None:
    """Handle /start command."""
    await state.clear()

    async with SessionLocal() as session:
        user_service = UserService(session)

        telegram_id = message.from_user.id
        full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()

        user = await user_service.get_or_create_user(
            telegram_id=telegram_id,
            full_name=full_name,
        )

        await session.commit()

        welcome_text = f"👋 Добро пожаловать, {full_name}!\n\nЭто система управления отчетами тренеров."

        if user.is_admin():
            keyboard = get_main_admin_keyboard()
            welcome_text += "\n\n🔐 Вы входите как администратор."
        elif user.is_manager():
            keyboard = get_main_manager_keyboard()
            welcome_text += "\n\n📊 Вы входите как менеджер."
        else:
            keyboard = None
            welcome_text += "\n\n⏳ Ваша учетная запись ожидает активации."

        if keyboard:
            await message.answer(welcome_text, reply_markup=keyboard)
        else:
            await message.answer(welcome_text)

        logger.info(f"User started: {telegram_id} {full_name}")


@router.callback_query(F.data == "home")
async def handle_home(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle home button."""
    await state.clear()

    async with SessionLocal() as session:
        user_service = UserService(session)
        user = await user_service.get_user(callback.from_user.id)

        if user.is_admin():
            keyboard = get_main_admin_keyboard()
        elif user.is_manager():
            keyboard = get_main_manager_keyboard()
        else:
            keyboard = None

        if keyboard:
            await callback.message.edit_text(
                "🏠 Главное меню",
                reply_markup=keyboard,
            )
        else:
            await callback.answer(
                "❌ Ваша учетная запись не имеет доступа.",
                show_alert=True,
            )

    await callback.answer()


@router.callback_query(F.data == "back")
async def handle_back(callback: CallbackQuery) -> None:
    """Handle back button."""
    await callback.answer()
    await handle_home(callback, FSMContext(storage=None, key="tmp"))
