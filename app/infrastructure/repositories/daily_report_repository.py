from datetime import date, datetime
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import DailyReport, AttendanceStatus
from app.infrastructure.repositories.base import BaseRepository


class DailyReportRepository(BaseRepository[DailyReport]):
    """Repository for DailyReport model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, DailyReport)

    async def get_by_coach_and_date(
        self, coach_id: int, report_date: date
    ) -> Optional[DailyReport]:
        """Get report for a coach on a specific date."""
        stmt = select(DailyReport).where(
            and_(
                DailyReport.coach_id == coach_id,
                DailyReport.report_date == report_date,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_date(self, report_date: date) -> list[DailyReport]:
        """Get all reports for a date."""
        stmt = select(DailyReport).where(DailyReport.report_date == report_date)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_coach(self, coach_id: int) -> list[DailyReport]:
        """Get all reports for a coach."""
        stmt = (
            select(DailyReport)
            .where(DailyReport.coach_id == coach_id)
            .order_by(DailyReport.report_date.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_coach_and_month(
        self, coach_id: int, year: int, month: int
    ) -> list[DailyReport]:
        """Get all reports for a coach in a month."""
        stmt = (
            select(DailyReport)
            .where(
                DailyReport.coach_id == coach_id,
                func.extract("year", DailyReport.report_date) == year,
                func.extract("month", DailyReport.report_date) == month,
            )
            .order_by(DailyReport.report_date)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_branch_and_date(
        self, branch_id: int, report_date: date
    ) -> list[DailyReport]:
        """Get all reports for a branch on a date."""
        stmt = (
            select(DailyReport)
            .where(
                and_(
                    DailyReport.branch_id == branch_id,
                    DailyReport.report_date == report_date,
                )
            )
            .order_by(DailyReport.coach_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_incomplete_by_date(self, report_date: date) -> list[DailyReport]:
        """Get incomplete reports for a date."""
        stmt = select(DailyReport).where(
            and_(
                DailyReport.report_date == report_date,
                DailyReport.is_completed == False,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_completed_by_date(self, report_date: date) -> int:
        """Count completed reports for a date."""
        stmt = select(func.count()).select_from(DailyReport).where(
            and_(
                DailyReport.report_date == report_date,
                DailyReport.is_completed == True,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_monthly_stats(
        self, coach_id: int, year: int, month: int
    ) -> dict:
        """Get monthly statistics for a coach."""
        reports = await self.get_by_coach_and_month(coach_id, year, month)

        stats = {
            "worked_hours": 0,
            "worked_days": 0,
            "late_arrivals": 0,
            "total_late_minutes": 0,
            "early_departures": 0,
            "total_early_departure_minutes": 0,
            "days_without_upper_uniform": 0,
            "days_without_lower_uniform": 0,
            "sick_days": 0,
            "vacation_days": 0,
            "unexcused_absences": 0,
        }

        for report in reports:
            if report.is_completed:
                stats["worked_hours"] += float(report.worked_hours or 0)
                if report.worked_hours and report.worked_hours > 0:
                    stats["worked_days"] += 1
                if report.late_arrival_minutes > 0:
                    stats["late_arrivals"] += 1
                    stats["total_late_minutes"] += report.late_arrival_minutes
                if report.early_departure_minutes > 0:
                    stats["early_departures"] += 1
                    stats["total_early_departure_minutes"] += (
                        report.early_departure_minutes
                    )

            from app.domain.models.daily_report import UniformStatus

            if report.upper_uniform == UniformStatus.NO:
                stats["days_without_upper_uniform"] += 1
            if report.lower_uniform == UniformStatus.NO:
                stats["days_without_lower_uniform"] += 1

            if report.attendance == AttendanceStatus.SICK_LEAVE:
                stats["sick_days"] += 1
            elif report.attendance == AttendanceStatus.VACATION:
                stats["vacation_days"] += 1
            elif report.attendance == AttendanceStatus.UNEXCUSED_ABSENCE:
                stats["unexcused_absences"] += 1

        return stats
