#!/bin/sh
set -e

echo "[entrypoint] waiting for the database..."
ATTEMPTS=0
until python -c "
import sys, asyncio, asyncpg
from app.core.config import get_settings
async def ping():
    url = get_settings().async_database_url.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(url)
    await conn.close()
asyncio.run(ping())
" 2>/dev/null; do
    ATTEMPTS=$((ATTEMPTS + 1))
    if [ "$ATTEMPTS" -ge 30 ]; then
        echo "[entrypoint] database did not become reachable in time" >&2
        exit 1
    fi
    sleep 2
done
echo "[entrypoint] database is up"

# Alembic owns the schema. Running this on every start makes deploys
# self-applying and keeps the migration history authoritative.
echo "[entrypoint] applying migrations..."
alembic upgrade head

echo "[entrypoint] starting: $*"
exec "$@"
