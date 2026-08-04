from typing import TypeVar, Generic, List, Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Base repository class for CRUD operations."""

    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def create(self, obj: T) -> T:
        """Create a new object."""
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, id: int) -> Optional[T]:
        """Get object by ID."""
        return await self.session.get(self.model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all objects with pagination."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(self, obj: T) -> T:
        """Update an object."""
        await self.session.merge(obj)
        await self.session.commit()
        return obj

    async def delete(self, id: int) -> bool:
        """Delete an object by ID."""
        obj = await self.get_by_id(id)
        if obj:
            await self.session.delete(obj)
            await self.session.commit()
            return True
        return False

    async def count(self) -> int:
        """Count total objects."""
        stmt = select(self.model)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
