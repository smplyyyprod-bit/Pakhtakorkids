"""Generic CRUD base for the repository layer."""

from typing import Generic, Sequence, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Shared CRUD operations.

    Repositories do not commit - the unit of work is owned by the caller (the
    middleware-provided session), so a handler can make several repository
    calls and still commit them atomically.
    """

    def __init__(self, session: AsyncSession, model: Type[T]) -> None:
        self.session = session
        self.model = model

    async def add(self, obj: T) -> T:
        """Stage a new object and flush so its primary key is populated."""
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_by_id(self, obj_id: int) -> T | None:
        return await self.session.get(self.model, obj_id)

    async def list_all(self, skip: int = 0, limit: int = 100) -> Sequence[T]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete(self, obj_id: int) -> bool:
        obj = await self.get_by_id(obj_id)
        if obj is None:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    async def count(self) -> int:
        """Count rows in the database rather than by loading them."""
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())
