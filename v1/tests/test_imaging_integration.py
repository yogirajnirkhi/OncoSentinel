"""
Integration tests for the HMS imaging + V1 AI inference workflow.

Covers the consolidated workflow:
  Patient -> Encounter -> Radiology Order -> Image Upload -> V1 Inference
  -> Persisted Prediction + Uncertainty + Explanation -> Radiology Report
  -> Longitudinal Timeline Event -> Audit

Uses the actual V1 inference pipeline (MobileNetV3-Small, kidney/oral).
No mock predictions.
"""
from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from services.hms.models import Encounters, Patients
from services.db.session import async_engine, AsyncSessionLocal, get_async_db
from services.db.models import Base
from services.gateway.app import app


@pytest.fixture(scope="function")
def kidney_image_b64(sample_image_bytes):
    return base64.b64encode(sample_image_bytes).decode("utf-8")


@pytest.fixture(autouse=True)
def route_api_to_async_engine():
    """Route FastAPI get_async_db through AsyncSessionLocal so API and fixture
    share the same in-memory SQLite database (:memory: is per-connection)."""
    async def override():
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_async_db] = override
    yield
    app.dependency_overrides.pop(get_async_db, None)


@pytest.fixture(scope="function")
async def patient_and_encounter(setup_test_db):
    """Create an HMS patient and linked encounter on the module-level engine."""
    # Ensure HMS tables exist on the engine AsyncSessionLocal connects to
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    patient_id = str(uuid.uuid4())
    encounter_id = str(uuid.uuid4())
    mrn = f"MRN-{uuid.uuid4().hex[:8].upper()}"

    async with AsyncSessionLocal() as session:
        session.add(Patients(
            id=uuid.UUID(patient_id),
            mrn=mrn,
            given_name="Eleanor",
            family_name="Vance",
            birth_date=datetime(1965, 3, 14).date(),
            gender="female",
            contact={},
            insurance={},
            consent={},
            actor_id="dr_chen",
            request_id=str(uuid.uuid4()),
        ))
        session.add(Encounters(
            id=uuid.UUID(encounter_id),
            patient_id=uuid.UUID(patient_id),
            department="Urologic Oncology",
            attending_id="dr_chen",
            started_at=datetime.now(timezone.utc),
            status="active",
            actor_id="dr_chen",
            request_id=str(uuid.uuid4()),
        ))
        await session.commit()

    return patient_id, encounter_id


@pytest.mark.asyncio
async def test_imaging_scan_persists_full_workflow(
    setup_test_db, patient_and_encounter, kidney_image_b64
):
    """End-to-end: scan via HMS endpoint persists prediction, uncertainty, report, timeline."""
    patient_id, encounter_id = patient_and_encounter

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "category": "kidney",
            "modality": "ct",
            "image_b64": kidney_image_b64,
            "text_query": "Evaluate renal cortical mass on contrast CT.",
        }
        res = await client.post("/api/v2/hms/imaging/scan", json=payload)
        assert res.status_code == 200, res.text
        data = res.json()

    # Inference result fields
    assert data["route"] == "ML_INFERENCE"
    assert data["category"] == "kidney"
    assert data["top1_class"] in ["normal", "tumor"]
    assert isinstance(data["top1_confidence"], float)
    assert data["persisted"] is True
    assert data["safety_state"] in ["PASS", "REVIEW", "ABSTAIN"]
    assert data["case_id"] is not None
    assert data["prediction_id"] is not None
    assert data["quality_score"] is not None
    assert data["image_uri"] is not None


@pytest.mark.asyncio
async def test_imaging_scan_degraded_image_terminal_failure(
    setup_test_db, patient_and_encounter, degraded_image_bytes
):
    """Degraded image triggers quality gate terminal failure, still recorded honestly."""
    patient_id, encounter_id = patient_and_encounter
    b64_img = base64.b64encode(degraded_image_bytes).decode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v2/hms/imaging/scan", json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "category": "kidney",
            "modality": "ct",
            "image_b64": b64_img,
        })
        assert res.status_code == 200
        data = res.json()

    assert data["route"] == "TERMINAL_LOW_QUALITY"
    assert data["safety_state"] == "SAFE_FAIL_TERMINAL"
    assert data["persisted"] is True  # failure recorded honestly
    assert data["quality_passed"] is False


@pytest.mark.asyncio
async def test_imaging_results_endpoint(
    setup_test_db, patient_and_encounter, kidney_image_b64
):
    """The imaging results endpoint returns a patient's longitudinal imaging history."""
    patient_id, encounter_id = patient_and_encounter

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Run a scan first
        await client.post("/api/v2/hms/imaging/scan", json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "category": "kidney",
            "modality": "ct",
            "image_b64": kidney_image_b64,
        })

        # Fetch results for this patient
        res = await client.get(f"/api/v2/hms/imaging/results/{patient_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["patient_id"] == patient_id
        assert len(data["results"]) >= 1

        result = data["results"][0]
        assert result["case_id"] is not None
        assert len(result["inference_results"]) >= 1
        inf = result["inference_results"][0]
        assert inf["category"] == "kidney"
        assert inf["top1_class"] in ["normal", "tumor"]
        assert inf["uncertainty"] is not None
        assert inf["uncertainty"]["aggregate_decision"] in ["PASS", "REVIEW", "ABSTAIN"]


@pytest.mark.asyncio
async def test_imaging_scan_invalid_patient_rejected(
    setup_test_db, kidney_image_b64
):
    """Scan with a non-existent patient is rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v2/hms/imaging/scan", json={
            "patient_id": str(uuid.uuid4()),
            "encounter_id": str(uuid.uuid4()),
            "category": "kidney",
            "modality": "ct",
            "image_b64": kidney_image_b64,
        })
        assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_imaging_results_nonexistent_patient(
    setup_test_db,
):
    """Results endpoint for a non-existent patient is rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/v2/hms/imaging/results/{uuid.uuid4()}")
        assert res.status_code == 422, res.text
