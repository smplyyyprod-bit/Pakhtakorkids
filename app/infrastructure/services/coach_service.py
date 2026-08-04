"""Coach management."""

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import Coach
from app.infrastructure.repositories import CoachRepository
from app.infrastructure.services.audit_service import AuditService

logger = get_logger()


class CoachService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = CoachRepository(session)
        self.audit = AuditService(session)

    async def get_coach(self, coach_id: int) -> Coach | None:
        return await self.repository.get_with_branch(coach_id)

    async def list_by_branch(
        self, branch_id: int, active_only: bool = True
    ) -> Sequence[Coach]:
        return await self.repository.list_by_branch(branch_id, active_only)

    async def list_all(self, active_only: bool = True) -> Sequence[Coach]:
        return await self.repository.list_all(active_only, with_branch=True)

    async def count_active(self, branch_id: int | None = None) -> int:
        return await self.repository.count_active(branch_id)

    async def create_coach(
        self,
        *,
        unique_id: str,
        full_name: str,
        position: str,
        team: str,
        branch_id: int,
        actor_id: int | None = None,
    ) -> Coach:
        coach = Coach(
            unique_id=unique_id,
            full_name=full_name,
            position=position,
            team=team,
            branch_id=branch_id,
            is_active=True,
        )
        await self.repository.add(coach)
        await self.audit.record(
            action="coach.created",
            entity_type="coach",
            entity_id=coach.id,
            user_id=actor_id,
            changes={"unique_id": unique_id, "full_name": full_name},
        )
        await self.session.commit()
        return coach

    async def update_coach(
        self,
        coach_id: int,
        *,
        full_name: str | None = None,
        position: str | None = None,
        team: str | None = None,
        actor_id: int | None = None,
    ) -> Coach | None:
        coach = await self.repository.get_by_id(coach_id)
        if coach is None:
            return None

        changes: dict[str, object] = {}
        if full_name is not None:
            changes["full_name"] = {"from": coach.full_name, "to": full_name}
            coach.full_name = full_name
        if position is not None:
            changes["position"] = position
            coach.position = position
        if team is not None:
            changes["team"] = team
            coach.team = team

        await self.audit.record(
            action="coach.updated",
            entity_type="coach",
            entity_id=coach.id,
            user_id=actor_id,
            changes=changes,
        )
        await self.session.commit()
        return coach

    async def move_to_branch(
        self, coach_id: int, branch_id: int, actor_id: int | None = None
    ) -> Coach | None:
        """Reassign a coach.

        Only future reports follow the coach - historical rows keep the branch
        they were filed under, so past branch statistics stay accurate.
        """
        coach = await self.repository.get_by_id(coach_id)
        if coach is None:
            return None

        previous = coach.branch_id
        coach.branch_id = branch_id
        await self.audit.record(
            action="coach.moved",
            entity_type="coach",
            entity_id=coach.id,
            user_id=actor_id,
            changes={"branch": {"from": previous, "to": branch_id}},
        )
        await self.session.commit()
        return coach

    async def set_active(
        self, coach_id: int, active: bool, actor_id: int | None = None
    ) -> Coach | None:
        """Deactivate rather than delete, to preserve report history."""
        coach = await self.repository.get_by_id(coach_id)
        if coach is None:
            return None
        coach.is_active = active
        await self.audit.record(
            action="coach.activated" if active else "coach.deactivated",
            entity_type="coach",
            entity_id=coach.id,
            user_id=actor_id,
        )
        await self.session.commit()
        return coach
