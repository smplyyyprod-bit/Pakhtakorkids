"""Bot composition root."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import get_settings
from app.core.logger import get_logger
from app.infrastructure.database import SessionLocal, init_db
from app.infrastructure.scheduler.jobs import (
    backfill_recent_days,
    setup_scheduler,
    shutdown_scheduler,
)
from app.presentation.telegram.commands_menu import (
    set_default_commands,
    sync_all_scoped_commands,
)
from app.presentation.telegram.handlers import build_router
from app.presentation.telegram.middlewares import (
    AuthMiddleware,
    DbSessionMiddleware,
    ErrorMiddleware,
)

logger = get_logger()
settings = get_settings()


def build_storage() -> BaseStorage:
    """Redis when configured, memory otherwise.

    Memory storage loses in-progress forms on restart and cannot be shared
    across processes, so Redis is the right choice for production.
    """
    if settings.redis_url:
        try:
            from aiogram.fsm.storage.redis import RedisStorage

            storage = RedisStorage.from_url(settings.redis_url)
            logger.info("FSM storage: Redis")
            return storage
        except Exception:
            logger.exception("Redis storage unavailable, falling back to memory")

    logger.warning(
        "FSM storage: in-memory - unfinished forms will not survive a restart"
    )
    return MemoryStorage()


def create_bot() -> Bot:
    if not settings.telegram_bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set - copy .env.example to .env and fill it in"
        )
    return Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=build_storage())

    # These must be OUTER middlewares. aiogram evaluates a handler's filters in
    # `handler.check()` before inner middlewares run, so a role filter
    # registered against inner middleware would never see `user` - every
    # role-guarded router would silently match nothing.
    #
    # Order: errors outermost so nothing escapes to the polling loop, then the
    # session, then auth (which needs the session to resolve the user).
    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(ErrorMiddleware())
        observer.outer_middleware(DbSessionMiddleware(SessionLocal))
        observer.outer_middleware(AuthMiddleware())

    dp.include_router(build_router())
    return dp


async def on_startup(bot: Bot) -> None:
    logger.info("Starting up (environment={})", settings.environment)

    # Database work first: a schema or connection problem should surface as
    # itself, not be masked by whatever the first Telegram call reports.
    await init_db()
    # Close any gaps left by downtime before serving the first request.
    await backfill_recent_days(days=7)

    # Drop updates queued while the bot was offline; replaying a backlog of
    # stale button taps would apply them against the wrong day.
    await bot.delete_webhook(drop_pending_updates=True)

    await set_default_commands(bot)

    async with SessionLocal() as session:
        from app.infrastructure.services import UserService

        service = UserService(session)
        users = list(await service.list_admins()) + list(await service.list_managers())
    await sync_all_scoped_commands(bot, users)

    setup_scheduler(bot)

    me = await bot.get_me()
    logger.info("Bot ready: @{} (id={})", me.username, me.id)


async def on_shutdown(bot: Bot) -> None:
    logger.info("Shutting down")
    shutdown_scheduler()
    await bot.session.close()
    logger.info("Shutdown complete")


async def run_bot() -> None:
    bot = create_bot()
    dp = create_dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
