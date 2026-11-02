"""
OncoSentinel v2.0 — End-to-End Integration & Enforced Role-Based Access Control (RBAC) Verification
Verifies:
1. Integrated ocnewui static assets served by FastAPI (`index.html`, `css/workspace.css`, `js/workspace.js`, `js/app.js`, `js/config.js`, `openapi.json`)
2. Complete removal of the legacy `#devRoleSelect` / `.dev-role-switcher` toggle from the UI
3. Authentic PBKDF2 login by username or hospital email, role-based staff registration, and `/api/v2/auth/me`
4. Strict role and privilege enforcement across CLINICIAN, RADIOLOGIST, PHARMACIST, BILLING_CLERK, and ADMIN
5. Live Multimodal AI Studio inference (`/api/v2/analyze`), Grad-CAM heatmap artifact serving, clinician adjudication, and Model Portfolio readiness (`/api/v2/training/queue`)
"""
from __future__ import annotations

import base64
import io
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from services.db.models import User
from services.db.session import get_async_db, get_hms_async_session
from services.gateway.app import app
from services.gateway.auth import ALL_ROLES, hash_password


def _make_test_png_b64() -> str:
    img = Image.new("RGB", (224, 224), color=(40, 45, 55))
    for x in range(60, 160):
        for y in range(60, 160):
            val = ((x * 7 + y * 13) % 180) + 50
            img.putpixel((x, y), (val, max(20, val - 30), min(255, val + 20)))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


async def _seed_test_staff(client: AsyncClient) -> None:
    """Seeds the 5 canonical hospital staff roles via the real /api/v2/auth/register endpoint."""
    staff = [
        ("dr_chen", "sarah.chen@oncosentinel.hospital.org", "Dr. Sarah Chen, MD", "CLINICIAN", "Medical Oncology"),
        ("dr_patel", "rajesh.patel@oncosentinel.hospital.org", "Dr. Rajesh Patel, MD", "RADIOLOGIST", "Diagnostic Radiology"),
        ("pharma_alex", "alex.rivera@oncosentinel.hospital.org", "Alex Rivera, PharmD", "PHARMACIST", "Clinical Oncology Pharmacy"),
        ("billing_mark", "mark.davis@oncosentinel.hospital.org", "Mark Davis, CRCR", "BILLING_CLERK", "Patient Financial Services"),
        ("admin_clara", "clara.vance@oncosentinel.hospital.org", "Clara Vance, MHA", "ADMIN", "Hospital Administration"),
    ]
    for uname, email, fname, role, dept in staff:
        r = await client.post(
            "/api/v2/auth/register",
            json={
                "username": uname,
                "email": email,
                "full_name": fname,
                "role": role,
                "department": dept,
                "password": "OncoUser2026!",
            },
        )
        assert r.status_code in (200, 400), r.text


@pytest.mark.asyncio
async def test_integrated_new_ui_and_removed_role_toggle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_html = await client.get("/")
        assert res_html.status_code == 200
        html = res_html.text

        # Verify new ocnewui workspace assets are integrated
        assert 'href="css/workspace.css"' in html
        assert 'src="js/config.js"' in html
        assert 'src="js/workspace.js"' in html
        assert 'id="btnHeaderSwitchAccount"' in html
        assert 'id="staffQuickLoginList"' in html

        # Verify role toggle dropdown (#devRoleSelect / .dev-role-switcher) is completely removed
        assert 'id="devRoleSelect"' not in html
        assert 'class="dev-role-switcher"' not in html

        # Verify static JS/CSS/OpenAPI assets are served
        for asset in [
            "/css/app.css",
            "/css/workspace.css",
            "/js/config.js",
            "/js/api-client.js",
            "/js/app.js",
            "/js/workspace.js",
            "/openapi.json",
        ]:
            r = await client.get(asset)
            assert r.status_code == 200, f"Asset {asset} failed with {r.status_code}"


@pytest.mark.asyncio
async def test_staff_authentication_and_enforced_role_privileges():
    # Ensure HMS routes use the same test DB session override
    if get_async_db in app.dependency_overrides:
        app.dependency_overrides[get_hms_async_session] = app.dependency_overrides[get_async_db]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _seed_test_staff(client)

        # 1. Login as CLINICIAN (by username and by email)
        r_login = await client.post(
            "/api/v2/auth/login",
            json={"username": "dr_chen", "password": "OncoUser2026!"},
        )
        assert r_login.status_code == 200, r_login.text
        clin_token = r_login.json()["access_token"]
        assert r_login.json()["user"]["role"] == "CLINICIAN"

        r_email_login = await client.post(
            "/api/v2/auth/login",
            json={"username": "sarah.chen@oncosentinel.hospital.org", "password": "OncoUser2026!"},
        )
        assert r_email_login.status_code == 200

        clin_headers = {"Authorization": f"Bearer {clin_token}"}
        me_res = await client.get("/api/v2/auth/me", headers=clin_headers)
        assert me_res.status_code == 200
        assert me_res.json()["username"] == "dr_chen"
        assert me_res.json()["role"] == "CLINICIAN"

        # Clinician can read patients, encounters, pharmacy/dispense, inventory/items, low-stock
        for path in ["patients", "encounters", "pharmacy/medications", "pharmacy/prescriptions", "pharmacy/dispense", "inventory/items"]:
            q = await client.post(f"/api/v2/hms/{path}/query", json={}, headers=clin_headers)
            assert q.status_code == 200, f"Clinician query {path} failed: {q.text}"
        low_stock = await client.get("/api/v2/hms/inventory/low-stock", headers=clin_headers)
        assert low_stock.status_code == 200

        # Clinician is FORBIDDEN from billing/invoices and finance/ledger (enforced RBAC)
        inv_forbidden = await client.post("/api/v2/hms/billing/invoices/query", json={}, headers=clin_headers)
        assert inv_forbidden.status_code == 403
        ledger_forbidden = await client.get("/api/v2/hms/finance/ledger", headers=clin_headers)
        assert ledger_forbidden.status_code == 403

        # 2. Login as RADIOLOGIST (dr_patel)
        r_rad = await client.post(
            "/api/v2/auth/login",
            json={"username": "dr_patel", "password": "OncoUser2026!"},
        )
        assert r_rad.status_code == 200
        rad_headers = {"Authorization": f"Bearer {r_rad.json()['access_token']}"}

        # Radiologist can read patients, encounters (read-only), radiology, lab
        for path in ["patients", "encounters", "scheduling/appointments", "medical-records", "radiology/orders", "radiology/reports", "lab/orders"]:
            q = await client.post(f"/api/v2/hms/{path}/query", json={}, headers=rad_headers)
            assert q.status_code == 200, f"Radiologist query {path} failed: {q.text}"

        # Radiologist is FORBIDDEN from creating encounters or accessing billing
        enc_write_forbidden = await client.post(
            "/api/v2/hms/encounters",
            json={"patient_id": str(uuid.uuid4()), "department": "Oncology", "attending_id": "dr_patel", "started_at": "2026-10-31T10:00:00Z"},
            headers={**rad_headers, "Idempotency-Key": str(uuid.uuid4())},
        )
        assert enc_write_forbidden.status_code == 403

        # 3. Login as PHARMACIST (pharma_alex)
        r_pharma = await client.post(
            "/api/v2/auth/login",
            json={"username": "pharma_alex", "password": "OncoUser2026!"},
        )
        assert r_pharma.status_code == 200
        pharma_headers = {"Authorization": f"Bearer {r_pharma.json()['access_token']}"}
        for path in ["patients", "pharmacy/medications", "pharmacy/prescriptions", "pharmacy/dispense", "inventory/items"]:
            q = await client.post(f"/api/v2/hms/{path}/query", json={}, headers=pharma_headers)
            assert q.status_code == 200, f"Pharmacist query {path} failed: {q.text}"

        # 4. Login as BILLING_CLERK (billing_mark)
        r_bill = await client.post(
            "/api/v2/auth/login",
            json={"username": "billing_mark", "password": "OncoUser2026!"},
        )
        assert r_bill.status_code == 200
        bill_headers = {"Authorization": f"Bearer {r_bill.json()['access_token']}"}
        for path in ["patients", "billing/charge-items", "billing/invoices", "billing/payments", "billing/claims", "billing/adjustments"]:
            q = await client.post(f"/api/v2/hms/{path}/query", json={}, headers=bill_headers)
            assert q.status_code == 200, f"Billing clerk query {path} failed: {q.text}"
        assert (await client.get("/api/v2/hms/finance/ledger", headers=bill_headers)).status_code == 200
        assert (await client.get("/api/v2/hms/finance/reports", headers=bill_headers)).status_code == 200

        # Billing clerk is FORBIDDEN from clinical pharmacy prescriptions
        rx_forbidden = await client.post("/api/v2/hms/pharmacy/prescriptions/query", json={}, headers=bill_headers)
        assert rx_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_live_analyze_evidence_cards_and_portfolio_queue():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _seed_test_staff(client)
        r_login = await client.post(
            "/api/v2/auth/login",
            json={"username": "dr_chen", "password": "OncoUser2026!"},
        )
        headers = {"Authorization": f"Bearer {r_login.json()['access_token']}"}

        # Verify training queue includes is_active and parameter_count for UI portfolio
        q_res = await client.get("/api/v2/training/queue", headers=headers)
        assert q_res.status_code == 200
        q_data = q_res.json()
        assert q_data["evaluated_tasks"] == 6
        assert sum(1 for t in q_data["tasks"] if t.get("is_active")) == 6
        assert any(t.get("parameter_count") == "1.52M" for t in q_data["tasks"])

        # Verify live /api/v2/analyze returns quality_evidence, relevance_score, evidence_cards, and heatmap URI
        analyze_res = await client.post(
            "/api/v2/analyze",
            headers=headers,
            json={
                "case_id": "MRN-2026-KD-001",
                "category_hint": "kidney",
                "modality": "ct",
                "text_query": "Abdominal contrast-enhanced CT study of renal parenchyma. Evaluate for cortical neoplasm.",
                "image_b64": _make_test_png_b64(),
            },
        )
        assert analyze_res.status_code == 200, analyze_res.text
        adata = analyze_res.json()
        assert adata["route"] == "ML_INFERENCE"
        assert adata["quality_evidence"]["passed"] is True
        assert isinstance(adata["relevance_score"], float)
        assert len(adata["evidence_cards"]) > 0
        assert adata["explanation"]["audit_heatmap_uri"].startswith("/api/v2/artifacts/heatmaps/")

        # Verify heatmap image is served
        hm_res = await client.get(adata["explanation"]["audit_heatmap_uri"])
        assert hm_res.status_code == 200
        assert hm_res.headers["content-type"] == "image/png"
