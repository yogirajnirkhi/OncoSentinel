"""Explicit synthetic development host; never copy into the real services package.
Only localhost access; pass DEMO_TOKEN via environment. No default credentials.
SQLite and synthetic audit model are demo/test-only compatibility shims.
"""

from __future__ import annotations

import os
import secrets
import sys
import types
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import JSON, DateTime, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


try:
    from services.db.models import Base
    from services.core.exceptions import OncoSentinelError
except ImportError:
    class Base(DeclarativeBase):
        pass

    class OncoSentinelError(Exception):
        pass

    def install_shims() -> None:
        # The real repository supplies these; the development harness is visibly separate.
        for name in ["services.db", "services.core"]:
            if name not in sys.modules:
                module = types.ModuleType(name)
                module.__path__ = []
                sys.modules[name] = module
        db = types.ModuleType("services.db.models")
        db.Base = Base
        errors = types.ModuleType("services.core.exceptions")
        errors.OncoSentinelError = OncoSentinelError
        sys.modules["services.db.models"] = db
        sys.modules["services.core.exceptions"] = errors

    install_shims()
from services.hms.bindings import HMSBindings
from services.hms.routes import mount_hms


class DemoAudit(Base):
    __tablename__ = "demo_audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_name: Mapped[str] = mapped_column(String)
    request_id: Mapped[str] = mapped_column(String, index=True)
    actor_id: Mapped[str] = mapped_column(String)
    actor_role: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    trace_id: Mapped[str] = mapped_column(String)
    details: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


async def audit_write(session: AsyncSession, **event: Any) -> None:
    session.add(DemoAudit(**event))
    await session.flush()


async def audit_query(
    session: AsyncSession,
    request_id: str | None = None,
    limit: int = 50,
    service_name: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    query = select(DemoAudit)
    if service_name:
        query = query.where(DemoAudit.service_name == service_name)
    if request_id:
        query = query.where(DemoAudit.request_id == request_id)
    actor_id = kwargs.get("actor_id")
    if actor_id:
        query = query.where(DemoAudit.actor == actor_id)
    rows = (await session.execute(query.order_by(DemoAudit.id.desc()).limit(limit))).scalars().all()
    return {
        "items": [
            {
                c.name: str(getattr(r, c.name))
                if isinstance(getattr(r, c.name), datetime)
                else getattr(r, c.name)
                for c in r.__table__.columns
            }
            for r in rows
        ]
    }


def make_app(database_url: str | None = None, token: str | None = None) -> FastAPI:
    url = database_url or os.environ.get(
        "HMS_DEMO_DATABASE_URL", "sqlite+aiosqlite:///./hms-demo.sqlite3"
    )
    expected = token or os.environ.get("DEMO_TOKEN")
    if not expected or len(expected) < 24:
        raise RuntimeError(
            "Set DEMO_TOKEN to at least 24 random characters; no default credential exists"
        )
    engine = create_async_engine(url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def session_dependency() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    bearer = HTTPBearer()

    async def current_user(
        credentials: HTTPAuthorizationCredentials = Depends(bearer),
    ) -> dict[str, Any]:
        if not secrets.compare_digest(credentials.credentials, expected):
            raise HTTPException(401, "Invalid development token")
        # Not JWT auth. Clearly labelled standalone demo principal only.
        from services.hms.config import load_config

        return {"id": "development-operator", "roles": load_config()["roles"]}

    def require_roles(*roles: str) -> Any:
        async def guard(principal: dict[str, Any] = Depends(current_user)) -> None:
            if not set(roles).intersection(principal["roles"]):
                raise HTTPException(403, "Role not allowed")

        return guard

    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        import services.hms.models  # noqa: F401
        from services.hms.migration import upgrade

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.run_sync(upgrade)
        yield
        await engine.dispose()

    app = FastAPI(
        title="OncoSentinel HMS · DEVELOPMENT HARNESS", version="2.0.0", lifespan=lifespan
    )
    bindings = HMSBindings(
        session_dependency,
        current_user,
        require_roles,
        lambda p: (p["id"], p["roles"]),
        audit_write,
        audit_query,
    )
    mount_hms(app, bindings)
    app.state.hms_bindings = bindings
    app.state.hms_engine = engine
    app.state.hms_sessions = sessions

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": "2.0.0",
            "environment": "development",
            "platform_phase": "synthetic harness; not clinical deployment",
        }

    return app


def factory() -> FastAPI:
    return make_app()
