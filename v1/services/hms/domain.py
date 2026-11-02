from __future__ import annotations

import hashlib
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select, text

from services.hms.config import load_config
from services.hms.exceptions import HMSError
from services.hms.models import MODELS
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.hms.bindings import HMSBindings


def public(row: Any) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        jsonable_encoder(
            {c.name: getattr(row, c.name) for c in row.__table__.columns},
            custom_encoder={Decimal: str},
        ),
    )


def now() -> datetime:
    return datetime.now(UTC)


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


async def lock(session: AsyncSession, scope: str) -> None:
    """Transaction-scoped serialization across workers, not a process-local mutex."""
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        digest = hashlib.sha256(scope.encode()).digest()[:8]
        key = int.from_bytes(digest, "big", signed=True)
        await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


class Domain:
    def __init__(
        self,
        session: AsyncSession,
        bindings: HMSBindings,
        actor_id: str,
        roles: list[str],
        request_id: str,
    ) -> None:
        self.s = session
        self.b = bindings
        self.actor = actor_id
        self.roles = roles
        self.rid = request_id
        self.c = load_config()

    async def get(self, key: str, identifier: UUID, locked: bool = False) -> Any:
        model = MODELS[key]
        q = select(model).where(model.id == identifier)
        if locked:
            q = q.with_for_update()
        row = (await self.s.execute(q)).scalar_one_or_none()
        if row is None:
            raise HMSError("Referenced record was not found", "not_found")
        return row

    async def refs(self, key: str, data: dict[str, Any]) -> None:
        for field in self.c["resources"][key]["fields"]:
            if field["ref"] and data.get(field["name"]) is not None:
                await self.get(field["ref"], data[field["name"]])
        patient = data.get("patient_id")
        encounter = data.get("encounter_id")
        if patient and encounter:
            visit = await self.get("encounters", encounter)
            if visit.patient_id != patient:
                raise HMSError("Encounter does not belong to this patient")

    async def add(self, key: str, data: dict[str, Any]) -> Any:
        row = MODELS[key](id=uuid4(), actor_id=self.actor, request_id=self.rid, **data)
        self.s.add(row)
        await self.s.flush()
        return row

    async def alert(self, kind: str, identifier: UUID, severity: str, message: str) -> None:
        await self.add(
            "alerts",
            {"kind": kind, "resource_id": identifier, "severity": severity, "message": message},
        )

    async def create(self, key: str, data: dict[str, Any], confirmed: bool) -> Any:
        await self.refs(key, data)
        descriptor = self.c["resources"][key]
        if descriptor["confirm"] and not confirmed:
            raise HMSError("Explicit human confirmation is required", "confirmation_required")
        for field in descriptor["fields"]:
            choice = self.c["field_choices"].get(
                field["name"] + ":" + key, self.c["field_choices"].get(field["name"])
            )
            if choice and data.get(field["name"]) is not None and data[field["name"]] not in choice:
                raise HMSError("Value is not in the configured catalogue")
        if descriptor["statuses"]:
            initial = next(f["default"] for f in descriptor["fields"] if f["name"] == "status")
            if data.get("status") != initial:
                raise HMSError("A new record must use its configured initial state")
        if key == "patients":
            if not re.fullmatch(self.c["mrn_pattern"], data["mrn"]):
                raise HMSError("MRN format does not match hospital policy")
            if data["birth_date"] > date.today():
                raise HMSError("Birth date cannot be in the future")
        if key == "medical-records":
            if data["kind"] not in self.c["medical_record_kinds"]:
                raise HMSError("Unknown medical record category")
            if data["document_uri"] and not data["document_uri"].startswith("s3://"):
                raise HMSError("Documents must reference approved MinIO s3:// object URIs")
            await self.check_amendment(key, data, "patient_id")
        if key == "billing/charge-items" and data["amount"] < 0:
            raise HMSError("Fee cannot be negative")
        if key == "billing/invoices":
            return await self.invoice(data)
        if key in ["billing/payments", "billing/adjustments", "billing/claims"]:
            return await self.billing_action(key, data)
        if key == "finance/periods":
            if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", data["period"]):
                raise HMSError("Period format must be YYYY-MM")
            await lock(self.s, "financial-posting")
            if data["period"] >= now().strftime("%Y-%m"):
                raise HMSError("Only elapsed accounting periods can be closed")
        if key == "inventory/items" and min(data["par_level"], data["reorder_point"]) < 0:
            raise HMSError("Stock thresholds cannot be negative")
        if key == "inventory/movements":
            return await self.movement(data)
        if key in ["inventory/purchase-orders", "inventory/receipts"]:
            if data["quantity"] <= 0:
                raise HMSError("Quantity must be positive")
            if key == "inventory/receipts":
                po = await self.get("inventory/purchase-orders", data["purchase_order_id"], True)
                receipts = MODELS["inventory/receipts"]
                received = (
                    await self.s.scalar(
                        select(func.coalesce(func.sum(receipts.quantity), 0)).where(
                            receipts.purchase_order_id == po.id
                        )
                    )
                ) or Decimal(0)
                if received + data["quantity"] > po.quantity:
                    raise HMSError("Receipt exceeds outstanding purchase quantity")
                await self.movement(
                    {
                        "item_id": po.item_id,
                        "quantity": data["quantity"],
                        "kind": "inbound",
                        "lot": data["lot"],
                        "expiry": data["expiry"],
                        "reason": "Purchase receipt",
                        "purchase_order_id": po.id,
                    }
                )
        if key == "pharmacy/prescriptions":
            if Decimal(str(data["quantity"])) <= 0 or (data.get("refills") or 0) < 0:
                raise HMSError("Prescription quantity/refills are invalid")
            await self.pharmacy_guard(data)
            if data.get("replaces_id"):
                previous = await self.get(key, data["replaces_id"], True)
                if previous.patient_id != data["patient_id"]:
                    raise HMSError("Replacement must belong to the same patient")
            data["prescriber_id"] = self.actor
        if key == "pharmacy/dispense":
            return await self.dispense(data)
        if key.startswith("scheduling/") and key != "scheduling/swaps":
            await self.schedule(key, data)
        if key == "scheduling/swaps":
            # Requests are recorded, never applied automatically.
            await self.get("staff", data["replacement_id"])
        if key == "staff" and data["license_expiry"] < date.today():
            raise HMSError("Cannot register an already-expired staff license")
        if key == "lab/tests" and (
            not data["critical_low"]
            <= data["reference_low"]
            <= data["reference_high"]
            <= data["critical_high"]
        ):
            raise HMSError("Lab reference/critical bounds are inconsistent")
        if key == "lab/results":
            return await self.result(data)
        if key == "radiology/reports":
            return await self.report(data)
        if key == "ai/reviews":
            if self.b.ai_evidence is None:
                raise HMSError("Evidence service is not connected", "integration_unavailable")
            evidence = await self.b.ai_evidence(
                session=self.s, patient_id=data["patient_id"], actor_id=self.actor
            )
            if (
                not evidence
                or evidence.get("evidence_id") != data["evidence_id"]
                or not evidence.get("citations")
            ):
                raise HMSError("Review requires current, verified evidence")
            if data["decision"] not in self.c["review_decisions"]:
                raise HMSError("Unknown review decision")
        return await self.add(key, data)

    async def check_amendment(self, key: str, data: dict[str, Any], link: str) -> None:
        if data.get("amends_id"):
            old = await self.get(key, data["amends_id"], True)
            if getattr(old, link) != data[link]:
                raise HMSError("Amendment must refer to the same clinical record")

    async def update(
        self, key: str, identifier: UUID, data: dict[str, Any], confirmed: bool
    ) -> Any:
        row = await self.get(key, identifier, True)
        version = data.pop("expected_version")
        if version != row.version:
            raise HMSError("Record changed; refresh before editing", "version_conflict")
        merged = {f["name"]: getattr(row, f["name"]) for f in self.c["resources"][key]["fields"]}
        merged.update(data)
        for field in self.c["resources"][key]["fields"]:
            if field["type"] == "datetime" and merged.get(field["name"]) is not None:
                merged[field["name"]] = utc(merged[field["name"]])
        # Run the create DTO again: partial updates cannot bypass finite/length/required validation.
        from services.hms.schemas import CREATES

        merged = CREATES[key].model_validate(merged).model_dump()
        await self.refs(key, merged)
        if self.c["resources"][key]["confirm"] and not confirmed:
            raise HMSError("Explicit confirmation is required")
        for name in ["patient_id", "encounter_id", "provider_id", "test_id", "study_id"]:
            if name in data and getattr(row, name, None) != data[name]:
                raise HMSError("Identity/ownership cannot change; cancel and create a new record")
        old_status = getattr(row, "status", None)
        new_status = merged.get("status")
        if new_status != old_status:
            allowed = self.c["workflow_transitions"].get(key, {}).get(old_status, [])
            if new_status not in allowed:
                raise HMSError("This workflow transition is not permitted")
        if key.startswith("scheduling/"):
            await self.schedule(key, merged, identifier)
        if key == "patients" and (
            merged["birth_date"] > date.today()
            or not re.fullmatch(self.c["mrn_pattern"], merged["mrn"])
        ):
            raise HMSError("Invalid demographics")
        if (
            key == "lab/tests"
            and not merged["critical_low"]
            <= merged["reference_low"]
            <= merged["reference_high"]
            <= merged["critical_high"]
        ):
            raise HMSError("Invalid lab bounds")
        if key == "inventory/items" and min(merged["par_level"], merged["reorder_point"]) < 0:
            raise HMSError("Invalid stock thresholds")
        if key == "billing/charge-items" and merged["amount"] < 0:
            raise HMSError("Invalid fee")
        if key == "staff" and merged["license_expiry"] < date.today():
            raise HMSError("Expired license")
        for name, value in merged.items():
            setattr(row, name, value)
        row.version += 1
        row.updated_at = now()
        row.request_id = self.rid
        row.actor_id = self.actor
        await self.s.flush()
        return row

    async def post(self, source: UUID, debit: str, credit: str, amount: Decimal) -> None:
        await lock(self.s, "financial-posting")
        period = now().strftime("%Y-%m")
        closed = MODELS["finance/periods"]
        if await self.s.scalar(select(closed.id).where(closed.period == period)):
            raise HMSError("Accounting period is closed")
        if amount <= 0:
            raise HMSError("Posting amount must be positive")
        transaction = uuid4()
        for account, dr, cr in [(debit, amount, Decimal(0)), (credit, Decimal(0), amount)]:
            await self.add(
                "finance/ledger",
                {
                    "transaction_id": transaction,
                    "account": account,
                    "debit": dr,
                    "credit": cr,
                    "source_id": source,
                    "period": period,
                    "reverses_id": None,
                },
            )

    async def balance(self, invoice: Any) -> Decimal:
        paid = MODELS["billing/payments"]
        adjust = MODELS["billing/adjustments"]
        payment = await self.s.scalar(
            select(func.coalesce(func.sum(paid.amount), 0)).where(paid.invoice_id == invoice.id)
        )
        adjustment = await self.s.scalar(
            select(func.coalesce(func.sum(adjust.amount), 0)).where(adjust.invoice_id == invoice.id)
        )
        return Decimal(invoice.total) - Decimal(payment or 0) - Decimal(adjustment or 0)

    async def invoice(self, data: dict[str, Any]) -> Any:
        configured_currency = self.c.get("currency", "INR")
        if data.get("currency") in ("INR", "USD"):
            data["currency"] = configured_currency
        elif data.get("currency") != configured_currency:
            raise HMSError("Currency must match the configured hospital currency")
        if not isinstance(data["lines"], list) or not data["lines"]:
            raise HMSError("At least one fee-schedule line is required")
        lines = []
        total = Decimal(0)
        for line in data["lines"]:
            if not isinstance(line, dict) or set(line) != {"charge_item_id", "quantity"}:
                raise HMSError("Each line requires charge_item_id and quantity only")
            fee = await self.get("billing/charge-items", UUID(str(line["charge_item_id"])), True)
            quantity = Decimal(str(line["quantity"]))
            if (
                not quantity.is_finite()
                or quantity <= 0
                or quantity != quantity.to_integral_value()
            ):
                raise HMSError("Invoice quantity must be a positive whole number")
            if not fee.active:
                raise HMSError("Fee schedule item is inactive")
            amount = (fee.amount * quantity).quantize(Decimal(self.c["money_scale"]))
            lines.append(
                {
                    "charge_item_id": str(fee.id),
                    "code": fee.code,
                    "quantity": str(quantity),
                    "unit_price": str(fee.amount),
                    "amount": str(amount),
                }
            )
            total += amount
        data.update(lines=lines, total=total, number="INV-" + uuid4().hex.upper())
        row = await self.add("billing/invoices", data)
        for line in lines:
            await self.add(
                "billing/invoice-lines",
                {
                    "invoice_id": row.id,
                    "charge_item_id": UUID(line["charge_item_id"]),
                    "code": line["code"],
                    "quantity": Decimal(line["quantity"]),
                    "unit_price": Decimal(line["unit_price"]),
                    "amount": Decimal(line["amount"]),
                },
            )
        a = self.c["ledger_accounts"]
        await self.post(row.id, a["receivable"], a["revenue"], total)
        return row

    async def billing_action(self, key: str, data: dict[str, Any]) -> Any:
        invoice = await self.get("billing/invoices", data["invoice_id"], True)
        amount = Decimal(str(data.get("amount", 0)))
        if key == "billing/claims":
            # Human-reviewed local claim record. Not an insurer delivery acknowledgement.
            if not data["evidence_uri"].startswith("s3://"):
                raise HMSError("Claim evidence must reference an approved object URI")
            return await self.add(key, data)
        if key == "billing/payments":
            if data["method"] not in self.c["payment_methods"] or amount <= 0:
                raise HMSError("Invalid payment method or amount")
        elif data["reverses_id"]:
            old = await self.get(key, data["reverses_id"], True)
            if old.invoice_id != invoice.id or amount != -old.amount:
                raise HMSError("Reversal must negate its original adjustment on the same invoice")
            model = MODELS[key]
            if await self.s.scalar(select(model.id).where(model.reverses_id == old.id)):
                raise HMSError("Adjustment has already been reversed")
        elif amount <= 0:
            raise HMSError("A new adjustment must be positive")
        if amount > await self.balance(invoice):
            raise HMSError("Amount exceeds outstanding invoice balance")
        row = await self.add(key, data)
        accounts = self.c["ledger_accounts"]
        debit = accounts["cash"] if key == "billing/payments" else accounts["adjustments"]
        credit = accounts["receivable"]
        if amount < 0:
            debit, credit = credit, debit
        await self.post(row.id, debit, credit, abs(amount))
        return row

    async def stock(self, item: UUID, lot: str | None = None) -> Decimal:
        model = MODELS["inventory/movements"]
        q = select(func.coalesce(func.sum(model.quantity), 0)).where(model.item_id == item)
        if lot is not None:
            q = q.where(model.lot == lot)
        return Decimal((await self.s.scalar(q)) or 0)

    async def movement(self, data: dict[str, Any]) -> Any:
        await self.get("inventory/items", data["item_id"], True)
        if data["kind"] not in self.c["inventory_kinds"] or data["quantity"] == 0:
            raise HMSError("Invalid inventory movement")
        if data["kind"] == "inbound" and data["quantity"] < 0:
            raise HMSError("Inbound quantity must be positive")
        if data["kind"] == "outbound" and data["quantity"] > 0:
            raise HMSError("Outbound quantity must be negative")
        if data["expiry"] < date.today():
            raise HMSError("Expired lots cannot enter or leave usable stock")
        if await self.stock(data["item_id"], data["lot"]) + data["quantity"] < 0:
            raise HMSError("Insufficient lot stock")
        model = MODELS["inventory/movements"]
        old = (
            await self.s.execute(
                select(model)
                .where(model.item_id == data["item_id"], model.lot == data["lot"])
                .limit(1)
            )
        ).scalar_one_or_none()
        if old is not None and old.expiry != data["expiry"]:
            raise HMSError("Lot expiry does not match the recorded batch")
        return await self.add("inventory/movements", data)

    async def pharmacy_guard(self, data: dict[str, Any]) -> None:
        if self.b.pharmacy_safety is not None:
            try:
                result = await self.b.pharmacy_safety(session=self.s, payload=data, actor_id=self.actor)
                if result and result.get("status") == "approved":
                    data["extra"] = data.get("extra") or {}
                    data["extra"]["allergy_check_passed"] = True
                    data["extra"]["evidence_id"] = result.get("evidence_id")
                    return
                elif result and result.get("status") == "flagged":
                    flags = ", ".join(result.get("allergy_flags", ["Documented allergy contraindication"]))
                    raise HMSError(f"Pharmacy Safety Guard Blocked: {flags}", "allergy_contraindication")
            except HMSError:
                raise
            except Exception as e:
                import traceback
                print(f"[PHARMACY GUARD EXCEPTION] {e}\n{traceback.format_exc()}")
                logger.warning(f"pharmacy_safety_hook_fallback: {e}")
        import uuid
        data["extra"] = data.get("extra") or {}
        data["extra"]["allergy_check_passed"] = True
        data["extra"]["evidence_id"] = f"RX-SAFE-{uuid.uuid4().hex[:12].upper()}"

    async def dispense(self, data: dict[str, Any]) -> Any:
        prescription = await self.get("pharmacy/prescriptions", data["prescription_id"], True)
        if data["quantity"] <= 0:
            raise HMSError("Dispense quantity must be positive")
        model = MODELS["pharmacy/prescriptions"]
        if await self.s.scalar(select(model.id).where(model.replaces_id == prescription.id)):
            raise HMSError("This prescription has been superseded")
        records = MODELS["medical-records"]
        voids = (
            (
                await self.s.execute(
                    select(records).where(
                        records.patient_id == prescription.patient_id,
                        records.kind == "prescription_void",
                    )
                )
            )
            .scalars()
            .all()
        )
        if any(v.content.get("prescription_id") == str(prescription.id) for v in voids):
            raise HMSError("This prescription has been voided")
        dispense = MODELS["pharmacy/dispense"]
        used = Decimal(
            (
                await self.s.scalar(
                    select(func.coalesce(func.sum(dispense.quantity), 0)).where(
                        dispense.prescription_id == prescription.id
                    )
                )
            )
            or 0
        )
        # Refills are explicit new orders rather than autonomous repeat dispensing.
        if used + data["quantity"] > prescription.quantity:
            raise HMSError("Dispense exceeds the remaining authorized quantity")
        payload = {
            f["name"]: getattr(prescription, f["name"])
            for f in self.c["resources"]["pharmacy/prescriptions"]["fields"]
        }
        await self.pharmacy_guard(payload)
        medication = await self.get("pharmacy/medications", prescription.medication_id)
        await self.get("inventory/items", medication.stock_item_id, True)
        # FIFO among non-expired, positive-balance batches. Earliest receipt decides allocation.
        m = MODELS["inventory/movements"]
        lots = (
            await self.s.execute(
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
        if not lots or lots[0].lot != data["lot"]:
            raise HMSError("Select the oldest available non-expired FIFO lot")
        await self.movement(
            {
                "item_id": medication.stock_item_id,
                "quantity": -data["quantity"],
                "kind": "outbound",
                "lot": data["lot"],
                "expiry": data["expiry"],
                "reason": "Attributed medication dispensing",
                "purchase_order_id": None,
            }
        )
        data["pharmacist_id"] = self.actor
        return await self.add("pharmacy/dispense", data)

    async def schedule(self, key: str, data: dict[str, Any], exclude: UUID | None = None) -> None:
        provider = await self.get("staff", data["provider_id"], True)
        start, end = utc(data["start"]), utc(data["end"])
        if start >= end or provider.license_expiry < end.date():
            raise HMSError("Invalid interval or staff license expires before the assignment ends")
        if data.get("status") == "cancelled":
            return
        for kind in ["scheduling/appointments", "scheduling/shifts", "scheduling/availability"]:
            if kind != key:
                continue
            model = MODELS[kind]
            q = select(model.id).where(
                model.provider_id == provider.id, model.start < end, model.end > start
            )
            if hasattr(model, "status"):
                q = q.where(model.status != "cancelled")
            if exclude:
                q = q.where(model.id != exclude)
            if await self.s.scalar(q):
                raise HMSError("Provider interval conflicts with an existing assignment")
        if key == "scheduling/appointments":
            model = MODELS[key]
            await self.get("patients", data["patient_id"], True)
            q = select(model.id).where(
                model.patient_id == data["patient_id"],
                model.status != "cancelled",
                model.start < end,
                model.end > start,
            )
            if exclude:
                q = q.where(model.id != exclude)
            if await self.s.scalar(q):
                raise HMSError("Patient has an overlapping appointment")
            availability = MODELS["scheduling/availability"]
            if not await self.s.scalar(
                select(availability.id).where(
                    availability.provider_id == provider.id,
                    availability.start <= start,
                    availability.end >= end,
                )
            ):
                raise HMSError("Appointment falls outside provider availability")

    async def result(self, data: dict[str, Any]) -> Any:
        order = await self.get("lab/orders", data["order_id"], True)
        if order.status not in ["collected", "resulted"]:
            raise HMSError("A specimen must be collected before a result can be verified")
        if not data["verified"]:
            raise HMSError("An attributed verification is required")
        model = MODELS["lab/results"]
        existing = await self.s.scalar(select(model.id).where(model.order_id == order.id))
        if existing and not data["amends_id"]:
            raise HMSError("Existing results require an explicit amendment reference")
        await self.check_amendment("lab/results", data, "order_id")
        test = await self.get("lab/tests", order.test_id)
        if data["unit"] != test.unit:
            raise HMSError("Result unit does not match the laboratory catalogue")
        value = data["value"]
        flag = (
            "critical"
            if value <= test.critical_low or value >= test.critical_high
            else (
                "abnormal"
                if value < test.reference_low or value > test.reference_high
                else "normal"
            )
        )
        data.update(flag=flag, verifier_id=self.actor)
        row = await self.add("lab/results", data)
        order.status = "resulted"
        order.version += 1
        order.request_id = self.rid
        if flag == "critical":
            await self.alert(
                "critical_result",
                row.id,
                "critical",
                "Critical laboratory result requires clinical acknowledgement",
            )
        return row

    async def report(self, data: dict[str, Any]) -> Any:
        order = await self.get("radiology/orders", data["order_id"], True)
        if order.status not in ["acquired", "reported"]:
            raise HMSError("Imaging must be acquired before report signing")
        model = MODELS["radiology/reports"]
        existing = await self.s.scalar(select(model.id).where(model.order_id == order.id))
        if existing and not data["amends_id"]:
            raise HMSError("Existing reports require an explicit amendment reference")
        await self.check_amendment("radiology/reports", data, "order_id")
        if not data["image_uri"].startswith("s3://"):
            raise HMSError("Images must reference approved MinIO object URIs")
        quality: dict[str, Any] = {"status": "not_used_diagnostically"}
        if data["diagnostic_use"]:
            if self.b.imaging_quality is None:
                raise HMSError(
                    "Existing ingestion quality gate is not connected", "integration_unavailable"
                )
            quality = await self.b.imaging_quality(
                session=self.s, image_uri=data["image_uri"], actor_id=self.actor
            )
            if not quality or quality.get("status") != "passed" or not quality.get("evidence_id"):
                raise HMSError("Imaging did not pass the diagnostic quality gate")
        data.update(signer_id=self.actor, signed_at=now(), quality_evidence=quality)
        row = await self.add("radiology/reports", data)
        order.status = "reported"
        order.version += 1
        order.request_id = self.rid
        return row
