from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

AsyncHook = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class HMSBindings:
    """Host adapters must be explicit: no guessed principal/session/audit contracts."""

    session_dependency: Callable[..., Any]
    get_current_user: Callable[..., Any]
    require_roles: Callable[..., Any]
    actor: Callable[[Any], tuple[str, list[str]]]
    audit_write: AsyncHook
    audit_query: AsyncHook
    pharmacy_safety: AsyncHook | None = None
    imaging_quality: AsyncHook | None = None
    ai_evidence: AsyncHook | None = None

    async def audit(self, session: AsyncSession, **event: Any) -> None:
        # Host callback MUST flush, not commit, and use this same session.
        await self.audit_write(session=session, service_name="hms", **event)
