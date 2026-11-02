from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.hms.domain import Domain


async def order(domain: Domain, payload: dict[str, Any], *, confirmed: bool = False) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("radiology/orders", payload, confirmed)


async def sign_report(domain: Domain, payload: dict[str, Any], *, confirmed: bool = False) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("radiology/reports", payload, confirmed)
