from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class EvaluationCriteria(Base, TimestampMixin):
    """Configurable evaluation criteria for daily reports."""

    __tablename__ = "evaluation_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    field_type: Mapped[str] = mapped_column(String(50), nullable=False)  # text, number, select, boolean
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    criterion_values: Mapped[list["CriterionValue"]] = relationship(
        "CriterionValue", back_populates="criterion", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<EvaluationCriteria {self.name}>"


class CriterionValue(Base, TimestampMixin):
    """Predefined values for evaluation criteria."""

    __tablename__ = "criterion_values"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    criterion_id: Mapped[int] = mapped_column(Integer, ForeignKey("evaluation_criteria.id"), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    criterion: Mapped["EvaluationCriteria"] = relationship("EvaluationCriteria", back_populates="criterion_values")

    def __repr__(self) -> str:
        return f"<CriterionValue {self.label}>"
