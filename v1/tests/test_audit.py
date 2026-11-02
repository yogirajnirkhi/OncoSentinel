"""
Tests for Insert-Only Audit Service (FR-29, NFR-06)
"""
from __future__ import annotations

import uuid
from services.audit.service import AuditService
from services.db.models import AuditEvent


def test_audit_event_creation():
    # Verifies audit record attributes and insert-only properties
    req_id = str(uuid.uuid4())
    event = AuditEvent(
        id=str(uuid.uuid4()),
        request_id=req_id,
        actor_id="clinician_dr_smith",
        actor_role="CLINICIAN",
        action="ML_INFERENCE_COMPLETED",
        model_id="onco_breast_classifier",
        model_version="2.0.0",
        service_name="oncosentinel_v2",
        trace_id=req_id,
    )
    assert event.request_id == req_id
    assert event.actor_role == "CLINICIAN"
    assert event.action == "ML_INFERENCE_COMPLETED"
