"""Main Telegram bot application."""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import get_settings
from app.core.logger import get_logger
from app.infrastructure.database import init_db
from app.infrastructure.scheduler import setup_scheduler, shutdown_scheduler
from app.presentation.telegram.handlers import (
    start_router,
    admin_router,
    manager_router,
    report_router,
)

logger = get_logger()
settings = get_settings()


async def on_startup(dp: Dispatcher, bot: Bot) -> None:
    """Startup hook."""
    logger.info("Bot startup started")

    # Initialize database
    await init_db()

    # Setup scheduler
    setup_scheduler()

    logger.info("Bot startup completed")


async def on_shutdown(dp: Dispatcher, bot: Bot) -> None:
    """Shutdown hook."""
    logger.info("Bot shutdown started")

    # Shutdown scheduler
    shutdown_scheduler()

    # Close bot session
    await bot.session.close()

    logger.info("Bot shutdown completed")


async def create_bot() -> tuple[Bot, Dispatcher]:
    """Create bot instance and dispatcher."""
    bot = Bot(token=settings.telegram_bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Include routers
    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(manager_router)
    dp.include_router(report_router)

    return bot, dp


async def run_bot() -> None:
    """Run bot."""
    bot, dp = await create_bot()

    try:
        await on_startup(dp, bot)
        logger.info("Starting bot polling")
        await dp.start_polling(bot)
    finally:
        await on_shutdown(dp, bot)
