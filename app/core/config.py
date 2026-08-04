"""Application settings, loaded once from the environment."""

import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _parse_id_list(raw: str | None) -> list[int]:
    """Parse a comma-separated list of Telegram IDs, ignoring junk entries."""
    if not raw:
        return []
    ids: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.append(int(chunk))
        except ValueError:
            # A typo in .env should not take the whole bot down.
            continue
    return ids


def _parse_bool(raw: str | None, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Immutable view of the environment."""

    telegram_bot_token: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", "")
    )
    telegram_admin_ids: list[int] = field(
        default_factory=lambda: _parse_id_list(os.getenv("TELEGRAM_ADMIN_IDS"))
    )
    telegram_manager_ids: list[int] = field(
        default_factory=lambda: _parse_id_list(os.getenv("TELEGRAM_MANAGER_IDS"))
    )

    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql://localhost/coaching_management"
        )
    )
    database_echo: bool = field(
        default_factory=lambda: _parse_bool(os.getenv("DATABASE_ECHO"))
    )

    redis_url: str | None = field(default_factory=lambda: os.getenv("REDIS_URL"))

    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: str = field(
        default_factory=lambda: os.getenv("LOG_FILE", "logs/app.log")
    )

    scheduler_timezone: str = field(
        default_factory=lambda: os.getenv("SCHEDULER_TIMEZONE", "Asia/Tashkent")
    )
    auto_report_generation_time: str = field(
        default_factory=lambda: os.getenv("AUTO_REPORT_GENERATION_TIME", "23:30")
    )
    incomplete_report_reminder_time: str = field(
        default_factory=lambda: os.getenv("INCOMPLETE_REPORT_REMINDER_TIME", "19:00")
    )

    environment: str = field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )
    debug: bool = field(default_factory=lambda: _parse_bool(os.getenv("DEBUG")))

    @property
    def async_database_url(self) -> str:
        """SQLAlchemy URL using the asyncpg driver."""
        url = self.database_url
        if url.startswith("postgresql+"):
            return url
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)

    @property
    def sync_database_url(self) -> str:
        """SQLAlchemy URL using the sync psycopg2 driver, for Alembic."""
        url = self.database_url
        if url.startswith("postgresql+"):
            scheme, _, rest = url.partition("://")
            return f"postgresql://{rest}"
        return url

    def parsed_time(self, value: str, fallback: tuple[int, int]) -> tuple[int, int]:
        """Parse an 'HH:MM' setting into (hour, minute), falling back on junk."""
        try:
            hour_str, _, minute_str = value.partition(":")
            hour, minute = int(hour_str), int(minute_str)
        except ValueError:
            return fallback
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return fallback
        return hour, minute


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings singleton."""
    return Settings()
