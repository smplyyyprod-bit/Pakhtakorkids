"""Per-role command menus.

Telegram's BotFather list is global - every user sees the same commands. This
module publishes scoped menus instead, so administrators never see the
analytics commands they are not allowed to run, and managers never see the
report-filling ones. Calling setMyCommands here also means the menu is defined
in version control rather than in a chat window, and it overrides whatever
BotFather holds.
"""

from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
)

from app.core.logger import get_logger
from app.domain.models import Role, User

logger = get_logger()

# Shown to anyone who has not been granted a role yet.
BASE_COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="help", description="Справка"),
]

ADMIN_COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="branches", description="Отделения: заполнить отчёты"),
    BotCommand(command="today", description="Отчёты за сегодня"),
    BotCommand(command="edit", description="Редактировать отчёт"),
    BotCommand(command="cancel", description="Отменить текущее действие"),
    BotCommand(command="help", description="Справка"),
]

MANAGER_COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="coaches", description="Список тренеров"),
    BotCommand(command="monthly", description="Месячная статистика"),
    BotCommand(command="dashboard", description="Панель управления"),
    BotCommand(command="analytics", description="Аналитика и рейтинги"),
    BotCommand(command="export", description="Экспорт отчётов (Excel / PDF)"),
    BotCommand(command="admin", description="Администрирование"),
    BotCommand(command="cancel", description="Отменить текущее действие"),
    BotCommand(command="help", description="Справка"),
]

COMMANDS_BY_ROLE = {
    Role.ADMIN: ADMIN_COMMANDS,
    Role.MANAGER: MANAGER_COMMANDS,
}


async def set_default_commands(bot: Bot) -> None:
    """Publish the minimal menu shown to every private chat."""
    await bot.set_my_commands(BASE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    logger.info("Published default command menu")


async def set_commands_for_user(bot: Bot, user: User) -> None:
    """Publish the role-appropriate menu for one chat."""
    commands = COMMANDS_BY_ROLE.get(user.role)
    if commands is None:
        return
    try:
        await bot.set_my_commands(
            commands, scope=BotCommandScopeChat(chat_id=user.telegram_id)
        )
    except Exception:
        # A user who has never opened the chat cannot receive a scoped menu;
        # that is not a reason to fail the request they were actually making.
        logger.warning(
            "Could not set scoped commands for telegram_id={}", user.telegram_id
        )


async def sync_all_scoped_commands(bot: Bot, users: list[User]) -> int:
    """Refresh scoped menus for known users at startup."""
    updated = 0
    for user in users:
        if not user.is_active or user.role not in COMMANDS_BY_ROLE:
            continue
        await set_commands_for_user(bot, user)
        updated += 1
    logger.info("Synced scoped command menus for {} user(s)", updated)
    return updated
