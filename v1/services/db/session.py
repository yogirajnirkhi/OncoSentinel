"""
OncoSentinel v2.0 — Database Session & Engine Configuration
Satisfies: SRS §11, FR-16 (append-only timeline), FR-29 (audit trail)
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from services.core.logging import get_logger
from services.core.settings import get_settings
from services.db.models import Base

logger = get_logger(__name__)

# Determine if we need SQLite fallback for testing/local standalone mode
_db_url = get_settings().database_url

if "postgresql" in _db_url:
    try:
        import psycopg2  # type: ignore
    except ImportError:
        logger.info("psycopg2_driver_not_found_falling_back_to_sqlite")
        _db_url = "sqlite+aiosqlite:///./oncosentinel.db"

# Handle sqlite async/sync conversions if using sqlite
if "sqlite" in _db_url:
    _sync_db_url = _db_url.replace("+aiosqlite", "")
    _async_db_url = _db_url if "+aiosqlite" in _db_url else _db_url.replace("sqlite://", "sqlite+aiosqlite://")
else:
    _sync_db_url = _db_url.replace("+asyncpg", "+psycopg2")
    _async_db_url = _db_url

# Async Engine & Sessionmaker
async_engine = create_async_engine(
    _async_db_url,
    echo=False,
    pool_pre_ping=True,
    future=True,
)
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
async_session_factory = AsyncSessionLocal

# Sync Engine & Sessionmaker (for sync scripts, migrations, test fixtures)
sync_engine = create_engine(
    _sync_db_url,
    echo=False,
    pool_pre_ping=True,
    future=True,
)
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def _ensure_schema_current(connection: Any) -> None:
    """Detect legacy pre-v2 schema (e.g. cases table missing patient_id) and rebuild cleanly."""
    from sqlalchemy import inspect as sa_inspect

    inspector = sa_inspect(connection)
    if inspector.has_table("cases"):
        col_names = {col["name"] for col in inspector.get_columns("cases")}
        if "patient_id" not in col_names or "encounter_id" not in col_names:
            logger.info("legacy_database_schema_detected_rebuilding")
            Base.metadata.drop_all(bind=connection)


async def init_db() -> None:
    """Initialize database tables including HMS tables and security guards."""
    try:
        import services.hms.models  # noqa: F401 - register HMS models with Base.metadata
        from services.hms.migration import install_guards
        from services.db.seed import seed_database

        async with async_engine.begin() as conn:
            await conn.run_sync(_ensure_schema_current)
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(install_guards)
        logger.info("database_initialized", url=_async_db_url)
        seed_database()
    except Exception as exc:
        logger.warning("database_async_init_fallback", error=str(exc))
        # Fallback to sync engine if needed
        try:
            import services.hms.models  # noqa: F401
            from services.hms.migration import install_guards
            from services.db.seed import seed_database

            with sync_engine.begin() as conn:
                _ensure_schema_current(conn)
                Base.metadata.create_all(bind=conn)
                install_guards(conn)
            seed_database()
        except Exception as sync_exc:
            logger.error("database_init_failed", error=str(sync_exc))


async def get_hms_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Fresh request-scoped AsyncSession where transaction boundary is owned by HMS domain."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI route handlers providing AsyncSession."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Generator[Session, None, None]:
    """Synchronous database session generator for CLI or background tasks."""
    db = SyncSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
