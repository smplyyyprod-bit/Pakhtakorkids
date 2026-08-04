"""Alembic environment configuration."""

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import asyncio
from app.domain.models import Base
from app.core.config import get_settings

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata
settings = get_settings()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.database_url.replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
