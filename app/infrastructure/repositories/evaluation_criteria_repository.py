from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import EvaluationCriteria, CriterionValue
from app.infrastructure.repositories.base import BaseRepository


class EvaluationCriteriaRepository(BaseRepository[EvaluationCriteria]):
    """Repository for EvaluationCriteria model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, EvaluationCriteria)

    async def get_by_name(self, name: str) -> Optional[EvaluationCriteria]:
        """Get criterion by name."""
        stmt = select(EvaluationCriteria).where(EvaluationCriteria.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active_criteria(self) -> list[EvaluationCriteria]:
        """Get all active evaluation criteria."""
        stmt = (
            select(EvaluationCriteria)
            .where(EvaluationCriteria.is_active == True)
            .order_by(EvaluationCriteria.order)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_with_values(self, criterion_id: int) -> Optional[EvaluationCriteria]:
        """Get criterion with all values."""
        stmt = (
            select(EvaluationCriteria)
            .where(EvaluationCriteria.id == criterion_id)
            .options(selectinload(EvaluationCriteria.criterion_values))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_with_values(self) -> list[EvaluationCriteria]:
        """Get all criteria with values."""
        stmt = (
            select(EvaluationCriteria)
            .options(selectinload(EvaluationCriteria.criterion_values))
            .order_by(EvaluationCriteria.order)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
