import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # Telegram
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_admin_ids: list[int] = None

    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://localhost/coaching_management")
    database_echo: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"

    # Redis
    redis_url: Optional[str] = os.getenv("REDIS_URL")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "logs/app.log")

    # Scheduler
    scheduler_timezone: str = os.getenv("SCHEDULER_TIMEZONE", "Asia/Tashkent")
    auto_report_generation_time: str = os.getenv("AUTO_REPORT_GENERATION_TIME", "23:30")

    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Server
    bot_webhook_path: str = os.getenv("BOT_WEBHOOK_PATH", "/webhook")
    bot_webhook_port: int = int(os.getenv("BOT_WEBHOOK_PORT", "8080"))
    bot_webhook_host: str = os.getenv("BOT_WEBHOOK_HOST", "0.0.0.0")

    def __post_init__(self):
        """Parse telegram admin IDs."""
        admin_ids_str = os.getenv("TELEGRAM_ADMIN_IDS", "")
        if admin_ids_str:
            self.telegram_admin_ids = [int(id.strip()) for id in admin_ids_str.split(",")]
        else:
            self.telegram_admin_ids = []


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()
