from enum import Enum as PyEnum
from datetime import date, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date, Time, Integer, ForeignKey, String, Boolean, Text, Numeric, Enum,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.domain.models.coach import Coach
    from app.domain.models.branch import Branch


class AttendanceStatus(PyEnum):
    """Attendance status options."""

    PRESENT = "present"
    SICK_LEAVE = "sick_leave"
    VACATION = "vacation"
    UNEXCUSED_ABSENCE = "unexcused_absence"
    NOT_FILLED = "not_filled"


class UniformStatus(PyEnum):
    """Uniform status options."""

    YES = "yes"
    NO = "no"
    NO_DATA = "no_data"


class DailyReport(Base, TimestampMixin):
    """Daily report for each coach."""

    __tablename__ = "daily_reports"

    # One report per coach per day, enforced by the database rather than by
    # application logic - this is what makes the nightly auto-create idempotent.
    __table_args__ = (
        UniqueConstraint("coach_id", "report_date", name="uq_daily_report_coach_date"),
        Index("ix_daily_reports_branch_date", "branch_id", "report_date"),
        Index("ix_daily_reports_date", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coach_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coaches.id", ondelete="CASCADE"), nullable=False
    )
    branch_id: Mapped[int] = mapped_column(Integer, ForeignKey("branches.id"), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Uniform
    upper_uniform: Mapped[UniformStatus] = mapped_column(
        Enum(UniformStatus), default=UniformStatus.NO_DATA, nullable=False
    )
    lower_uniform: Mapped[UniformStatus] = mapped_column(
        Enum(UniformStatus), default=UniformStatus.NO_DATA, nullable=False
    )

    # Working Hours
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    worked_hours: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)

    # Attendance
    attendance: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus), default=AttendanceStatus.NOT_FILLED, nullable=False
    )

    # Performance
    late_arrival_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    early_departure_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Additional
    notes: Mapped[str | None] = mapped_column(Text)
    admin_comments: Mapped[str | None] = mapped_column(Text)

    # Status
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )

    coach: Mapped["Coach"] = relationship("Coach", back_populates="daily_reports")
    branch: Mapped["Branch"] = relationship("Branch")

    def __repr__(self) -> str:
        return f"<DailyReport coach={self.coach_id} date={self.report_date}>"
