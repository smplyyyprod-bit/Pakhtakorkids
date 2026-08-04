import os
import sys

from loguru import logger

from app.core.config import get_settings

settings = get_settings()

log_file = settings.log_file
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logger.remove()
logger.add(
    sys.stderr,
    format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level,
)

logger.add(
    log_file,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level=settings.log_level,
    rotation="500 MB",
    retention="7 days",
)


def get_logger():
    """Get configured logger."""
    return logger
