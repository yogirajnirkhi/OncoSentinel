"""
Tests for HL7 FHIR Interoperability (NFR-13, SRS §6)
Validates bi-directional translation of DiagnosticReport, Observation, and Bundle resources.
"""
from __future__ import annotations

import datetime
from services.interop.fhir_adapter import FHIRAdapter


def test_fhir_parse_diagnostic_report():
    adapter = FHIRAdapter()
    sample_report = {
        "resourceType": "DiagnosticReport",
        "id": "dr-test-001",
        "status": "final",
        "subject": {"reference": "Patient/CASE-BR-2024-8841"},
        "effectiveDateTime": "2024-10-18T10:30:00Z",
        "conclusion": "Breast ultrasound demonstrating 2.1cm irregular hypoechoic mass. BI-RADS 4C.",
        "performer": [{"display": "Hospital Radiology Dept"}],
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                        "code": "RAD",
                        "display": "Radiology",
                    }
                ]
            }
        ],
    }

    parsed = adapter.parse_diagnostic_report(sample_report)
    assert parsed["resource_type"] == "DiagnosticReport"
    assert parsed["case_id"] == "CASE-BR-2024-8841"
    assert "BI-RADS 4C" in parsed["findings"]
    assert parsed["event_type"] == "IMAGING"
    assert parsed["source"] == "Hospital Radiology Dept"


def test_fhir_parse_observation():
    adapter = FHIRAdapter()
    sample_obs = {
        "resourceType": "Observation",
        "id": "obs-biomarker-01",
        "status": "final",
        "subject": {"reference": "Patient/CASE-BR-2024-8841"},
        "effectiveDateTime": "2024-10-18T11:00:00Z",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "85319-2",
                    "display": "HER2 receptor status",
                }
            ]
        },
        "valueCodeableConcept": {
            "coding": [{"code": "260385009", "display": "Negative"}],
            "text": "HER2 Negative (Score 0)",
        },
        "performer": [{"display": "Pathology Core Lab"}],
    }

    parsed = adapter.parse_observation(sample_obs)
    assert parsed["resource_type"] == "Observation"
    assert parsed["case_id"] == "CASE-BR-2024-8841"
    assert "HER2" in parsed["findings"]
    assert parsed["event_type"] == "LABORATORY"


def test_fhir_parse_bundle():
    adapter = FHIRAdapter()
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "DiagnosticReport",
                    "id": "dr-1",
                    "subject": {"reference": "Patient/CASE-01"},
                    "conclusion": "Initial mammography screening.",
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-1",
                    "subject": {"reference": "Patient/CASE-01"},
                    "valueString": "Elevated CA 15-3 level.",
                }
            },
        ],
    }

    items = adapter.parse_bundle(bundle)
    assert len(items) == 2
    assert items[0]["event_type"] == "DIAGNOSIS"
    assert items[1]["event_type"] == "LABORATORY"


def test_fhir_to_diagnostic_report():
    adapter = FHIRAdapter()
    fhir_doc = adapter.to_diagnostic_report(
        prediction_id="pred-test-999",
        case_id="CASE-KD-2024-5512",
        category="kidney",
        top1_class="renal_cell_carcinoma",
        top1_confidence=0.923,
        calibrated_probabilities={"clear_cell_rcc": 0.923, "papillary_rcc": 0.05, "normal": 0.027},
        uncertainty={"predictive_uncertainty": 0.14, "ood_score": 0.08, "safety_state": "PASS"},
        explanation={
            "fidelity_score": 0.91,
            "robustness_score": 0.89,
            "why": [{"concept_id": "cortical_distortion", "salience_score": 0.88}],
            "synthesis": "CT features consistent with stage I clear cell renal cell carcinoma.",
        },
    )

    assert fhir_doc["resourceType"] == "DiagnosticReport"
    assert fhir_doc["status"] == "final"
    assert fhir_doc["subject"]["reference"] == "Patient/CASE-KD-2024-5512"
    assert "clear_cell_rcc (92.3%)" in fhir_doc["conclusion"]
    assert any("ai-uncertainty" in ext.get("url", "") for ext in fhir_doc["extension"])
    assert any("ai-concept-xai" in ext.get("url", "") for ext in fhir_doc["extension"])


def test_fhir_to_observation_bundle():
    adapter = FHIRAdapter()
    events = [
        {
            "id": "ev-01",
            "event_time": "2024-01-15T09:00:00Z",
            "event_type": "DIAGNOSIS",
            "source": "Oncology Clinic",
            "missingness_state": "PRESENT",
            "payload": {"clinical_finding": "Initial presentation with flank mass."},
        },
        {
            "id": "ev-02",
            "event_time": "2024-02-01T14:30:00Z",
            "event_type": "TREATMENT",
            "source": "Surgical Suite",
            "missingness_state": "PRESENT",
            "payload": {"clinical_finding": "Partial robotic nephrectomy completed."},
        },
    ]

    bundle = adapter.to_observation_bundle(case_id="CASE-KD-2024-5512", timeline_events=events)
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert bundle["total"] == 2
    assert len(bundle["entry"]) == 2
    assert bundle["entry"][0]["resource"]["resourceType"] == "Observation"
    assert "flank mass" in bundle["entry"][0]["resource"]["valueString"]
