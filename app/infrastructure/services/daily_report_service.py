"""Daily report business logic."""

from datetime import date, time
from decimal import Decimal
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import Coach, DailyReport
from app.domain.models.daily_report import AttendanceStatus, UniformStatus
from app.infrastructure.repositories import (
    CoachRepository,
    CompletionStats,
    DailyReportRepository,
    MonthlyStats,
)
from app.infrastructure.services.audit_service import AuditService

logger = get_logger()

# Attendance states that mean the coach was not at work; hours are forced to
# zero for these regardless of any times left over from an earlier edit.
NON_WORKING_STATUSES = {
    AttendanceStatus.SICK_LEAVE,
    AttendanceStatus.VACATION,
    AttendanceStatus.UNEXCUSED_ABSENCE,
    AttendanceStatus.NOT_FILLED,
}


def calculate_worked_hours(start: time | None, end: time | None) -> float:
    """Hours between two clock times, treating end < start as an overnight shift."""
    if start is None or end is None:
        return 0.0

    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    if end_minutes < start_minutes:
        end_minutes += 24 * 60

    return round((end_minutes - start_minutes) / 60, 2)


class DailyReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = DailyReportRepository(session)
        self.coaches = CoachRepository(session)
        self.audit = AuditService(session)

    # ------------------------------------------------------------- reading

    async def get_report(self, coach_id: int, report_date: date) -> DailyReport | None:
        return await self.repository.get_by_coach_and_date(coach_id, report_date)

    async def get_or_create(
        self, coach: Coach, report_date: date
    ) -> DailyReport:
        """Fetch the day's report, creating a blank one if it is missing."""
        report = await self.repository.get_by_coach_and_date(coach.id, report_date)
        if report is not None:
            return report

        report = DailyReport(
            coach_id=coach.id,
            branch_id=coach.branch_id,
            report_date=report_date,
            upper_uniform=UniformStatus.NO_DATA,
            lower_uniform=UniformStatus.NO_DATA,
            attendance=AttendanceStatus.NOT_FILLED,
            worked_hours=0,
            is_completed=False,
        )
        await self.repository.add(report)
        await self.session.commit()
        return report

    async def branch_reports(
        self, branch_id: int, report_date: date
    ) -> Sequence[DailyReport]:
        return await self.repository.get_by_branch_and_date(branch_id, report_date)

    async def incomplete_reports(
        self, report_date: date, branch_id: int | None = None
    ) -> Sequence[DailyReport]:
        return await self.repository.get_incomplete_for_date(report_date, branch_id)

    async def monthly_reports(
        self, coach_id: int, year: int, month: int
    ) -> Sequence[DailyReport]:
        return await self.repository.get_by_coach_and_month(coach_id, year, month)

    # ------------------------------------------------------------- writing

    async def save_report(
        self,
        *,
        coach: Coach,
        report_date: date,
        attendance: AttendanceStatus,
        upper_uniform: UniformStatus,
        lower_uniform: UniformStatus,
        start_time: time | None,
        end_time: time | None,
        late_arrival_minutes: int = 0,
        early_departure_minutes: int = 0,
        notes: str | None = None,
        admin_comments: str | None = None,
        actor_id: int | None = None,
    ) -> DailyReport:
        """Persist a completed report, deriving worked hours from the times."""
        report = await self.get_or_create(coach, report_date)

        if attendance in NON_WORKING_STATUSES:
            # An absent coach has no hours, no lateness and no early exit,
            # whatever was entered before the status was changed.
            start_time = None
            end_time = None
            worked_hours = 0.0
            late_arrival_minutes = 0
            early_departure_minutes = 0
        else:
            worked_hours = calculate_worked_hours(start_time, end_time)

        report.attendance = attendance
        report.upper_uniform = upper_uniform
        report.lower_uniform = lower_uniform
        report.start_time = start_time
        report.end_time = end_time
        report.worked_hours = Decimal(str(worked_hours))
        report.late_arrival_minutes = max(int(late_arrival_minutes), 0)
        report.early_departure_minutes = max(int(early_departure_minutes), 0)
        report.notes = notes or None
        report.admin_comments = admin_comments or None
        report.is_completed = True
        report.completed_by_user_id = actor_id

        await self.audit.record(
            action="daily_report.saved",
            entity_type="daily_report",
            entity_id=report.id,
            user_id=actor_id,
            changes={
                "coach_id": coach.id,
                "date": report_date,
                "attendance": attendance.value,
                "worked_hours": worked_hours,
            },
        )
        await self.session.commit()
        logger.info(
            "Saved report coach={} date={} hours={}", coach.id, report_date, worked_hours
        )
        return report

    async def ensure_day_exists(self, report_date: date) -> int:
        """Create placeholder reports for a date. Idempotent."""
        created = await self.repository.ensure_reports_exist(report_date)
        if created:
            logger.info("Created {} placeholder reports for {}", created, report_date)
        return created

    # --------------------------------------------------------- aggregation

    async def monthly_stats(self, coach_id: int, year: int, month: int) -> MonthlyStats:
        return await self.repository.monthly_stats(coach_id, year, month)

    async def completion(
        self, start: date, end: date, branch_id: int | None = None
    ) -> CompletionStats:
        return await self.repository.completion_stats(start, end, branch_id)
