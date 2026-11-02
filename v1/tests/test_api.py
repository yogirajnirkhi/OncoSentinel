"""
Integration tests for FastAPI Gateway endpoints (SRS §12)
"""
from __future__ import annotations

import base64
import pytest
from httpx import ASGITransport, AsyncClient

from services.gateway.app import app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"


@pytest.mark.asyncio
async def test_taxonomy_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v2/taxonomy")
        assert res.status_code == 200
        data = res.json()
        assert "categories" in data
        assert "breast" in data["categories"]
        assert "kidney" in data["categories"]


@pytest.mark.asyncio
async def test_models_list_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v2/models")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 8


@pytest.mark.asyncio
async def test_analyze_rag_route():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "category_hint": "breast",
            "text_query": "What are the NCCN guidelines for breast biopsy?",
        }
        res = await client.post("/api/v2/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["route"] == "RAG_RETRIEVAL"
        assert len(data["rag_response"]) > 0
        assert len(data["cited_sources"]) > 0


@pytest.mark.asyncio
async def test_analyze_ml_route(sample_image_bytes):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        b64_img = base64.b64encode(sample_image_bytes).decode("utf-8")
        payload = {
            "category_hint": "kidney",
            "modality": "ct",
            "text_query": "Evaluate renal cortical mass on contrast CT.",
            "image_b64": b64_img,
        }
        res = await client.post("/api/v2/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["route"] == "ML_INFERENCE"
        assert data["top1_class"] in ["normal", "tumor"]
        assert data["uncertainty"]["aggregate_decision"] in ["PASS", "REVIEW", "ABSTAIN"]
        assert data["explanation"] is not None
        assert len(data["explanation"]["why"]) > 0


@pytest.mark.asyncio
async def test_analyze_ml_oral_route(sample_image_bytes):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        b64_img = base64.b64encode(sample_image_bytes).decode("utf-8")
        payload = {
            "category_hint": "oral",
            "modality": "histology",
            "text_query": "Evaluate oral squamous biopsy histology.",
            "image_b64": b64_img,
        }
        res = await client.post("/api/v2/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["route"] == "ML_INFERENCE"
        assert data["top1_class"] in ["normal", "oscc"]
        assert data["uncertainty"]["aggregate_decision"] in ["PASS", "REVIEW", "ABSTAIN"]


@pytest.mark.asyncio
async def test_analyze_ml_untrained_refusal(sample_image_bytes):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        b64_img = base64.b64encode(sample_image_bytes).decode("utf-8")
        payload = {
            "category_hint": "breast",
            "modality": "ultrasound",
            "text_query": "Evaluate breast ultrasound scan.",
            "image_b64": b64_img,
        }
        res = await client.post("/api/v2/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["route"] == "TERMINAL_MODEL_UNTRAINED"
        assert data["safety_state"] == "SAFE_FAIL_TERMINAL"
        assert "UNTRAINED" in data["status_message"]


@pytest.mark.asyncio
async def test_uncertainty_unknown_id_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v2/predictions/nonexistent_12345/uncertainty")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_clinician_review_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "action": "ACCEPT",
            "notes": "Clinician confirmed finding concordant with imaging.",
        }
        res = await client.post("/api/v2/predictions/test_pred_01/review", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["clinician_action"] == "ACCEPT"
        assert data["status"] == "RECORDED"


@pytest.mark.asyncio
async def test_federated_round_endpoint():
    from services.gateway.auth import create_access_token
    token = create_access_token(user_id="test_researcher", role="RESEARCHER")
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "category": "breast",
            "participating_sites": 3,
        }
        res = await client.post("/api/v2/federated/rounds", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert data["unseen_site_auc"] >= 0.88



@pytest.mark.asyncio
async def test_fhir_diagnostic_report_inbound_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sample_fhir = {
            "resourceType": "DiagnosticReport",
            "id": "dr-api-test-01",
            "status": "final",
            "subject": {"reference": "Patient/CASE-BR-2024-8841"},
            "effectiveDateTime": "2024-10-18T12:00:00Z",
            "conclusion": "Mammography: dense fibroglandular parenchyma with architectural distortion.",
            "performer": [{"display": "Hospital Radiology PACS"}],
        }
        res = await client.post("/api/v2/interop/fhir/diagnostic-report", json=sample_fhir)
        assert res.status_code == 200
        data = res.json()
        assert data["resource_type"] == "DiagnosticReport"
        assert data["case_id"] == "CASE-BR-2024-8841"
        assert "Mammography" in data["findings"]


@pytest.mark.asyncio
async def test_fhir_timeline_export_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v2/interop/fhir/timeline/CASE-BR-2024-8841")
        assert res.status_code == 200
        data = res.json()
        assert data["resourceType"] == "Bundle"
        assert data["type"] == "collection"
        assert "entry" in data


@pytest.mark.asyncio
async def test_training_queue_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v2/training/queue")
        assert res.status_code == 200
        data = res.json()
        assert data["total_tasks"] == 8
        assert data["evaluated_tasks"] >= 2
        assert any(t["task_id"] == "breast_ultrasound" for t in data["tasks"])


@pytest.mark.asyncio
async def test_model_card_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v2/model-cards/breast_ultrasound")
        assert res.status_code == 200
        data = res.json()
        assert data["task_id"] == "breast_ultrasound"
        assert "Model Card" in data["model_card_markdown"]
        assert "Intended Use" in data["model_card_markdown"]


@pytest.mark.asyncio
async def test_decisions_log_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v2/decisions")
        assert res.status_code == 200
        data = res.json()
        assert "ADR-08" in data["decisions_markdown"]
        assert "ADR-12" in data["decisions_markdown"]


@pytest.mark.asyncio
async def test_faculty_briefing_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v2/faculty/briefing")
        assert res.status_code == 200
        data = res.json()
        assert data["audit_date"] == "2026-10-20"
        assert "Hybrid Shared Network" in data["selected_architecture"]
        assert data["portfolio"]["total_tasks"] == 8
        assert data["test_suite_status"]["passed"] >= 58
        assert len(data["phase_readiness"]) == 6
        assert len(data["governance_guarantees"]) >= 4



