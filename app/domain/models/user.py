from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, BigInteger, Enum, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.domain.models.branch import Branch


class Role(PyEnum):
    """User roles in the system."""

    ADMIN = "admin"
    MANAGER = "manager"
    COACH = "coach"


class User(Base, TimestampMixin):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # BigInteger: Telegram user IDs already exceed the 32-bit signed range.
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    branch_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("branches.id"))

    branch: Mapped["Branch | None"] = relationship("Branch", back_populates="users")

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def is_manager(self) -> bool:
        return self.role == Role.MANAGER

    def is_coach(self) -> bool:
        return self.role == Role.COACH

    def __repr__(self) -> str:
        return f"<User {self.telegram_id} {self.full_name}>"
