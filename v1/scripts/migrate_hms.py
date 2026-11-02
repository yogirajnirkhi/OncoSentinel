"""Explicit one-time standalone migration helper; prefer the host's Alembic chain in production."""

from __future__ import annotations
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    from services.hms.migration import upgrade

    url = os.environ["DATABASE_URL"]
    if not url.startswith("postgresql+asyncpg://"):
        raise RuntimeError("Production migrations require postgresql+asyncpg://")
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.run_sync(upgrade)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
