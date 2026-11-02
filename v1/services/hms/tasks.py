from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import func, select

from services.hms.domain import Domain, lock
from services.hms.exceptions import HMSError
from services.hms.models import MODELS, OperationReceipt

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.ext.asyncio import AsyncSession

    from services.hms.bindings import HMSBindings

JOB_NAMES = (
    "billing_run",
    "claim_submission",
    "low_stock_reorder",
    "expiry_sweep",
    "critical_result_notification",
    "invoice_reminder",
    "financial_period_close",
)


async def review_job(
    name: str, run_key: str, session: AsyncSession, bindings: HMSBindings
) -> dict[str, Any]:
    """Jobs surface review work, never autonomously submit claims, prescribe or close periods."""
    if name not in JOB_NAMES:
        raise HMSError("Unknown background job")
    scope = "worker:" + name + ":" + run_key
    await lock(session, scope)
    previous = await session.get(OperationReceipt, scope)
    if previous:
        return previous.response
    request_id = str(uuid4())
    domain = Domain(session, bindings, "hms-review-worker", [], request_id)
    records = []
    if name == "low_stock_reorder":
        model = MODELS["inventory/items"]
        for item in (await session.execute(select(model))).scalars():
            if await domain.stock(item.id) <= item.reorder_point:
                records.append({"id": str(item.id), "action": "review_reorder"})
    elif name == "expiry_sweep":
        # Horizon is config-driven; expired stock is never dispensed.
        from services.hms.config import load_config

        horizon = int(load_config()["expiry_alert_days"])
        model = MODELS["inventory/movements"]
        rows = (
            await session.execute(
                select(model.item_id, model.lot, model.expiry, func.sum(model.quantity))
                .group_by(model.item_id, model.lot, model.expiry)
                .having(func.sum(model.quantity) > 0)
                .where(model.expiry <= date.today() + timedelta(days=horizon))
            )
        ).all()
        records = [{"id": str(r.item_id), "lot": r.lot, "action": "review_expiry"} for r in rows]
    elif name == "critical_result_notification":
        model = MODELS["alerts"]
        rows = (
            (await session.execute(select(model).where(model.severity == "critical")))
            .scalars()
            .all()
        )
        records = [{"id": str(r.id), "action": "acknowledgement_required"} for r in rows]
    elif name in ["billing_run", "invoice_reminder"]:
        model = MODELS["billing/invoices"]
        for invoice in (await session.execute(select(model))).scalars():
            if await domain.balance(invoice) > 0:
                records.append({"id": str(invoice.id), "action": "review_balance"})
    elif name == "claim_submission":
        model = MODELS["billing/claims"]
        records = [
            {"id": str(r.id), "action": "manual_delivery_required"}
            for r in (await session.execute(select(model))).scalars()
        ]
    elif name == "financial_period_close":
        records = [{"action": "human_period_close_required"}]
    result = {"job": name, "request_id": request_id, "status": "review_required", "items": records}
    await bindings.audit(
        session,
        request_id=request_id,
        actor_id=domain.actor,
        actor_role="SYSTEM_REVIEW",
        action="task:" + name,
        trace_id=request_id,
        details={"count": len(records)},
    )
    session.add(OperationReceipt(key=scope, fingerprint=name, response=result))
    await session.commit()
    return result


def register_tasks(
    celery_app: Any, session_context: Callable[..., Any], bindings: HMSBindings
) -> None:
    """Call from the existing worker startup. Factory must create/dispose an engine per loop.
    Do not reuse a request-loop asyncpg engine across asyncio.run() calls.
    """

    def build(name: str) -> Any:
        def task(run_key: str) -> dict[str, Any]:
            async def execute() -> dict[str, Any]:
                async with session_context() as session:
                    return await review_job(name, run_key, session, bindings)

            return asyncio.run(execute())

        task.__name__ = name
        return celery_app.task(name="hms." + name)(task)

    for name in JOB_NAMES:
        build(name)
