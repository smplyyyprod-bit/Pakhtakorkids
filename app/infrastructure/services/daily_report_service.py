from datetime import date, time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import (
    DailyReport,
    AttendanceStatus,
    UniformStatus,
    Coach,
)
from app.infrastructure.repositories import DailyReportRepository, CoachRepository

logger = get_logger()


class DailyReportService:
    """Service for daily report operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = DailyReportRepository(session)
        self.coach_repository = CoachRepository(session)

    async def create_or_update_report(
        self,
        coach_id: int,
        branch_id: int,
        report_date: date,
        **kwargs,
    ) -> DailyReport:
        """Create or update a daily report."""
        report = await self.repository.get_by_coach_and_date(coach_id, report_date)

        if not report:
            logger.info(f"Creating report for coach {coach_id} on {report_date}")
            report = DailyReport(
                coach_id=coach_id,
                branch_id=branch_id,
                report_date=report_date,
            )
            self.session.add(report)

        # Update fields from kwargs
        for key, value in kwargs.items():
            if hasattr(report, key):
                setattr(report, key, value)

        report.is_completed = True
        report.completed_by_user_id = kwargs.get("completed_by_user_id")

        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def calculate_worked_hours(
        self, start_time: time, end_time: time
    ) -> float:
        """Calculate worked hours from start and end time."""
        if not start_time or not end_time:
            return 0.0

        start = start_time
        end = end_time

        start_minutes = start.hour * 60 + start.minute
        end_minutes = end.hour * 60 + end.minute

        if end_minutes < start_minutes:  # End time is next day
            end_minutes += 24 * 60

        worked_minutes = end_minutes - start_minutes
        return round(worked_minutes / 60, 2)

    async def get_report(
        self, coach_id: int, report_date: date
    ) -> Optional[DailyReport]:
        """Get report for a coach on a date."""
        return await self.repository.get_by_coach_and_date(coach_id, report_date)

    async def get_coach_reports(self, coach_id: int) -> list[DailyReport]:
        """Get all reports for a coach."""
        return await self.repository.get_by_coach(coach_id)

    async def get_monthly_reports(
        self, coach_id: int, year: int, month: int
    ) -> list[DailyReport]:
        """Get reports for a coach in a month."""
        return await self.repository.get_by_coach_and_month(coach_id, year, month)

    async def get_branch_reports(self, branch_id: int, report_date: date) -> list[DailyReport]:
        """Get all reports for a branch on a date."""
        return await self.repository.get_by_branch_and_date(branch_id, report_date)

    async def auto_create_daily_reports(
        self, branch_id: int, report_date: date
    ) -> int:
        """Automatically create empty reports for all active coaches in a branch."""
        coaches = await self.coach_repository.get_active_by_branch(branch_id)
        created_count = 0

        for coach in coaches:
            existing = await self.repository.get_by_coach_and_date(coach.id, report_date)
            if not existing:
                report = DailyReport(
                    coach_id=coach.id,
                    branch_id=branch_id,
                    report_date=report_date,
                    upper_uniform=UniformStatus.NO_DATA,
                    lower_uniform=UniformStatus.NO_DATA,
                    attendance=AttendanceStatus.NOT_FILLED,
                    worked_hours=0,
                    is_completed=False,
                )
                self.session.add(report)
                created_count += 1

        if created_count > 0:
            await self.session.commit()
            logger.info(f"Auto-created {created_count} daily reports for {report_date}")

        return created_count

    async def get_completion_stats(self, branch_id: int, report_date: date) -> dict:
        """Get completion statistics for a branch on a date."""
        all_coaches = await self.coach_repository.get_active_by_branch(branch_id)
        all_reports = await self.repository.get_by_branch_and_date(branch_id, report_date)

        completed_count = sum(1 for r in all_reports if r.is_completed)
        total_count = len(all_coaches)

        return {
            "total": total_count,
            "completed": completed_count,
            "incomplete": total_count - completed_count,
            "percentage": (
                (completed_count / total_count * 100) if total_count > 0 else 0
            ),
        }

    async def get_incomplete_reports(
        self, branch_id: int, report_date: date
    ) -> list[DailyReport]:
        """Get incomplete reports for a branch on a date."""
        all_reports = await self.repository.get_by_branch_and_date(branch_id, report_date)
        return [r for r in all_reports if not r.is_completed]

    async def get_monthly_stats(
        self, coach_id: int, year: int, month: int
    ) -> dict:
        """Get monthly statistics for a coach."""
        return await self.repository.get_monthly_stats(coach_id, year, month)
