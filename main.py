"""Main entry point for the application."""

import asyncio
import sys

from app.core.logger import get_logger
from app.presentation.telegram.bot import run_bot

logger = get_logger()


async def main() -> None:
    """Main function."""
    try:
        logger.info("Application starting")
        await run_bot()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
