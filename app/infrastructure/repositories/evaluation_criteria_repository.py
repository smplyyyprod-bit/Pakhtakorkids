"""Evaluation criteria queries.

Criteria are rows, not code. Adding a new one is an INSERT, which is what lets
the evaluation form grow without touching business logic.
"""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import EvaluationCriteria
from app.infrastructure.repositories.base import BaseRepository


class EvaluationCriteriaRepository(BaseRepository[EvaluationCriteria]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EvaluationCriteria)

    async def get_by_name(self, name: str) -> EvaluationCriteria | None:
        stmt = select(EvaluationCriteria).where(EvaluationCriteria.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_active(self, with_values: bool = True) -> Sequence[EvaluationCriteria]:
        stmt = select(EvaluationCriteria).where(EvaluationCriteria.is_active.is_(True))
        if with_values:
            stmt = stmt.options(selectinload(EvaluationCriteria.criterion_values))
        stmt = stmt.order_by(EvaluationCriteria.order, EvaluationCriteria.id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_all_with_values(self) -> Sequence[EvaluationCriteria]:
        stmt = (
            select(EvaluationCriteria)
            .options(selectinload(EvaluationCriteria.criterion_values))
            .order_by(EvaluationCriteria.order, EvaluationCriteria.id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
