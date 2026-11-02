from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.hms.domain import Domain


async def record_movement(
    domain: Domain, payload: dict[str, Any], *, confirmed: bool = False
) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("inventory/movements", payload, confirmed)


async def receive(domain: Domain, payload: dict[str, Any], *, confirmed: bool = False) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("inventory/receipts", payload, confirmed)


async def purchase_order(
    domain: Domain, payload: dict[str, Any], *, confirmed: bool = False
) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("inventory/purchase-orders", payload, confirmed)
