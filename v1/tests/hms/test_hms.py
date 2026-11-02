from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select, text

from demo.host import Base, make_app
from services.hms.config import load_config
from services.hms.interop import from_fhir, to_fhir
from services.hms.models import MODELS

TOKEN = "unit-test-only-token-not-a-real-secret"


@pytest_asyncio.fixture
async def env():
    url = os.environ.get("HMS_TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    if url.startswith("postgresql") and "hms_test" not in url.rsplit("/", 1)[-1]:
        raise RuntimeError("Refusing destructive tests outside a database named hms_test*")
    app = make_app(url, TOKEN)
    if url.startswith("postgresql"):
        async with app.state.hms_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": "Bearer " + TOKEN},
        ) as client:
            yield app, client


async def create(client, key, data, confirm=True, expected=201, idem=None):
    result = await client.post(
        "/api/v2/hms/" + key,
        json=data,
        headers={"Idempotency-Key": idem or str(uuid4()), "X-HMS-Confirm": str(confirm).lower()},
    )
    assert result.status_code == expected, result.text
    return result.json()


async def patient(client, mrn="HMS-001"):
    return await create(
        client,
        "patients",
        dict(
            mrn=mrn,
            given_name="Synthetic",
            family_name="Test",
            birth_date="1990-01-01",
            consent={"research": False},
        ),
    )


async def encounter(client, p):
    return await create(
        client,
        "encounters",
        dict(
            patient_id=p["id"],
            department="Oncology",
            attending_id="clinician-test",
            started_at=datetime.now(timezone.utc).isoformat(),
        ),
    )


async def catalogue(client):
    item = await create(
        client,
        "inventory/items",
        dict(
            sku="SKU-" + uuid4().hex,
            name="Synthetic stock",
            category="medication",
            unit="tablet",
            par_level="10",
            reorder_point="5",
        ),
    )
    medication = await create(
        client,
        "pharmacy/medications",
        dict(
            code=uuid4().hex,
            name="Synthetic medicine",
            strength="10 mg",
            dosage_form="tablet",
            route="oral",
            stock_item_id=item["id"],
        ),
    )
    return item, medication


@pytest.mark.asyncio
async def test_gateway_metadata_and_all_read_queues(env):
    app, client = env
    r = await client.get("/hms")
    assert r.status_code == 200
    assert "Content-Security-Policy" in r.headers
    assert (await client.get("/hms/assets/hms.js")).status_code == 200
    assert (await client.get("/health")).json()["status"] == "ok"
    m = (await client.get("/api/v2/hms/metadata")).json()
    assert m["can_audit"] and m["can_ai"]
    assert not m["integrations"]["pharmacy"]
    for key in m["resources"]:
        page = await client.post("/api/v2/hms/" + key + "/query", json={})
        assert page.status_code == 200, page.text
        assert page.json()["total"] == 0
        missing = await client.get("/api/v2/hms/" + key + "/" + str(uuid4()))
        assert missing.status_code == 422
    assert (await client.get("/api/v2/hms/audit")).status_code == 200
    assert (await client.get("/api/v2/hms/finance/ledger")).status_code == 200
    assert (await client.get("/api/v2/hms/inventory/low-stock")).json()["items"] == []
    assert (
        await client.get("/api/v2/hms/metadata", headers={"Authorization": "Bearer invalid"})
    ).status_code == 401


@pytest.mark.asyncio
async def test_patient_validation_update_idempotence_fhir_and_audit(env):
    app, c = env
    payload = dict(
        mrn="SYN-001",
        given_name="Synthetic",
        family_name="Patient",
        birth_date="1980-01-02",
        gender="unknown",
        contact={"email": "test@example.invalid"},
    )
    idem = str(uuid4())
    p = await create(c, "patients", payload, idem=idem)
    assert (await create(c, "patients", payload, idem=idem))["id"] == p["id"]
    await create(c, "patients", {**payload, "given_name": "Changed"}, expected=422, idem=idem)
    await create(c, "patients", payload, expected=422)
    await create(c, "patients", {**payload, "mrn": "1"}, expected=422)
    await create(
        c, "patients", {**payload, "mrn": "SYN-002", "birth_date": "2999-01-01"}, expected=422
    )
    await create(c, "patients", {**payload, "mrn": "SYN-003", "injected": "x"}, expected=422)
    r = await c.post("/api/v2/hms/patients", json={**payload, "mrn": "SYN-004"})
    assert r.status_code == 422
    record = (await c.get("/api/v2/hms/patients/" + p["id"])).json()
    assert record["mrn"] == "SYN-001"
    hdr = {"Idempotency-Key": str(uuid4())}
    r = await c.put(
        "/api/v2/hms/patients/" + p["id"],
        json={"expected_version": 1, "given_name": "Edited"},
        headers=hdr,
    )
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 2
    r = await c.put(
        "/api/v2/hms/patients/" + p["id"],
        json={"expected_version": 1, "given_name": "Stale"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert r.status_code == 422
    r = await c.put(
        "/api/v2/hms/patients/" + p["id"],
        json={"expected_version": 2, "given_name": None},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert r.status_code == 422
    query = await c.post("/api/v2/hms/patients/query", json={"filters": {"mrn": "SYN-001"}})
    assert query.json()["total"] == 1
    for filters in [{"unknown": "x"}, {"created_at": "invalid"}]:
        assert (
            await c.post("/api/v2/hms/patients/query", json={"filters": filters})
        ).status_code == 422
    fhir = (await c.get("/api/v2/hms/fhir/patient/" + p["id"])).json()["entry"][0]["resource"]
    fhir["identifier"][0]["value"] = "SYN-IMPORT"
    p2 = await create(c, "fhir/patient", fhir, expected=200)
    assert p2["mrn"] == "SYN-IMPORT"
    assert from_fhir(to_fhir("Patient", p2))["mrn"] == p2["mrn"]
    await create(c, "fhir/patient", {"resourceType": "Observation"}, expected=422)
    events = (await c.get("/api/v2/hms/audit", params={"request_id": p["request_id"]})).json()[
        "items"
    ]
    assert events and events[0]["details"]["record_id"] == p["id"]
    assert (await c.post("/api/v2/hms/ai/patient/" + p["id"], json={})).status_code == 422
    await create(
        c,
        "medical-records",
        dict(patient_id=p["id"], kind="allergy", content={"substance": "test"}),
    )
    await create(
        c,
        "medical-records",
        dict(
            patient_id=p["id"],
            kind="document",
            content={},
            document_uri="https://unapproved.invalid",
        ),
        expected=422,
    )
    await create(
        c, "medical-records", dict(patient_id=p["id"], kind="bad", content={}), expected=422
    )
    assert (
        await c.get("/api/v2/hms/metadata", headers={"X-Request-ID": "not-uuid"})
    ).status_code == 422


@pytest.mark.asyncio
async def test_billing_atomicity_balance_reversal_immutability(env):
    app, c = env
    p = await patient(c)
    fee = await create(
        c,
        "billing/charge-items",
        dict(code="CONSULT", name="Synthetic consultation", amount="120.50", coding_system="local"),
    )
    invoice_data = dict(
        patient_id=p["id"],
        lines=[{"charge_item_id": fee["id"], "quantity": 2}],
        due_date="2030-12-01",
    )
    await create(c, "billing/invoices", invoice_data, confirm=False, expected=422)
    inv = await create(c, "billing/invoices", invoice_data)
    assert inv["total"] == "241.00"
    await create(c, "billing/invoices", {**invoice_data, "currency": "ZZZ"}, expected=422)
    await create(c, "billing/invoices", {**invoice_data, "lines": []}, expected=422)
    await create(
        c,
        "billing/invoices",
        {**invoice_data, "lines": [{"charge_item_id": fee["id"], "quantity": 0}]},
        expected=422,
    )
    await create(c, "billing/invoices", {**invoice_data, "lines": [{"price": "1"}]}, expected=422)
    payment = await create(
        c,
        "billing/payments",
        dict(invoice_id=inv["id"], amount="50.00", method="cash", reference="TEST-PAYMENT"),
    )
    await create(
        c,
        "billing/payments",
        dict(invoice_id=inv["id"], amount="300", method="cash", reference="OVERPAY"),
        expected=422,
    )
    await create(
        c,
        "billing/payments",
        dict(invoice_id=inv["id"], amount="1", method="bad", reference="BAD"),
        expected=422,
    )
    adjust = await create(
        c, "billing/adjustments", dict(invoice_id=inv["id"], amount="10", reason="Test credit")
    )
    await create(
        c,
        "billing/adjustments",
        dict(invoice_id=inv["id"], amount="-10", reason="Reverse credit", reverses_id=adjust["id"]),
    )
    await create(
        c,
        "billing/adjustments",
        dict(
            invoice_id=inv["id"],
            amount="-10",
            reason="Duplicate reversal",
            reverses_id=adjust["id"],
        ),
        expected=422,
    )
    await create(
        c,
        "billing/adjustments",
        dict(invoice_id=inv["id"], amount="-1", reason="Unlinked negative"),
        expected=422,
    )
    await create(
        c,
        "billing/claims",
        dict(
            invoice_id=inv["id"],
            payer="Test",
            reference="LOCAL-ONLY",
            evidence_uri="s3://approved/claim",
        ),
    )
    await create(
        c,
        "billing/claims",
        dict(invoice_id=inv["id"], payer="Test", reference="LOCAL", evidence_uri="https://bad"),
        expected=422,
    )
    page = (await c.post("/api/v2/hms/billing/invoices/query", json={})).json()
    assert page["items"][0]["outstanding"] == "191.00"
    lines = (await c.post("/api/v2/hms/billing/invoice-lines/query", json={})).json()
    assert lines["total"] == 1
    ledger = (await c.get("/api/v2/hms/finance/ledger")).json()["items"]
    assert len(ledger) == 8
    assert sum(Decimal(e["debit"]) - Decimal(e["credit"]) for e in ledger) == 0
    async with app.state.hms_sessions() as session:
        for operation in [
            "UPDATE hms_billing_payments SET amount=1",
            "DELETE FROM hms_billing_payments",
        ]:
            with pytest.raises(Exception):
                await session.execute(text(operation))
                await session.commit()
            await session.rollback()
        model = MODELS["billing/payments"]
        row = await session.get(
            model, payment["id"] if False else __import__("uuid").UUID(payment["id"])
        )
        row.amount = Decimal(1)
        with pytest.raises(ValueError):
            await session.flush()
        await session.rollback()
    await create(c, "finance/periods", dict(period="2020-01", reason="Test close"))
    await create(c, "finance/periods", dict(period="BAD", reason="Test close"), expected=422)
    await create(c, "finance/periods", dict(period="2999-01", reason="Test close"), expected=422)
    summary = (await c.get("/api/v2/hms/finance/reports")).json()
    assert summary["billed"] == "241.00"
    assert summary["collected"] == "50.00"
    assert summary["outstanding"] == "191.00"


@pytest.mark.asyncio
async def test_inventory_receipts_and_pharmacy_fail_closed(env):
    app, c = env
    p = await patient(c)
    visit = await encounter(c, p)
    item, med = await catalogue(c)
    po = await create(
        c,
        "inventory/purchase-orders",
        dict(supplier="Test supplier", item_id=item["id"], quantity="20", reference="TEST-PO"),
    )
    receipt = dict(purchase_order_id=po["id"], quantity="20", lot="LOT-A", expiry="2099-01-01")
    await create(c, "inventory/receipts", receipt)
    await create(c, "inventory/receipts", receipt, expected=422)
    movement = dict(
        item_id=item["id"],
        quantity="-5",
        kind="outbound",
        lot="LOT-A",
        expiry="2099-01-01",
        reason="Test consumption",
    )
    await create(c, "inventory/movements", movement)
    await create(c, "inventory/movements", {**movement, "quantity": "-50"}, expected=422)
    await create(c, "inventory/movements", {**movement, "quantity": "5"}, expected=422)
    await create(c, "inventory/movements", {**movement, "kind": "invalid"}, expected=422)
    await create(c, "inventory/movements", {**movement, "expiry": "2000-01-01"}, expected=422)
    await create(c, "inventory/movements", {**movement, "expiry": "2098-01-01"}, expected=422)
    rx = dict(
        patient_id=p["id"],
        encounter_id=visit["id"],
        medication_id=med["id"],
        quantity="10",
        directions="Synthetic instructions",
    )
    await create(c, "pharmacy/prescriptions", rx, expected=422)
    bindings = app.state.hms_bindings

    # Test-only explicit safety callback. Production must bind a validated host service.
    async def approve(**kwargs):
        return {"status": "approved", "evidence_id": "test-review"}

    object.__setattr__(bindings, "pharmacy_safety", approve)
    prescription = await create(c, "pharmacy/prescriptions", rx)
    dispense = dict(
        prescription_id=prescription["id"], quantity="6", lot="LOT-A", expiry="2099-01-01"
    )
    await create(c, "pharmacy/dispense", dispense)
    await create(c, "pharmacy/dispense", dispense, expected=422)
    await create(c, "pharmacy/dispense", {**dispense, "quantity": "0"}, expected=422)
    result = (await c.post("/api/v2/hms/inventory/items/query", json={})).json()["items"][0]
    assert result["on_hand"] == "9.0000"
    assert (await c.get("/api/v2/hms/inventory/low-stock")).json()["items"] == []
    await create(c, "inventory/movements", {**movement, "quantity": "-5"})
    assert len((await c.get("/api/v2/hms/inventory/low-stock")).json()["items"]) == 1

    async def reject(**kwargs):
        return {"status": "review_required"}

    object.__setattr__(bindings, "pharmacy_safety", reject)
    await create(c, "pharmacy/prescriptions", rx, expected=422)


@pytest.mark.asyncio
async def test_scheduling_conflicts_versions_credentials(env):
    app, c = env
    p = await patient(c)
    staff = await create(
        c,
        "staff",
        dict(
            display_name="Synthetic clinician",
            role="CLINICIAN",
            department="Oncology",
            credentials={"verified": True},
            license_expiry="2099-01-01",
        ),
    )
    start = (datetime.now(timezone.utc) + timedelta(days=5)).replace(microsecond=0)
    end = start + timedelta(hours=4)
    block = dict(provider_id=staff["id"], start=start.isoformat(), end=end.isoformat())
    avail = await create(c, "scheduling/availability", block)
    await create(c, "scheduling/availability", block, expected=422)
    data = {
        **block,
        "patient_id": p["id"],
        "kind": "Oncology follow-up",
        "end": (start + timedelta(hours=1)).isoformat(),
    }
    appt = await create(c, "scheduling/appointments", data)
    await create(c, "scheduling/appointments", data, expected=422)
    r = await c.put(
        "/api/v2/hms/scheduling/appointments/" + appt["id"],
        json={"expected_version": 1, "status": "cancelled"},
        headers={"Idempotency-Key": str(uuid4()), "X-HMS-Confirm": "true"},
    )
    assert r.status_code == 200, r.text
    await create(c, "scheduling/appointments", data)
    await create(c, "scheduling/appointments", {**data, "end": start.isoformat()}, expected=422)
    await create(
        c,
        "scheduling/appointments",
        {
            **data,
            "start": (start + timedelta(days=2)).isoformat(),
            "end": (end + timedelta(days=2)).isoformat(),
        },
        expected=422,
    )
    shift = await create(c, "scheduling/shifts", {**block, "department": "Oncology"})
    await create(
        c,
        "scheduling/swaps",
        dict(shift_id=shift["id"], replacement_id=staff["id"], reason="Requested review"),
    )
    await create(
        c,
        "staff",
        dict(
            display_name="Expired",
            role="CLINICIAN",
            department="Oncology",
            credentials={},
            license_expiry="2000-01-01",
        ),
        expected=422,
    )


@pytest.mark.asyncio
async def test_lab_and_radiology_workflow_amendments_quality(env):
    app, c = env
    p = await patient(c)
    v = await encounter(c, p)
    test_data = dict(
        code="TEST-LOINC",
        name="Synthetic analyte",
        specimen="blood",
        unit="unit",
        reference_low="3",
        reference_high="8",
        critical_low="1",
        critical_high="10",
    )
    lab = await create(c, "lab/tests", test_data)
    await create(c, "lab/tests", {**test_data, "critical_low": "5"}, expected=422)
    order = await create(
        c, "lab/orders", dict(patient_id=p["id"], encounter_id=v["id"], test_id=lab["id"])
    )
    result = dict(order_id=order["id"], value="11", unit="unit", verified=True)
    await create(c, "lab/results", result, expected=422)
    r = await c.put(
        "/api/v2/hms/lab/orders/" + order["id"],
        json={"expected_version": 1, "status": "collected"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert r.status_code == 200, r.text
    first = await create(c, "lab/results", result)
    assert first["flag"] == "critical"
    await create(c, "lab/results", result, expected=422)
    await create(
        c,
        "lab/results",
        {**result, "amends_id": first["id"], "value": "7", "unit": "bad"},
        expected=422,
    )
    amended = await create(c, "lab/results", {**result, "amends_id": first["id"], "value": "7"})
    assert amended["flag"] == "normal"
    alerts = (await c.post("/api/v2/hms/alerts/query", json={})).json()
    assert alerts["total"] == 1
    study = await create(
        c, "radiology/studies", dict(modality="CT", body_part="Chest", name="Synthetic study")
    )
    ro = await create(
        c,
        "radiology/orders",
        dict(
            patient_id=p["id"],
            encounter_id=v["id"],
            study_id=study["id"],
            priority="routine",
            preparation="Reviewed",
        ),
    )
    report = dict(
        order_id=ro["id"],
        findings="Synthetic findings",
        impression="Synthetic impression",
        image_uri="s3://approved/image",
        dicom_metadata={},
        diagnostic_use=True,
    )
    await create(c, "radiology/reports", report, expected=422)
    for version, status in [(1, "scheduled"), (2, "acquired")]:
        r = await c.put(
            "/api/v2/hms/radiology/orders/" + ro["id"],
            json={"expected_version": version, "status": status},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert r.status_code == 200, r.text
    await create(c, "radiology/reports", report, expected=422)

    async def gate(**kwargs):
        return {"status": "passed", "evidence_id": "test-quality"}

    object.__setattr__(app.state.hms_bindings, "imaging_quality", gate)
    signed = await create(c, "radiology/reports", report)
    assert signed["signer_id"] == "development-operator"
    await create(c, "radiology/reports", report, expected=422)
    await create(
        c, "radiology/reports", {**report, "amends_id": signed["id"], "diagnostic_use": False}
    )

    async def evidence(**kwargs):
        return {
            "evidence_id": "test-evidence",
            "citations": [{"title": "Synthetic evidence fixture"}],
            "uncertainty": {"status": "review_required"},
        }

    object.__setattr__(app.state.hms_bindings, "ai_evidence", evidence)
    assert (await c.post("/api/v2/hms/ai/patient/" + p["id"])).json()["advisory"] is True
    await create(
        c,
        "ai/reviews",
        dict(
            patient_id=p["id"],
            evidence_id="test-evidence",
            decision="abstain",
            comment="Human review",
        ),
    )
    await create(
        c,
        "ai/reviews",
        dict(patient_id=p["id"], evidence_id="stale", decision="accept", comment="Wrong evidence"),
        expected=422,
    )


@pytest.mark.parametrize(
    "kind,data,expected",
    [
        (
            "Encounter",
            dict(id="1", patient_id="p", status="active", started_at="2026-01-01T00:00:00Z"),
            "patient_id",
        ),
        ("Medication", dict(id="1", code="x", name="Synthetic", dosage_form="tablet"), "code"),
        (
            "MedicationRequest",
            dict(
                id="1",
                patient_id="p",
                medication_id="m",
                encounter_id="e",
                directions="Test",
                quantity=1,
            ),
            "patient_id",
        ),
        (
            "ServiceRequest",
            dict(id="1", patient_id="p", encounter_id="e", test_id="t"),
            "catalogue_id",
        ),
        ("Observation", dict(id="1", patient_id="p", code="x", value=4, unit="unit"), "value"),
        (
            "DiagnosticReport",
            dict(id="1", patient_id="p", code="x", impression="Test", result_ids=["r"]),
            "impression",
        ),
        (
            "Appointment",
            dict(
                id="1",
                patient_id="p",
                provider_id="s",
                status="booked",
                start="2026-01-01T00:00:00Z",
                end="2026-01-01T01:00:00Z",
            ),
            "provider_id",
        ),
        (
            "Schedule",
            dict(id="1", provider_id="s", start="2026-01-01T00:00:00Z", end="2026-01-01T01:00:00Z"),
            "provider_id",
        ),
        (
            "Slot",
            dict(id="1", schedule_id="s", start="2026-01-01T00:00:00Z", end="2026-01-01T01:00:00Z"),
            "schedule_id",
        ),
    ],
)
def test_fhir_projections(kind, data, expected):
    encoded = to_fhir(kind, data)
    decoded = from_fhir(encoded)
    assert expected in decoded


def test_fhir_failures_and_bundle():
    for kind in ["Bogus", "Observation", "DiagnosticReport", "Slot"]:
        with pytest.raises(Exception):
            to_fhir(kind, {"id": "1"})
    with pytest.raises(Exception):
        from_fhir({"resourceType": "Bogus"})
    assert from_fhir(to_fhir("Bundle", {"resources": []})) == {"resources": []}


@pytest.mark.asyncio
async def test_role_permissions_are_enforced_server_side(env):
    app, client = env
    binding = app.state.hms_bindings

    async def billing_principal():
        return {"id": "synthetic-billing-clerk", "roles": ["BILLING_CLERK"]}

    app.dependency_overrides[binding.get_current_user] = billing_principal
    metadata = (await client.get("/api/v2/hms/metadata")).json()
    assert "patients" not in metadata["resources"]
    assert "billing/invoices" in metadata["resources"]
    assert not metadata["can_audit"]
    assert (await client.post("/api/v2/hms/patients/query", json={})).status_code == 403
    assert (await client.get("/api/v2/hms/audit")).status_code == 403
    assert (await client.get("/api/v2/hms/finance/reports")).status_code == 403

    async def missing_identity():
        return {"id": "", "roles": []}

    app.dependency_overrides[binding.get_current_user] = missing_identity
    assert (await client.get("/api/v2/hms/metadata")).status_code == 403
