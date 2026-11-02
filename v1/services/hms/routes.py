from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from services.hms.config import load_config
from services.hms.domain import Domain, lock, public
from services.hms.exceptions import HMSError
from services.hms.models import MODELS, OperationReceipt
from services.hms.schemas import CREATES, RESPONSES, UPDATES, Page, Query

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from services.hms.bindings import HMSBindings

logger = structlog.get_logger("hms")


def create_router(bindings: HMSBindings) -> APIRouter:
    router = APIRouter(prefix="/api/v2/hms", tags=["HMS"])
    config = load_config()

    async def context(
        request: Request,
        response: Response,
        session: AsyncSession = Depends(bindings.session_dependency),
        principal: Any = Depends(bindings.get_current_user),
    ) -> Domain:
        actor_id, roles = bindings.actor(principal)
        if not actor_id or not roles:
            raise HTTPException(403, "HMS requires an attributed principal")
        supplied = request.headers.get("X-Request-ID")
        try:
            request_id = str(UUID(supplied)) if supplied else str(uuid4())
        except ValueError as exc:
            raise HMSError("X-Request-ID must be a UUID") from exc
        request.state.hms_request_id = request_id
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        return Domain(session, bindings, actor_id, roles, request_id)

    def permitted(roles: list[str]) -> list[Any]:
        return [Depends(bindings.require_roles(*roles))]

    async def run(
        d: Domain,
        request: Request,
        action: str,
        task: Callable[[], Awaitable[Any]],
        payload: Any = None,
        write: bool = False,
    ) -> Any:
        scope = None
        try:
            if write:
                key = request.headers.get("Idempotency-Key", "")
                try:
                    UUID(key)
                except ValueError as exc:
                    raise HMSError("Writes require a UUID Idempotency-Key") from exc
                scope = d.actor + ":" + key
                await lock(d.s, "operation:" + scope)
                encoded = json.dumps(
                    jsonable_encoder(payload), sort_keys=True, separators=(",", ":")
                )
                fingerprint = hashlib.sha256((action + encoded).encode()).hexdigest()
                receipt = await d.s.get(OperationReceipt, scope)
                if receipt:
                    if receipt.fingerprint != fingerprint:
                        raise HMSError("Idempotency key was used for a different request")
                    await d.b.audit(
                        d.s,
                        request_id=d.rid,
                        actor_id=d.actor,
                        actor_role=",".join(d.roles),
                        action="idempotent_replay",
                        trace_id=d.rid,
                        details={"operation": action},
                    )
                    await d.s.commit()
                    return receipt.response
            result = await task()
            result = jsonable_encoder(result)
            # Audit details intentionally contain identifiers, never request bodies or PHI.
            record_id = result.get("id") if isinstance(result, dict) else None
            await d.b.audit(
                d.s,
                request_id=d.rid,
                actor_id=d.actor,
                actor_role=",".join(d.roles),
                action=action,
                trace_id=d.rid,
                details={"record_id": record_id},
            )
            if write and scope:
                d.s.add(OperationReceipt(key=scope, fingerprint=fingerprint, response=result))
            await d.s.commit()
            logger.info("hms_action", action=action, request_id=d.rid, actor_id=d.actor)
            return result
        except Exception as exc:
            await d.s.rollback()
            if isinstance(exc, HMSError | ValidationError | IntegrityError | ValueError):
                code = exc.code if isinstance(exc, HMSError) else "validation_or_integrity"
                message = (
                    exc.message
                    if isinstance(exc, HMSError)
                    else "Payload violates validation or record integrity constraints"
                )
                await d.b.audit(
                    d.s,
                    request_id=d.rid,
                    actor_id=d.actor,
                    actor_role=",".join(d.roles),
                    action="rejected:" + action,
                    trace_id=d.rid,
                    details={"error": code},
                )
                await d.s.commit()
                raise HMSError(message, code) from exc
            logger.error("hms_action_failed", action=action, request_id=d.rid)
            raise

    @router.get("/metadata")
    async def metadata(d: Domain = Depends(context)) -> dict[str, Any]:
        # Discovery exposes only resources authorized for the authenticated actor.
        visible = {}
        for key, spec in config["resources"].items():
            if set(spec["read"]).intersection(d.roles):
                visible[key] = {
                    **spec,
                    "can_create": bool(set(spec["write"]).intersection(d.roles)),
                    "can_update": bool(spec["update"] and set(spec["write"]).intersection(d.roles)),
                }
        await d.b.audit(
            d.s,
            request_id=d.rid,
            actor_id=d.actor,
            actor_role=",".join(d.roles),
            action="metadata:read",
            trace_id=d.rid,
            details={},
        )
        await d.s.commit()
        return {
            "actor": {"id": d.actor, "roles": d.roles},
            "resources": visible,
            "version": config["version"],
            "title": config["title"],
            "ui": config["ui"],
            "field_choices": config["field_choices"],
            "status_semantics": config["status_semantics"],
            "workflow_transitions": config["workflow_transitions"],
            "disclaimer": config["disclaimer"],
            "features": config["features"],
            "page_size": config["page_size"],
            "max_page_size": config["max_page_size"],
            "can_audit": bool(set(d.roles).intersection(config["permissions"]["audit"])),
            "can_ai": bool(set(d.roles).intersection(config["permissions"]["ai"])),
            "integrations": {
                "pharmacy": bindings.pharmacy_safety is not None,
                "imaging": bindings.imaging_quality is not None,
                "ai": bindings.ai_evidence is not None,
            },
        }

    def register(key: str, spec: dict[str, Any]) -> None:
        model = MODELS[key]

        async def listing(request: Request, query: Query, d: Domain = Depends(context)) -> Any:
            async def task() -> Any:
                if query.limit > config["max_page_size"]:
                    raise HMSError("Requested page exceeds the configured limit")
                conditions = []
                for name, filter_value in query.filters.items():
                    if name not in model.__table__.columns:
                        raise HMSError("Unknown filter column")
                    column = model.__table__.columns[name]
                    # Strict equality only; no raw SQL, wildcard or arbitrary JSON filtering.
                    py = column.type.python_type
                    converted = UUID(filter_value) if py == UUID else filter_value
                    if py not in [UUID, str]:
                        raise HMSError("Only textual and identifier filters are supported")
                    conditions.append(getattr(model, name) == converted)
                rows = (
                    (
                        await d.s.execute(
                            select(model)
                            .where(*conditions)
                            .order_by(model.created_at.desc(), model.id)
                            .offset(query.offset)
                            .limit(query.limit)
                        )
                    )
                    .scalars()
                    .all()
                )
                count = await d.s.scalar(select(func.count()).select_from(model).where(*conditions))
                items = []
                for row in rows:
                    value = public(row)
                    if key == "billing/invoices":
                        value["outstanding"] = str(await d.balance(row))
                    if key == "inventory/items":
                        value["on_hand"] = str(await d.stock(row.id))
                    items.append(value)
                return {
                    "items": items,
                    "total": count,
                    "offset": query.offset,
                    "limit": query.limit,
                }

            return await run(d, request, key + ":list", task)

        router.add_api_route(
            "/" + key + "/query",
            listing,
            methods=["POST"],
            response_model=Page,
            name=key.replace("/", "_") + "_query",
            dependencies=permitted(spec["read"]),
        )

        async def retrieve(request: Request, id: UUID, d: Domain = Depends(context)) -> Any:
            async def task() -> Any:
                return public(await d.get(key, id))

            return await run(d, request, key + ":read", task)

        router.add_api_route(
            "/" + key + "/{id}",
            retrieve,
            methods=["GET"],
            response_model=RESPONSES[key],
            dependencies=permitted(spec["read"]),
            name=key.replace("/", "_") + "_get",
        )

        if spec["write"]:

            async def create(request: Request, payload: Any, d: Domain = Depends(context)) -> Any:
                async def task() -> Any:
                    row = await d.create(
                        key, payload.model_dump(), request.headers.get("X-HMS-Confirm") == "true"
                    )
                    return public(row)

                return await run(
                    d, request, key + ":create", task, payload.model_dump(mode="json"), True
                )

            create.__annotations__["payload"] = CREATES[key]
            router.add_api_route(
                "/" + key,
                create,
                methods=["POST"],
                status_code=201,
                response_model=RESPONSES[key],
                dependencies=permitted(spec["write"]),
                name=key.replace("/", "_") + "_create",
            )
        if spec["update"]:

            async def update(
                request: Request, id: UUID, payload: Any, d: Domain = Depends(context)
            ) -> Any:
                async def task() -> Any:
                    return public(
                        await d.update(
                            key,
                            id,
                            payload.model_dump(exclude_unset=True),
                            request.headers.get("X-HMS-Confirm") == "true",
                        )
                    )

                return await run(
                    d,
                    request,
                    key + ":update:" + str(id),
                    task,
                    payload.model_dump(mode="json", exclude_unset=True),
                    True,
                )

            update.__annotations__["payload"] = UPDATES[key]
            router.add_api_route(
                "/" + key + "/{id}",
                update,
                methods=["PUT"],
                response_model=RESPONSES[key],
                dependencies=permitted(spec["write"]),
                name=key.replace("/", "_") + "_update",
            )

    # Fixed endpoints are registered first, before variable identifier routes.
    @router.get(
        "/finance/ledger", dependencies=permitted(config["resources"]["finance/ledger"]["read"])
    )
    async def ledger(request: Request, d: Domain = Depends(context), offset: int = 0) -> Any:
        async def task() -> Any:
            if offset < 0:
                raise HMSError("Offset cannot be negative")
            m = MODELS["finance/ledger"]
            rows = (
                (
                    await d.s.execute(
                        select(m)
                        .order_by(m.created_at.desc(), m.id)
                        .offset(offset)
                        .limit(config["page_size"])
                    )
                )
                .scalars()
                .all()
            )
            return {"items": [public(r) for r in rows]}

        return await run(d, request, "finance/ledger:read", task)

    @router.get(
        "/inventory/low-stock",
        dependencies=permitted(config["resources"]["inventory/items"]["read"]),
    )
    async def low_stock(request: Request, d: Domain = Depends(context)) -> Any:
        async def task() -> Any:
            items = MODELS["inventory/items"]
            moves = MODELS["inventory/movements"]
            q = (
                select(items, func.coalesce(func.sum(moves.quantity), 0).label("on_hand"))
                .outerjoin(moves, moves.item_id == items.id)
                .group_by(items.id)
                .having(func.coalesce(func.sum(moves.quantity), 0) <= items.reorder_point)
            )
            rows = (await d.s.execute(q)).all()
            return {
                "items": [{**public(item), "on_hand": str(quantity)} for item, quantity in rows]
            }

        return await run(d, request, "inventory/low-stock:read", task)

    @router.get("/audit", dependencies=permitted(config["permissions"]["audit"]))
    async def audit(
        request: Request, request_id: UUID | None = None, d: Domain = Depends(context)
    ) -> Any:
        async def task() -> Any:
            is_admin = "ADMIN" in d.roles or "AUDITOR" in d.roles
            filter_actor = None if is_admin else d.actor
            return await d.b.audit_query(
                session=d.s,
                request_id=str(request_id) if request_id else None,
                actor_id=filter_actor,
                limit=config["max_page_size"],
                service_name=None,
            )

        return await run(d, request, "audit:read", task)

    @router.post("/ai/patient/{id}", dependencies=permitted(config["permissions"]["ai"]))
    async def advisory(request: Request, id: UUID, d: Domain = Depends(context)) -> Any:
        async def task() -> Any:
            await d.get("patients", id)
            if d.b.ai_evidence is None:
                raise HMSError(
                    "Existing evidence-grounded AI service is not connected",
                    "integration_unavailable",
                )
            result = await d.b.ai_evidence(session=d.s, patient_id=id, actor_id=d.actor)
            if (
                not result
                or not result.get("evidence_id")
                or not result.get("citations")
                or "uncertainty" not in result
            ):
                raise HMSError(
                    "Verified evidence and explicit uncertainty are required", "safe_abstain"
                )
            return {**result, "advisory": True, "disclaimer": config["disclaimer"]}

        return await run(d, request, "ai:advisory", task)

    @router.get("/finance/reports", dependencies=permitted(config["permissions"]["reports"]))
    async def financial_reports(request: Request, d: Domain = Depends(context)) -> Any:
        async def task() -> Any:
            from datetime import date
            from decimal import Decimal

            model = MODELS["billing/invoices"]
            invoices = (await d.s.execute(select(model))).scalars().all()
            billed = Decimal(0)
            outstanding = Decimal(0)
            limits = sorted(config["aging_buckets_days"])
            aging = {str(limit): Decimal(0) for limit in limits}
            for invoice in invoices:
                balance = await d.balance(invoice)
                billed += invoice.total
                outstanding += balance
                days = max(0, (date.today() - invoice.due_date).days)
                bucket = max(limit for limit in limits if limit <= days)
                aging[str(bucket)] += balance
            payment = MODELS["billing/payments"]
            adjustment = MODELS["billing/adjustments"]
            collected = Decimal(
                (await d.s.scalar(select(func.coalesce(func.sum(payment.amount), 0)))) or 0
            )
            adjustments = Decimal(
                (await d.s.scalar(select(func.coalesce(func.sum(adjustment.amount), 0)))) or 0
            )
            return {
                "currency": config["currency"],
                "billed": str(billed),
                "collected": str(collected),
                "net_revenue": str(billed - adjustments),
                "outstanding": str(outstanding),
                "collection_rate": str(collected / billed if billed else Decimal(0)),
                "aging_by_days_past_due": {k: str(v) for k, v in aging.items()},
            }

        return await run(d, request, "finance:reports", task)

    from services.hms.interop import patient_from_fhir, patient_to_fhir

    @router.get("/pharmacy/fifo-lot/{prescription_id}")
    async def get_fifo_lot_for_prescription(
        request: Request, prescription_id: UUID, d: Domain = Depends(context)
    ) -> Any:
        async def task() -> Any:
            from datetime import date
            from decimal import Decimal

            prescription = await d.get("pharmacy/prescriptions", prescription_id)
            medication = await d.get("pharmacy/medications", prescription.medication_id)
            dispense_model = MODELS["pharmacy/dispense"]
            used = Decimal(
                (
                    await d.s.scalar(
                        select(func.coalesce(func.sum(dispense_model.quantity), 0)).where(
                            dispense_model.prescription_id == prescription.id
                        )
                    )
                )
                or 0
            )
            remaining = max(Decimal(0), Decimal(prescription.quantity) - used)
            m = MODELS["inventory/movements"]
            lots = (
                await d.s.execute(
                    select(
                        m.lot,
                        m.expiry,
                        func.sum(m.quantity).label("balance"),
                        func.min(m.created_at).label("first"),
                    )
                    .where(m.item_id == medication.stock_item_id, m.expiry >= date.today())
                    .group_by(m.lot, m.expiry)
                    .having(func.sum(m.quantity) > 0)
                    .order_by(func.min(m.created_at), m.lot)
                )
            ).all()
            if not lots:
                return {
                    "prescription_id": str(prescription.id),
                    "medication_id": str(medication.id),
                    "stock_item_id": str(medication.stock_item_id),
                    "remaining_quantity": str(remaining),
                    "available": False,
                    "fifo_lot": None,
                }
            oldest = lots[0]
            dispense_qty = min(remaining, Decimal(oldest.balance))
            return {
                "prescription_id": str(prescription.id),
                "medication_id": str(medication.id),
                "stock_item_id": str(medication.stock_item_id),
                "remaining_quantity": str(remaining),
                "available": remaining > 0 and Decimal(oldest.balance) > 0,
                "fifo_lot": {
                    "lot": oldest.lot,
                    "expiry": str(oldest.expiry),
                    "lot_balance": str(oldest.balance),
                    "recommended_dispense_quantity": str(dispense_qty),
                },
            }

        return await run(d, request, "pharmacy:fifo-lot", task)

    @router.post("/fhir/patient", dependencies=permitted(config["permissions"]["ai"]))
    async def inbound(
        request: Request, payload: dict[str, Any], d: Domain = Depends(context)
    ) -> Any:
        async def task() -> Any:
            data = CREATES["patients"].model_validate(patient_from_fhir(payload)).model_dump()
            return public(await d.create("patients", data, True))

        return await run(d, request, "fhir:patient:import", task, payload, True)

    @router.get("/fhir/patient/{id}", dependencies=permitted(config["permissions"]["ai"]))
    async def outbound(request: Request, id: UUID, d: Domain = Depends(context)) -> Any:
        async def task() -> Any:
            patient = await d.get("patients", id)
            return {
                "resourceType": "Bundle",
                "type": "collection",
                "entry": [{"resource": patient_to_fhir(public(patient))}],
            }

        return await run(d, request, "fhir:patient:export", task)

    for key, spec in config["resources"].items():
        register(key, spec)
    return router


def mount_hms(app: FastAPI, bindings: HMSBindings, web_path: Path | None = None) -> None:
    """Called once by the host gateway; host CORS/auth/observability stay intact."""
    app.include_router(create_router(bindings))
    web = web_path or Path(__file__).resolve().parents[1] / "web"

    @app.get("/hms/assets/hms.js", include_in_schema=False)
    async def hms_js_compat() -> FileResponse:
        return FileResponse(
            web / "js" / "app.js",
            media_type="application/javascript",
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )

    if web.exists():
        app.mount("/hms/assets", StaticFiles(directory=web), name="hms-assets")

    @app.get("/hms", include_in_schema=False)
    async def hms_page() -> FileResponse:
        unified_index = Path(__file__).resolve().parents[1] / "web" / "index.html"
        return FileResponse(
            unified_index,
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": (
                    "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:;"
                ),
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.exception_handler(HMSError)
    async def hms_error(request: Request, exc: HMSError) -> JSONResponse:
        rid = getattr(request.state, "hms_request_id", str(uuid4()))
        return JSONResponse(
            status_code=422,
            content={"error": exc.code, "message": exc.message, "request_id": rid},
            headers={"X-Request-ID": rid, "Cache-Control": "no-store"},
        )
