from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.hms.domain import Domain


async def book(domain: Domain, payload: dict[str, Any], *, confirmed: bool = False) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("scheduling/appointments", payload, confirmed)


async def assign_shift(domain: Domain, payload: dict[str, Any], *, confirmed: bool = False) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("scheduling/shifts", payload, confirmed)


async def request_swap(domain: Domain, payload: dict[str, Any], *, confirmed: bool = False) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("scheduling/swaps", payload, confirmed)
