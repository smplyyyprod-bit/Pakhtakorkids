from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import Branch
from app.infrastructure.repositories import BranchRepository

logger = get_logger()


class BranchService:
    """Service for branch operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = BranchRepository(session)

    async def create_branch(self, name: str, description: str = "", address: str = "") -> Branch:
        """Create a new branch."""
        logger.info(f"Creating branch: {name}")
        branch = Branch(
            name=name,
            description=description,
            address=address,
            is_active=True,
        )
        return await self.repository.create(branch)

    async def get_branch(self, branch_id: int) -> Optional[Branch]:
        """Get branch by ID."""
        return await self.repository.get_by_id(branch_id)

    async def get_branch_by_name(self, name: str) -> Optional[Branch]:
        """Get branch by name."""
        return await self.repository.get_by_name(name)

    async def get_all_branches(self) -> list[Branch]:
        """Get all branches."""
        return await self.repository.get_active_branches()

    async def get_branch_with_coaches(self, branch_id: int) -> Optional[Branch]:
        """Get branch with all coaches."""
        return await self.repository.get_with_coaches(branch_id)

    async def update_branch(
        self, branch_id: int, name: str = None, description: str = None, address: str = None
    ) -> Optional[Branch]:
        """Update branch information."""
        branch = await self.repository.get_by_id(branch_id)
        if branch:
            if name:
                branch.name = name
            if description is not None:
                branch.description = description
            if address is not None:
                branch.address = address
            logger.info(f"Updating branch: {branch_id}")
            return await self.repository.update(branch)
        return None

    async def deactivate_branch(self, branch_id: int) -> Optional[Branch]:
        """Deactivate a branch."""
        branch = await self.repository.get_by_id(branch_id)
        if branch:
            branch.is_active = False
            logger.info(f"Deactivating branch: {branch_id}")
            return await self.repository.update(branch)
        return None

    async def count_branches(self) -> int:
        """Count total branches."""
        return await self.repository.count()
