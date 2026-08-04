"""Audit logging.

Every mutation routes through here so "every modification should be logged" is
a property of the service layer rather than something each call site remembers
to do.
"""

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.domain.models import AuditLog

logger = get_logger()


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: int | None = None,
        user_id: int | None = None,
        changes: dict[str, Any] | None = None,
    ) -> None:
        """Stage an audit row. Committed with the surrounding unit of work."""
        payload: str | None = None
        if changes:
            payload = json.dumps(changes, ensure_ascii=False, default=str)

        self.session.add(
            AuditLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                changes=payload,
            )
        )
        logger.debug("audit: {} {}#{}", action, entity_type, entity_id)
