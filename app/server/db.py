"""Lakebase (PostgreSQL) connection pool using native user/password from env or secret scope."""

import asyncpg
from typing import Optional

from .config import PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD, has_lakebase_credentials


class DatabasePool:
    def __init__(self) -> None:
        self._pool: Optional[asyncpg.Pool] = None

    async def get_pool(self) -> Optional[asyncpg.Pool]:
        if not has_lakebase_credentials():
            return None
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=PGHOST,
                port=PGPORT,
                database=PGDATABASE,
                user=PGUSER,
                password=PGPASSWORD,
                ssl="require",
                min_size=1,
                max_size=6,
                command_timeout=60,
            )
        return self._pool

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None


db = DatabasePool()
