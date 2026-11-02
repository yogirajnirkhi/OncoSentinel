from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.hms.domain import Domain


async def issue_invoice(domain: Domain, payload: dict[str, Any], *, confirmed: bool = False) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("billing/invoices", payload, confirmed)


async def record_payment(
    domain: Domain, payload: dict[str, Any], *, confirmed: bool = False
) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("billing/payments", payload, confirmed)


async def record_claim(domain: Domain, payload: dict[str, Any], *, confirmed: bool = False) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("billing/claims", payload, confirmed)


async def adjust_invoice(
    domain: Domain, payload: dict[str, Any], *, confirmed: bool = False
) -> Any:
    """Transaction/audit ownership stays with the gateway request boundary."""
    return await domain.create("billing/adjustments", payload, confirmed)
