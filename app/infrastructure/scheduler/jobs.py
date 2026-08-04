"""Scheduled jobs: placeholder report generation and reminders."""

from datetime import date, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.logger import get_logger
from app.infrastructure.database import get_db_context
from app.infrastructure.services import (
    DailyReportService,
    StatisticsService,
    UserService,
    month_bounds,
)

logger = get_logger()
settings = get_settings()

_scheduler: AsyncIOScheduler | None = None


async def generate_placeholder_reports(for_date: date | None = None) -> int:
    """Ensure every active coach has a row for the day.

    Runs late each evening so the current day is closed out, and again at
    startup to backfill anything missed while the bot was down.
    """
    target = for_date or date.today()
    async with get_db_context() as session:
        created = await DailyReportService(session).ensure_day_exists(target)
    logger.info("Placeholder generation for {}: {} created", target, created)
    return created


async def backfill_recent_days(days: int = 7) -> int:
    """Fill any gaps from the last N days.

    Without this, a weekend of downtime would leave permanent holes - and the
    whole point of the design is that holes cannot exist.
    """
    total = 0
    today = date.today()
    for offset in range(days):
        total += await generate_placeholder_reports(today - timedelta(days=offset))
    if total:
        logger.info("Backfilled {} missing report rows over {} days", total, days)
    return total


async def notify_incomplete_reports(bot: Bot) -> None:
    """Evening nudge listing how many reports are still unfilled."""
    today = date.today()
    async with get_db_context() as session:
        report_service = DailyReportService(session)
        user_service = UserService(session)

        completion = await report_service.completion(today, today)
        if completion.expected == 0 or completion.missing == 0:
            logger.info("No incomplete reports to report for {}", today)
            return

        recipients = list(await user_service.list_managers())
        recipients += list(await user_service.list_admins())

    text = (
        f"🔔 <b>Напоминание</b>\n\n"
        f"На {today.strftime('%d.%m.%Y')} не заполнено "
        f"<b>{completion.missing}</b> отчётов из {completion.expected}.\n"
        f"Заполнено: {completion.percentage}%"
    )

    for user in recipients:
        try:
            await bot.send_message(user.telegram_id, text, parse_mode="HTML")
        except Exception:
            # A blocked bot or deleted chat must not stop the remaining sends.
            logger.warning("Could not notify telegram_id={}", user.telegram_id)


async def notify_month_ready(bot: Bot) -> None:
    """Monthly summary sent to managers once the previous month closes."""
    today = date.today()
    previous_month_end = today.replace(day=1) - timedelta(days=1)
    year, month = previous_month_end.year, previous_month_end.month
    start, end = month_bounds(year, month)

    async with get_db_context() as session:
        stats_service = StatisticsService(session)
        user_service = UserService(session)
        completion = await stats_service.completion(year, month)
        overview = await stats_service.company_overview(year, month)
        managers = list(await user_service.list_managers())

    from app.presentation.telegram.utils import month_name

    text = (
        f"📅 <b>Отчёты за {month_name(month)} {year} готовы</b>\n\n"
        f"Отработано часов: <b>{overview.total_worked_hours}</b>\n"
        f"Процент явки: <b>{overview.attendance_percentage}%</b>\n"
        f"Заполнено отчётов: <b>{completion.completed}</b> из {completion.expected} "
        f"({completion.percentage}%)"
    )

    for user in managers:
        try:
            await bot.send_message(user.telegram_id, text, parse_mode="HTML")
        except Exception:
            logger.warning("Could not notify telegram_id={}", user.telegram_id)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Register the cron jobs and start the scheduler."""
    global _scheduler

    scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)

    gen_hour, gen_minute = settings.parsed_time(
        settings.auto_report_generation_time, (23, 30)
    )
    rem_hour, rem_minute = settings.parsed_time(
        settings.incomplete_report_reminder_time, (19, 0)
    )

    scheduler.add_job(
        generate_placeholder_reports,
        CronTrigger(hour=gen_hour, minute=gen_minute),
        id="generate_placeholder_reports",
        name="Create placeholder daily reports",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Also just after midnight, so the new day exists before anyone opens the bot.
    scheduler.add_job(
        generate_placeholder_reports,
        CronTrigger(hour=0, minute=5),
        id="generate_placeholder_reports_morning",
        name="Create placeholder reports for the new day",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        notify_incomplete_reports,
        CronTrigger(hour=rem_hour, minute=rem_minute),
        id="notify_incomplete_reports",
        name="Notify about incomplete reports",
        kwargs={"bot": bot},
        replace_existing=True,
        misfire_grace_time=1800,
    )

    scheduler.add_job(
        notify_month_ready,
        CronTrigger(day=1, hour=9, minute=0),
        id="notify_month_ready",
        name="Monthly summary",
        kwargs={"bot": bot},
        replace_existing=True,
        misfire_grace_time=7200,
    )

    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "Scheduler started (tz={}, generation={:02d}:{:02d}, reminder={:02d}:{:02d})",
        settings.scheduler_timezone,
        gen_hour,
        gen_minute,
        rem_hour,
        rem_minute,
    )
    return scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    _scheduler = None
