from datetime import date, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.logger import get_logger
from app.infrastructure.database import SessionLocal
from app.infrastructure.services import (
    BranchService,
    DailyReportService,
)

logger = get_logger()
scheduler = AsyncIOScheduler()
settings = get_settings()


async def auto_create_daily_reports_job() -> None:
    """Automatically create daily reports for all coaches."""
    try:
        logger.info("Starting daily report auto-creation job")
        async with SessionLocal() as session:
            branch_service = BranchService(session)
            report_service = DailyReportService(session)

            branches = await branch_service.get_all_branches()
            today = date.today()

            total_created = 0
            for branch in branches:
                created = await report_service.auto_create_daily_reports(
                    branch.id, today
                )
                total_created += created

            logger.info(f"Auto-created {total_created} daily reports")

    except Exception as e:
        logger.error(f"Error in auto_create_daily_reports_job: {str(e)}")


async def incomplete_reports_notification_job() -> None:
    """Send notifications about incomplete reports."""
    try:
        logger.info("Starting incomplete reports notification job")
        async with SessionLocal() as session:
            branch_service = BranchService(session)
            report_service = DailyReportService(session)

            branches = await branch_service.get_all_branches()
            today = date.today()

            for branch in branches:
                incomplete_reports = await report_service.get_incomplete_reports(
                    branch.id, today
                )

                if incomplete_reports:
                    count = len(incomplete_reports)
                    logger.info(
                        f"Branch {branch.name} has {count} incomplete reports"
                    )

    except Exception as e:
        logger.error(f"Error in incomplete_reports_notification_job: {str(e)}")


def setup_scheduler() -> None:
    """Setup and start the scheduler."""
    try:
        # Parse auto report generation time from settings
        time_parts = settings.auto_report_generation_time.split(":")
        hour = int(time_parts[0])
        minute = int(time_parts[1])

        # Add jobs
        scheduler.add_job(
            auto_create_daily_reports_job,
            CronTrigger(hour=hour, minute=minute, timezone=settings.scheduler_timezone),
            id="auto_create_daily_reports",
            name="Auto-create daily reports",
            replace_existing=True,
        )

        scheduler.add_job(
            incomplete_reports_notification_job,
            CronTrigger(
                hour=hour + 1 if hour < 23 else 0,
                minute=minute,
                timezone=settings.scheduler_timezone,
            ),
            id="incomplete_reports_notification",
            name="Send incomplete reports notifications",
            replace_existing=True,
        )

        scheduler.start()
        logger.info("Scheduler started successfully")

    except Exception as e:
        logger.error(f"Error setting up scheduler: {str(e)}")


def shutdown_scheduler() -> None:
    """Shutdown the scheduler."""
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Scheduler shutdown successfully")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {str(e)}")
