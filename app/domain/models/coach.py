from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.domain.models.branch import Branch
    from app.domain.models.daily_report import DailyReport


class Coach(Base, TimestampMixin):
    """Coach model representing a sports coach."""

    __tablename__ = "coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unique_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[str] = mapped_column(String(100), nullable=False)
    team: Mapped[str] = mapped_column(String(100), nullable=False)
    branch_id: Mapped[int] = mapped_column(Integer, ForeignKey("branches.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    branch: Mapped["Branch"] = relationship("Branch", back_populates="coaches")
    daily_reports: Mapped[list["DailyReport"]] = relationship(
        "DailyReport", back_populates="coach", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Coach {self.unique_id} {self.full_name}>"
