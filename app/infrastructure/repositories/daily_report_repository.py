"""Daily report queries.

Aggregation happens in SQL. The earlier approach - loading every row for a
coach and summing in Python, once per coach - meant a manager dashboard issued
one query per coach. At 50 coaches that is 50 round trips for a single screen,
and it grows linearly with headcount.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Sequence

from sqlalchemy import Select, and_, case, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Coach, DailyReport
from app.domain.models.daily_report import AttendanceStatus, UniformStatus
from app.infrastructure.repositories.base import BaseRepository


@dataclass(slots=True)
class MonthlyStats:
    """Aggregated month figures for one coach."""

    coach_id: int
    coach_name: str = ""
    worked_hours: float = 0.0
    worked_days: int = 0
    late_arrivals: int = 0
    total_late_minutes: int = 0
    early_departures: int = 0
    total_early_departure_minutes: int = 0
    days_without_upper_uniform: int = 0
    days_without_lower_uniform: int = 0
    sick_days: int = 0
    vacation_days: int = 0
    unexcused_absences: int = 0
    not_filled_days: int = 0
    total_days: int = 0

    @property
    def uniform_violations(self) -> int:
        return self.days_without_upper_uniform + self.days_without_lower_uniform


@dataclass(slots=True)
class CompletionStats:
    """Expected vs. completed reports over a period."""

    expected: int = 0
    completed: int = 0

    @property
    def missing(self) -> int:
        return max(self.expected - self.completed, 0)

    @property
    def percentage(self) -> float:
        if self.expected <= 0:
            return 0.0
        return round(self.completed / self.expected * 100, 1)


def _count_when(condition) -> object:
    """SUM(CASE WHEN cond THEN 1 ELSE 0 END) - portable conditional count."""
    return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)


class DailyReportRepository(BaseRepository[DailyReport]):
    """Queries over daily_reports."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DailyReport)

    # ---------------------------------------------------------------- reads

    async def get_by_coach_and_date(
        self, coach_id: int, report_date: date
    ) -> DailyReport | None:
        stmt = select(DailyReport).where(
            DailyReport.coach_id == coach_id,
            DailyReport.report_date == report_date,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_coach_and_month(
        self, coach_id: int, year: int, month: int
    ) -> Sequence[DailyReport]:
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
    ) -> Sequence[DailyReport]:
        """Reports for a branch on a date, with the coach eager-loaded.

        Eager loading matters here: lazy-loading `report.coach` from an async
        session raises MissingGreenlet, which is exactly the kind of failure
        that only shows up once a real user opens the screen.
        """
        stmt = (
            select(DailyReport)
            .where(
                DailyReport.branch_id == branch_id,
                DailyReport.report_date == report_date,
            )
            .options(selectinload(DailyReport.coach))
            .join(Coach, Coach.id == DailyReport.coach_id)
            .order_by(Coach.full_name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_incomplete_for_date(
        self, report_date: date, branch_id: int | None = None
    ) -> Sequence[DailyReport]:
        conditions = [
            DailyReport.report_date == report_date,
            DailyReport.is_completed.is_(False),
        ]
        if branch_id is not None:
            conditions.append(DailyReport.branch_id == branch_id)

        stmt = (
            select(DailyReport)
            .where(and_(*conditions))
            .options(selectinload(DailyReport.coach))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ---------------------------------------------------------- aggregation

    def _stats_select(self) -> Select:
        """Shared aggregate projection used by the per-coach and ranking queries."""
        return select(
            DailyReport.coach_id.label("coach_id"),
            func.coalesce(func.sum(DailyReport.worked_hours), 0).label("worked_hours"),
            _count_when(DailyReport.worked_hours > 0).label("worked_days"),
            _count_when(DailyReport.late_arrival_minutes > 0).label("late_arrivals"),
            func.coalesce(func.sum(DailyReport.late_arrival_minutes), 0).label(
                "total_late_minutes"
            ),
            _count_when(DailyReport.early_departure_minutes > 0).label(
                "early_departures"
            ),
            func.coalesce(func.sum(DailyReport.early_departure_minutes), 0).label(
                "total_early_departure_minutes"
            ),
            _count_when(DailyReport.upper_uniform == UniformStatus.NO).label(
                "days_without_upper_uniform"
            ),
            _count_when(DailyReport.lower_uniform == UniformStatus.NO).label(
                "days_without_lower_uniform"
            ),
            _count_when(DailyReport.attendance == AttendanceStatus.SICK_LEAVE).label(
                "sick_days"
            ),
            _count_when(DailyReport.attendance == AttendanceStatus.VACATION).label(
                "vacation_days"
            ),
            _count_when(
                DailyReport.attendance == AttendanceStatus.UNEXCUSED_ABSENCE
            ).label("unexcused_absences"),
            _count_when(DailyReport.attendance == AttendanceStatus.NOT_FILLED).label(
                "not_filled_days"
            ),
            func.count().label("total_days"),
        )

    @staticmethod
    def _row_to_stats(row, coach_name: str = "") -> MonthlyStats:
        return MonthlyStats(
            coach_id=row.coach_id,
            coach_name=coach_name,
            worked_hours=float(row.worked_hours or 0),
            worked_days=int(row.worked_days or 0),
            late_arrivals=int(row.late_arrivals or 0),
            total_late_minutes=int(row.total_late_minutes or 0),
            early_departures=int(row.early_departures or 0),
            total_early_departure_minutes=int(
                row.total_early_departure_minutes or 0
            ),
            days_without_upper_uniform=int(row.days_without_upper_uniform or 0),
            days_without_lower_uniform=int(row.days_without_lower_uniform or 0),
            sick_days=int(row.sick_days or 0),
            vacation_days=int(row.vacation_days or 0),
            unexcused_absences=int(row.unexcused_absences or 0),
            not_filled_days=int(row.not_filled_days or 0),
            total_days=int(row.total_days or 0),
        )

    async def monthly_stats(
        self, coach_id: int, year: int, month: int
    ) -> MonthlyStats:
        """Aggregate one coach's month.

        Incomplete records are deliberately included: they carry zeroed hours
        and NOT_FILLED attendance, which is what makes a gap visible in the
        totals instead of silently vanishing.
        """
        stmt = (
            self._stats_select()
            .where(
                DailyReport.coach_id == coach_id,
                func.extract("year", DailyReport.report_date) == year,
                func.extract("month", DailyReport.report_date) == month,
            )
            .group_by(DailyReport.coach_id)
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if row is None:
            return MonthlyStats(coach_id=coach_id)
        return self._row_to_stats(row)

    async def monthly_stats_all_coaches(
        self, year: int, month: int, branch_id: int | None = None
    ) -> list[MonthlyStats]:
        """Aggregate every coach's month in a single grouped query."""
        conditions = [
            func.extract("year", DailyReport.report_date) == year,
            func.extract("month", DailyReport.report_date) == month,
        ]
        if branch_id is not None:
            conditions.append(DailyReport.branch_id == branch_id)

        stmt = (
            self._stats_select()
            .add_columns(Coach.full_name.label("coach_name"))
            .join(Coach, Coach.id == DailyReport.coach_id)
            .where(and_(*conditions, Coach.is_active.is_(True)))
            .group_by(DailyReport.coach_id, Coach.full_name)
        )
        result = await self.session.execute(stmt)
        return [self._row_to_stats(row, row.coach_name) for row in result]

    async def completion_stats(
        self,
        start: date,
        end: date,
        branch_id: int | None = None,
    ) -> CompletionStats:
        """Expected vs completed reports across a date range (inclusive)."""
        conditions = [
            DailyReport.report_date >= start,
            DailyReport.report_date <= end,
        ]
        if branch_id is not None:
            conditions.append(DailyReport.branch_id == branch_id)

        stmt = select(
            func.count().label("expected"),
            _count_when(DailyReport.is_completed.is_(True)).label("completed"),
        ).where(and_(*conditions))

        result = await self.session.execute(stmt)
        row = result.one()
        return CompletionStats(
            expected=int(row.expected or 0), completed=int(row.completed or 0)
        )

    async def attendance_trend(
        self, start: date, end: date, branch_id: int | None = None
    ) -> list[dict[str, object]]:
        """Per-day attendance breakdown, ordered by date."""
        conditions = [
            DailyReport.report_date >= start,
            DailyReport.report_date <= end,
        ]
        if branch_id is not None:
            conditions.append(DailyReport.branch_id == branch_id)

        stmt = (
            select(
                DailyReport.report_date.label("day"),
                _count_when(DailyReport.attendance == AttendanceStatus.PRESENT).label(
                    "present"
                ),
                _count_when(
                    DailyReport.attendance == AttendanceStatus.SICK_LEAVE
                ).label("sick"),
                _count_when(DailyReport.attendance == AttendanceStatus.VACATION).label(
                    "vacation"
                ),
                _count_when(
                    DailyReport.attendance == AttendanceStatus.UNEXCUSED_ABSENCE
                ).label("absent"),
                _count_when(
                    DailyReport.attendance == AttendanceStatus.NOT_FILLED
                ).label("not_filled"),
                func.coalesce(func.sum(DailyReport.worked_hours), 0).label("hours"),
                func.count().label("total"),
            )
            .where(and_(*conditions))
            .group_by(DailyReport.report_date)
            .order_by(DailyReport.report_date)
        )
        result = await self.session.execute(stmt)
        return [
            {
                "day": row.day,
                "present": int(row.present or 0),
                "sick": int(row.sick or 0),
                "vacation": int(row.vacation or 0),
                "absent": int(row.absent or 0),
                "not_filled": int(row.not_filled or 0),
                "hours": float(row.hours or 0),
                "total": int(row.total or 0),
            }
            for row in result
        ]

    # ----------------------------------------------------------- generation

    async def ensure_reports_exist(self, report_date: date) -> int:
        """Create a placeholder report for every active coach on a date.

        Uses INSERT ... ON CONFLICT DO NOTHING against the
        (coach_id, report_date) unique constraint, so it is safe to run
        repeatedly, concurrently, or after a partially-completed run - which is
        what makes "the database never has a missing day" actually hold rather
        than being a property the scheduler hopes for.
        """
        coaches = await self.session.execute(
            select(Coach.id, Coach.branch_id).where(Coach.is_active.is_(True))
        )
        rows = [
            {
                "coach_id": coach_id,
                "branch_id": branch_id,
                "report_date": report_date,
                "upper_uniform": UniformStatus.NO_DATA,
                "lower_uniform": UniformStatus.NO_DATA,
                "attendance": AttendanceStatus.NOT_FILLED,
                "worked_hours": 0,
                "late_arrival_minutes": 0,
                "early_departure_minutes": 0,
                "is_completed": False,
            }
            for coach_id, branch_id in coaches.all()
        ]
        if not rows:
            return 0

        stmt = (
            pg_insert(DailyReport)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_daily_report_coach_date")
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return int(result.rowcount or 0)
