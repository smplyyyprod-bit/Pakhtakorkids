from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import Coach
from app.infrastructure.repositories import CoachRepository

logger = get_logger()


class CoachService:
    """Service for coach operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = CoachRepository(session)

    async def create_coach(
        self,
        unique_id: str,
        full_name: str,
        position: str,
        team: str,
        branch_id: int,
    ) -> Coach:
        """Create a new coach."""
        logger.info(f"Creating coach: {full_name} ({unique_id})")
        coach = Coach(
            unique_id=unique_id,
            full_name=full_name,
            position=position,
            team=team,
            branch_id=branch_id,
            is_active=True,
        )
        return await self.repository.create(coach)

    async def get_coach(self, coach_id: int) -> Optional[Coach]:
        """Get coach by ID."""
        return await self.repository.get_by_id(coach_id)

    async def get_coach_by_unique_id(self, unique_id: str) -> Optional[Coach]:
        """Get coach by unique ID."""
        return await self.repository.get_by_unique_id(unique_id)

    async def get_branch_coaches(self, branch_id: int) -> list[Coach]:
        """Get coaches in a branch."""
        return await self.repository.get_by_branch(branch_id)

    async def get_active_branch_coaches(self, branch_id: int) -> list[Coach]:
        """Get active coaches in a branch."""
        return await self.repository.get_active_by_branch(branch_id)

    async def get_all_coaches(self) -> list[Coach]:
        """Get all coaches."""
        return await self.repository.get_active_coaches()

    async def update_coach(
        self,
        coach_id: int,
        full_name: str = None,
        position: str = None,
        team: str = None,
        branch_id: int = None,
    ) -> Optional[Coach]:
        """Update coach information."""
        coach = await self.repository.get_by_id(coach_id)
        if coach:
            if full_name:
                coach.full_name = full_name
            if position:
                coach.position = position
            if team:
                coach.team = team
            if branch_id:
                coach.branch_id = branch_id
            logger.info(f"Updating coach: {coach_id}")
            return await self.repository.update(coach)
        return None

    async def deactivate_coach(self, coach_id: int) -> Optional[Coach]:
        """Deactivate a coach."""
        coach = await self.repository.get_by_id(coach_id)
        if coach:
            coach.is_active = False
            logger.info(f"Deactivating coach: {coach_id}")
            return await self.repository.update(coach)
        return None

    async def activate_coach(self, coach_id: int) -> Optional[Coach]:
        """Activate a coach."""
        coach = await self.repository.get_by_id(coach_id)
        if coach:
            coach.is_active = True
            logger.info(f"Activating coach: {coach_id}")
            return await self.repository.update(coach)
        return None

    async def move_coach_to_branch(self, coach_id: int, branch_id: int) -> Optional[Coach]:
        """Move coach to another branch."""
        coach = await self.repository.get_by_id(coach_id)
        if coach:
            coach.branch_id = branch_id
            logger.info(f"Moving coach {coach_id} to branch {branch_id}")
            return await self.repository.update(coach)
        return None

    async def count_coaches(self) -> int:
        """Count total coaches."""
        return await self.repository.count()
