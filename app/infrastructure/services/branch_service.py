"""Branch management."""

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import Branch
from app.infrastructure.repositories import BranchRepository, CoachRepository
from app.infrastructure.services.audit_service import AuditService

logger = get_logger()


class BranchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = BranchRepository(session)
        self.coaches = CoachRepository(session)
        self.audit = AuditService(session)

    async def list_branches(self) -> Sequence[Branch]:
        return await self.repository.list_active()

    async def get_branch(self, branch_id: int) -> Branch | None:
        return await self.repository.get_by_id(branch_id)

    async def create_branch(
        self,
        *,
        name: str,
        description: str = "",
        address: str = "",
        actor_id: int | None = None,
    ) -> Branch:
        branch = Branch(
            name=name,
            description=description or None,
            address=address or None,
            is_active=True,
        )
        await self.repository.add(branch)
        await self.audit.record(
            action="branch.created",
            entity_type="branch",
            entity_id=branch.id,
            user_id=actor_id,
            changes={"name": name},
        )
        await self.session.commit()
        return branch

    async def update_branch(
        self,
        branch_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        address: str | None = None,
        actor_id: int | None = None,
    ) -> Branch | None:
        branch = await self.repository.get_by_id(branch_id)
        if branch is None:
            return None

        changes: dict[str, object] = {}
        if name is not None:
            changes["name"] = {"from": branch.name, "to": name}
            branch.name = name
        if description is not None:
            branch.description = description
            changes["description"] = description
        if address is not None:
            branch.address = address
            changes["address"] = address

        await self.audit.record(
            action="branch.updated",
            entity_type="branch",
            entity_id=branch.id,
            user_id=actor_id,
            changes=changes,
        )
        await self.session.commit()
        return branch

    async def set_active(
        self, branch_id: int, active: bool, actor_id: int | None = None
    ) -> Branch | None:
        """Deactivate rather than delete.

        Branches are referenced by historical daily reports; removing the row
        would take the history with it.
        """
        branch = await self.repository.get_by_id(branch_id)
        if branch is None:
            return None
        branch.is_active = active
        await self.audit.record(
            action="branch.activated" if active else "branch.deactivated",
            entity_type="branch",
            entity_id=branch.id,
            user_id=actor_id,
        )
        await self.session.commit()
        return branch
