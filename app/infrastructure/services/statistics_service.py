from datetime import date, datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import AttendanceStatus
from app.infrastructure.repositories import DailyReportRepository, CoachRepository

logger = get_logger()


class StatisticsService:
    """Service for calculating statistics."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.report_repository = DailyReportRepository(session)
        self.coach_repository = CoachRepository(session)

    async def get_company_overview(self) -> dict:
        """Get company-wide overview statistics."""
        all_coaches = await self.coach_repository.get_active_coaches()
        today = date.today()

        today_reports = await self.report_repository.get_by_date(today)

        total_worked_hours = 0.0
        total_sick_days = 0
        total_absences = 0
        present_count = 0

        for report in today_reports:
            total_worked_hours += float(report.worked_hours or 0)

            if report.attendance == AttendanceStatus.SICK_LEAVE:
                total_sick_days += 1
            elif report.attendance == AttendanceStatus.UNEXCUSED_ABSENCE:
                total_absences += 1
            elif report.attendance == AttendanceStatus.PRESENT:
                present_count += 1

        attendance_percentage = (
            (present_count / len(all_coaches) * 100) if all_coaches else 0
        )

        return {
            "total_coaches": len(all_coaches),
            "total_worked_hours": round(total_worked_hours, 2),
            "attendance_percentage": round(attendance_percentage, 2),
            "total_sick_days": total_sick_days,
            "total_absences": total_absences,
            "reports_completed": sum(1 for r in today_reports if r.is_completed),
            "reports_total": len(today_reports),
        }

    async def get_coach_rankings(self, year: int, month: int) -> dict:
        """Get coach rankings for a month."""
        coaches = await self.coach_repository.get_active_coaches()

        rankings = {
            "most_worked_hours": [],
            "most_punctual": [],
            "most_late_arrivals": [],
            "most_uniform_violations": [],
        }

        coach_stats = []

        for coach in coaches:
            stats = await self.report_repository.get_monthly_stats(coach.id, year, month)
            coach_stats.append({
                "coach": coach,
                "stats": stats,
            })

        # Sort by worked hours
        coach_stats_sorted = sorted(
            coach_stats,
            key=lambda x: x["stats"]["worked_hours"],
            reverse=True,
        )
        rankings["most_worked_hours"] = coach_stats_sorted[:10]

        # Sort by punctuality (fewest late arrivals)
        coach_stats_sorted = sorted(
            coach_stats,
            key=lambda x: x["stats"]["late_arrivals"],
        )
        rankings["most_punctual"] = coach_stats_sorted[:10]

        # Sort by late arrivals
        coach_stats_sorted = sorted(
            coach_stats,
            key=lambda x: x["stats"]["late_arrivals"],
            reverse=True,
        )
        rankings["most_late_arrivals"] = coach_stats_sorted[:10]

        # Sort by uniform violations
        coach_stats_sorted = sorted(
            coach_stats,
            key=lambda x: (
                x["stats"]["days_without_upper_uniform"]
                + x["stats"]["days_without_lower_uniform"]
            ),
            reverse=True,
        )
        rankings["most_uniform_violations"] = coach_stats_sorted[:10]

        return rankings

    async def get_attendance_trends(self, year: int, month: int) -> dict:
        """Get attendance trends for a month."""
        from datetime import datetime

        trends = {}
        coaches = await self.coach_repository.get_active_coaches()

        for day in range(1, 32):
            try:
                report_date = date(year, month, day)
                reports = await self.report_repository.get_by_date(report_date)

                present = sum(
                    1 for r in reports if r.attendance == AttendanceStatus.PRESENT
                )
                sick = sum(
                    1 for r in reports if r.attendance == AttendanceStatus.SICK_LEAVE
                )
                vacation = sum(
                    1 for r in reports if r.attendance == AttendanceStatus.VACATION
                )
                absent = sum(
                    1 for r in reports
                    if r.attendance == AttendanceStatus.UNEXCUSED_ABSENCE
                )

                trends[str(day)] = {
                    "present": present,
                    "sick": sick,
                    "vacation": vacation,
                    "absent": absent,
                }
            except ValueError:
                break

        return trends
