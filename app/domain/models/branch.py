from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.domain.models.user import User
    from app.domain.models.coach import Coach


class Branch(Base, TimestampMixin):
    """Branch model representing a physical location/office."""

    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list["User"]] = relationship("User", back_populates="branch")
    coaches: Mapped[list["Coach"]] = relationship("Coach", back_populates="branch", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Branch {self.id} {self.name}>"
