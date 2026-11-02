from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.hms.bindings import HMSBindings


async def record(
    bindings: HMSBindings,
    session: AsyncSession,
    *,
    request_id: str,
    actor_id: str,
    actor_role: str,
    action: str,
    details: dict[str, Any],
) -> None:
    """Same-transaction audit adapter; the host implements INSERT-only AuditEvent persistence."""
    await bindings.audit(
        session,
        request_id=request_id,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        trace_id=request_id,
        details=details,
    )
