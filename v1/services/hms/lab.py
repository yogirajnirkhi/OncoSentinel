from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.hms.domain import Domain


async def order(domain: Domain, payload: dict[str, Any], *, confirmed: bool = False) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("lab/orders", payload, confirmed)


async def verify(domain: Domain, payload: dict[str, Any], *, confirmed: bool = False) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("lab/results", payload, confirmed)
