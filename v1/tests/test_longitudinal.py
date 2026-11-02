"""
Tests for Longitudinal Patient Modeling & Timeline Integrity (FR-16, FR-17, NFR-09)
"""
from __future__ import annotations

import datetime
from services.db.models import PatientTimelineEvent
from services.longitudinal.trajectory_features import TrajectoryFeatureExtractor


def test_trajectory_feature_extraction():
    extractor = TrajectoryFeatureExtractor()
    now = datetime.datetime.utcnow()

    # Create synthetic events
    e1 = PatientTimelineEvent(
        id="e1",
        case_id="case_101",
        event_time=now - datetime.timedelta(days=120),
        event_type="DIAGNOSIS",
        source="clinic",
        missingness_state="PRESENT",
        payload_json={"diagnosis": "Invasive ductal carcinoma"},
    )
    e2 = PatientTimelineEvent(
        id="e2",
        case_id="case_101",
        event_time=now - datetime.timedelta(days=90),
        event_type="TREATMENT",
        source="oncology",
        missingness_state="PRESENT",
        payload_json={"treatment_name": "Paclitaxel Chemotherapy"},
    )
    e3 = PatientTimelineEvent(
        id="e3",
        case_id="case_101",
        event_time=now,
        event_type="IMAGING",
        source="radiology",
        missingness_state="PRESENT",
        payload_json={"response": "Partial response"},
    )

    summary = extractor.extract_trajectory(case_id="case_101", events=[e1, e2, e3])
    assert summary.total_events == 3
    assert summary.disease_duration_days >= 119
    assert len(summary.prior_treatments) == 1
    assert "Paclitaxel" in summary.prior_treatments[0]
