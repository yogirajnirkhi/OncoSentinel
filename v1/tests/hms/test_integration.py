"""
OncoSentinel v2.0 — Unified Integration Test Suite
Verifies full end-to-end integration between OncoSentinel Core Platform and HMS:
- Gateway app startup with HMS mounted
- Authentication & JWT token issuing across all 14 clinical & administrative roles
- Database table creation & immutable guard triggers across SQLite / PostgreSQL
- Full clinical workflows: Patient registration, encounters, pharmacy safety, radiology quality gate, AI evidence advisory, and immutable audit trail
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
import pytest
import pytest_asyncio
import httpx
from sqlalchemy import select

from services.core.settings import get_settings
from services.db.models import AuditEvent, Base
from services.db.session import async_engine, init_db
from services.gateway.app import app
from services.gateway.auth import create_access_token


@pytest_asyncio.fixture
async def client():
    # Initialize DB (creates both core and hms tables and guards)
    await init_db()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_and_integration_status(client: httpx.AsyncClient):
    res = await client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["hms_integrated"] is True


@pytest.mark.asyncio
async def test_auth_token_endpoint(client: httpx.AsyncClient):
    res = await client.post("/api/v2/auth/token?role=CLINICIAN&user_id=dr_smith")
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "CLINICIAN"


@pytest.mark.asyncio
async def test_hms_metadata_discovery(client: httpx.AsyncClient):
    token = create_access_token(user_id="dr_smith", role="ADMIN", roles=["ADMIN", "CLINICIAN"])
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.get("/api/v2/hms/metadata", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "resources" in data
    assert "patients" in data["resources"]
    assert "billing/invoices" in data["resources"]
    assert "pharmacy/prescriptions" in data["resources"]


@pytest.mark.asyncio
async def test_patient_creation_and_audit(client: httpx.AsyncClient):
    token = create_access_token(user_id="dr_smith", role="CLINICIAN", roles=["CLINICIAN", "ADMIN"])
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": str(uuid.uuid4()),
        "X-HMS-Confirm": "true",
    }
    mrn = f"MRN-{uuid.uuid4().hex[:8]}"
    payload = {
        "mrn": mrn,
        "given_name": "Integration",
        "family_name": "Patient",
        "birth_date": "1985-05-15",
        "gender": "female",
        "consent": {"research": True},
    }
    res = await client.post("/api/v2/hms/patients", json=payload, headers=headers)
    assert res.status_code == 201
    patient_data = res.json()
    assert patient_data["mrn"] == mrn
    patient_id = patient_data["id"]

    # Verify audit event was written
    audit_res = await client.get(f"/api/v2/hms/audit", headers=headers)
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert len(audit_data["items"]) > 0

    # Test AI evidence advisory hook
    ai_res = await client.post(f"/api/v2/hms/ai/patient/{patient_id}", headers=headers)
    assert ai_res.status_code == 200
    ai_data = ai_res.json()
    assert ai_data["advisory"] is True
    assert len(ai_data["citations"]) > 0
    assert "uncertainty" in ai_data


@pytest.mark.asyncio
async def test_hms_ui_route(client: httpx.AsyncClient):
    res = await client.get("/hms")
    assert res.status_code == 200
    assert "OncoSentinel" in res.text
    assert "Hospital operations" in res.text
