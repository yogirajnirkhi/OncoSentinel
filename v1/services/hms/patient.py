from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.hms.domain import Domain


async def register(domain: Domain, payload: dict[str, Any], *, confirmed: bool = False) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("patients", payload, confirmed)


async def start_encounter(
    domain: Domain, payload: dict[str, Any], *, confirmed: bool = False
) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("encounters", payload, confirmed)


async def append_record(domain: Domain, payload: dict[str, Any], *, confirmed: bool = False) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("medical-records", payload, confirmed)
