"""Database bootstrap: seeding only.

Schema creation is owned by Alembic (`alembic upgrade head`), not by
`Base.metadata.create_all`. Keeping the two separate avoids the classic drift
where the running schema and the migration history disagree.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logger import get_logger
from app.domain.models import Branch, EvaluationCriteria, Role, User
from app.infrastructure.database.session import SessionLocal

logger = get_logger()
settings = get_settings()


# Criteria seeded on first boot. These describe the *configurable* extras;
# the fixed columns on daily_reports (attendance, uniform, hours) are not
# duplicated here.
DEFAULT_CRITERIA: list[dict[str, str | int]] = [
    {
        "name": "discipline_note",
        "description": "Дисциплинарная отметка",
        "field_type": "select",
        "order": 10,
    },
    {
        "name": "equipment_check",
        "description": "Проверка инвентаря",
        "field_type": "boolean",
        "order": 20,
    },
]


async def seed_branches(session: AsyncSession) -> None:
    """Create the default branch if no branches exist at all."""
    existing = await session.execute(select(Branch).limit(1))
    if existing.scalars().first() is not None:
        return

    session.add(
        Branch(
            name="Главное отделение",
            description="Основное отделение",
            is_active=True,
        )
    )
    await session.commit()
    logger.info("Seeded default branch")


async def seed_privileged_users(session: AsyncSession) -> None:
    """Promote the Telegram IDs listed in .env to their configured roles.

    Runs on every boot so that adding an ID to .env and restarting is enough
    to grant access - no manual SQL required.
    """
    wanted: dict[int, Role] = {}
    for telegram_id in settings.telegram_manager_ids:
        wanted[telegram_id] = Role.MANAGER
    # Admin wins if an ID appears in both lists.
    for telegram_id in settings.telegram_admin_ids:
        wanted[telegram_id] = Role.ADMIN

    if not wanted:
        logger.warning(
            "No TELEGRAM_ADMIN_IDS or TELEGRAM_MANAGER_IDS configured - "
            "nobody will be able to use the bot until one is set"
        )
        return

    result = await session.execute(
        select(User).where(User.telegram_id.in_(wanted.keys()))
    )
    existing = {user.telegram_id: user for user in result.scalars().all()}

    changed = 0
    for telegram_id, role in wanted.items():
        user = existing.get(telegram_id)
        if user is None:
            session.add(
                User(
                    telegram_id=telegram_id,
                    full_name=f"User {telegram_id}",
                    role=role,
                    is_active=True,
                )
            )
            changed += 1
        elif user.role is not role or not user.is_active:
            user.role = role
            user.is_active = True
            changed += 1

    if changed:
        await session.commit()
        logger.info("Seeded/updated {} privileged user(s)", changed)


async def seed_criteria(session: AsyncSession) -> None:
    """Insert the default evaluation criteria, skipping any already present."""
    result = await session.execute(select(EvaluationCriteria.name))
    known = set(result.scalars().all())

    added = 0
    for spec in DEFAULT_CRITERIA:
        if spec["name"] in known:
            continue
        session.add(EvaluationCriteria(is_active=True, **spec))
        added += 1

    if added:
        await session.commit()
        logger.info("Seeded {} evaluation criteria", added)


async def init_db() -> None:
    """Run all seeders. Safe to call on every startup."""
    async with SessionLocal() as session:
        await seed_branches(session)
        await seed_privileged_users(session)
        await seed_criteria(session)
    logger.info("Database seeding complete")
