"""Company-wide analytics for the manager dashboard."""

import calendar
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.infrastructure.repositories import (
    CoachRepository,
    CompletionStats,
    DailyReportRepository,
    MonthlyStats,
)

logger = get_logger()


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """First and last calendar day of a month."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


@dataclass(slots=True)
class CompanyOverview:
    total_coaches: int
    total_worked_hours: float
    attendance_percentage: float
    total_sick_days: int
    total_absences: int
    completion: CompletionStats


@dataclass(slots=True)
class Rankings:
    most_worked_hours: list[MonthlyStats]
    most_punctual: list[MonthlyStats]
    most_late_arrivals: list[MonthlyStats]
    most_uniform_violations: list[MonthlyStats]


class StatisticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.reports = DailyReportRepository(session)
        self.coaches = CoachRepository(session)

    async def company_overview(self, year: int, month: int) -> CompanyOverview:
        """Month-to-date figures across the whole company."""
        start, end = month_bounds(year, month)
        stats = await self.reports.monthly_stats_all_coaches(year, month)
        completion = await self.reports.completion_stats(start, end)
        total_coaches = await self.coaches.count_active()

        total_hours = sum(s.worked_hours for s in stats)
        total_sick = sum(s.sick_days for s in stats)
        total_absences = sum(s.unexcused_absences for s in stats)

        # Attendance is measured against days that were actually recorded, so a
        # month in progress is not penalised for days that have not happened.
        recorded_days = sum(s.total_days for s in stats)
        absent_days = total_sick + total_absences + sum(
            s.vacation_days + s.not_filled_days for s in stats
        )
        attendance_pct = (
            round((recorded_days - absent_days) / recorded_days * 100, 1)
            if recorded_days
            else 0.0
        )

        return CompanyOverview(
            total_coaches=total_coaches,
            total_worked_hours=round(total_hours, 2),
            attendance_percentage=attendance_pct,
            total_sick_days=total_sick,
            total_absences=total_absences,
            completion=completion,
        )

    async def rankings(
        self, year: int, month: int, limit: int = 10
    ) -> Rankings:
        """Leaderboards built from one grouped query, not one query per coach."""
        stats = list(await self.reports.monthly_stats_all_coaches(year, month))

        worked = sorted(stats, key=lambda s: s.worked_hours, reverse=True)
        late_desc = sorted(stats, key=lambda s: s.total_late_minutes, reverse=True)
        # "Most punctual" only means something for coaches who actually worked.
        punctual = sorted(
            [s for s in stats if s.worked_days > 0],
            key=lambda s: (s.total_late_minutes, -s.worked_days),
        )
        uniform = sorted(stats, key=lambda s: s.uniform_violations, reverse=True)

        return Rankings(
            most_worked_hours=worked[:limit],
            most_punctual=punctual[:limit],
            most_late_arrivals=[s for s in late_desc if s.total_late_minutes > 0][:limit],
            most_uniform_violations=[s for s in uniform if s.uniform_violations > 0][
                :limit
            ],
        )

    async def compare_coaches(
        self, year: int, month: int, branch_id: int | None = None
    ) -> list[MonthlyStats]:
        """All coaches' month figures side by side, ordered by hours worked."""
        stats = list(
            await self.reports.monthly_stats_all_coaches(year, month, branch_id)
        )
        return sorted(stats, key=lambda s: s.worked_hours, reverse=True)

    async def attendance_trend(
        self, year: int, month: int, branch_id: int | None = None
    ) -> list[dict[str, object]]:
        start, end = month_bounds(year, month)
        return await self.reports.attendance_trend(start, end, branch_id)

    async def completion(
        self, year: int, month: int, branch_id: int | None = None
    ) -> CompletionStats:
        start, end = month_bounds(year, month)
        return await self.reports.completion_stats(start, end, branch_id)
