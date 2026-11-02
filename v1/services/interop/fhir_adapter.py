"""
OncoSentinel v2.0 — HL7 FHIR Interoperability Adapter
Satisfies: NFR-13 (Interoperability: PACS/RIS/LIS/FHIR/HL7 integration)
Grounded in: Architecture v2.0 §10 & SRS §1.3 (Standards-oriented integration path)
"""
from __future__ import annotations

import base64
import uuid
from datetime import datetime
from typing import Any, Optional

from services.core.logging import get_logger

logger = get_logger(__name__)


class FHIRAdapter:
    """
    Bi-directional adapter between standard HL7 FHIR R4 resources
    (DiagnosticReport, Observation, Bundle) and OncoSentinel data representations.
    """

    def __init__(self) -> None:
        self.system_loinc = "http://loinc.org"
        self.system_snomed = "http://snomed.info/sct"
        self.system_onco = "http://oncosentinel.org/fhir/StructureDefinition"

    # ── Inbound Parsing: FHIR -> OncoSentinel ─────────────────────────────────

    def parse_diagnostic_report(self, fhir_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Parses an incoming FHIR DiagnosticReport resource into an OncoSentinel
        multimodal analysis payload.
        """
        if fhir_dict.get("resourceType") != "DiagnosticReport":
            raise ValueError(f"Expected DiagnosticReport, got '{fhir_dict.get('resourceType')}'")

        # Extract subject/patient
        subject_ref = fhir_dict.get("subject", {}).get("reference", "")
        case_id = subject_ref.replace("Patient/", "") if subject_ref else f"case_{uuid.uuid4().hex[:8]}"

        # Extract modality from category or coding
        modality = "ultrasound"
        category_entries = fhir_dict.get("category", [])
        for entry in category_entries:
            for coding in entry.get("coding", []):
                code = coding.get("code", "").lower()
                display = coding.get("display", "").lower()
                for mod in ["ultrasound", "ct", "mri", "histology", "cytology"]:
                    if mod in code or mod in display:
                        modality = mod
                        break

        # Extract text / clinical findings
        conclusion = fhir_dict.get("conclusion", "")
        text_query = conclusion

        # Extract image if attached in presentedForm
        image_b64 = None
        for form in fhir_dict.get("presentedForm", []):
            content_type = form.get("contentType", "")
            if "image" in content_type or "octet-stream" in content_type:
                image_b64 = form.get("data")
                break
            elif "text" in content_type and not text_query:
                # Decode text
                data = form.get("data")
                if data:
                    try:
                        text_query = base64.b64decode(data).decode("utf-8")
                    except Exception:
                        pass

        # Extract category hint from code
        category_hint = None
        code_coding = fhir_dict.get("code", {}).get("coding", [])
        for c in code_coding:
            text = (c.get("display", "") + " " + c.get("code", "")).lower()
            for cat in [
                "breast", "kidney", "all_leukemia", "oral",
                "lung_colon", "lymphoma", "brain", "cervical"
            ]:
                if cat in text:
                    category_hint = cat
                    break

        findings = conclusion
        event_type = "DIAGNOSIS" if ("screening" in conclusion.lower() or "biopsy" in conclusion.lower() or "diagnosis" in conclusion.lower()) else "IMAGING"

        return {
            "resource_type": "DiagnosticReport",
            "case_id": case_id,
            "category_hint": category_hint,
            "modality": modality,
            "text_query": text_query,
            "findings": findings,
            "event_type": event_type,
            "source": fhir_dict.get("performer", [{}])[0].get("display", "Hospital Radiology Dept"),
            "image_b64": image_b64,
            "patient_context": {
                "source": "HL7_FHIR_R4",
                "fhir_id": fhir_dict.get("id"),
                "status": fhir_dict.get("status"),
                "issued": fhir_dict.get("issued") or fhir_dict.get("effectiveDateTime"),
            },
        }

    def parse_observation(self, fhir_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Parses an incoming FHIR Observation resource into a PatientTimelineEvent payload.
        Maps missingness states explicitly (FR-16).
        """
        if fhir_dict.get("resourceType") != "Observation":
            raise ValueError(f"Expected Observation, got '{fhir_dict.get('resourceType')}'")

        subject_ref = fhir_dict.get("subject", {}).get("reference", "")
        case_id = subject_ref.replace("Patient/", "") if subject_ref else "unknown_patient"

        # Determine missingness
        missingness = "PRESENT"
        if "dataAbsentReason" in fhir_dict:
            dar = fhir_dict["dataAbsentReason"].get("coding", [{}])[0].get("code", "unknown")
            missingness = "MISSING" if dar != "unsupported" else "UNKNOWN"

        # Determine event type
        event_type = "LABORATORY"
        code_entries = fhir_dict.get("code", {}).get("coding", [])
        display = code_entries[0].get("display", "Clinical Observation") if code_entries else "Observation"
        code_val = code_entries[0].get("code", "UNKNOWN") if code_entries else "UNKNOWN"

        # Parse value
        val_payload: dict[str, Any] = {"test_name": display, "code": code_val}
        if "valueQuantity" in fhir_dict:
            vq = fhir_dict["valueQuantity"]
            val_payload["value"] = vq.get("value")
            val_payload["unit"] = vq.get("unit")
        elif "valueString" in fhir_dict:
            val_payload["value"] = fhir_dict["valueString"]
        elif "valueCodeableConcept" in fhir_dict:
            vcc = fhir_dict["valueCodeableConcept"].get("coding", [{}])[0]
            val_payload["value"] = vcc.get("display") or vcc.get("code")

        effective_time = fhir_dict.get("effectiveDateTime")
        event_time = (
            datetime.fromisoformat(effective_time.replace("Z", "+00:00"))
            if effective_time
            else datetime.utcnow()
        )

        findings = fhir_dict.get("valueCodeableConcept", {}).get("text") or str(val_payload.get("value", ""))
        if not findings or findings == "None":
            findings = fhir_dict.get("valueString") or display

        return {
            "resource_type": "Observation",
            "case_id": case_id,
            "event_time": event_time,
            "event_type": event_type,
            "findings": findings,
            "source": fhir_dict.get("performer", [{}])[0].get("display", "Hospital LIS/PACS"),
            "missingness_state": missingness,
            "payload": val_payload,
        }

    def parse_bundle(self, bundle_dict: dict[str, Any]) -> list[dict[str, Any]]:
        """Parses a FHIR Bundle into a list of parsed resource payloads."""
        if bundle_dict.get("resourceType") != "Bundle":
            raise ValueError(f"Expected Bundle, got '{bundle_dict.get('resourceType')}'")

        parsed_items: list[dict[str, Any]] = []
        for entry in bundle_dict.get("entry", []):
            res = entry.get("resource", {})
            rtype = res.get("resourceType")
            if rtype == "DiagnosticReport":
                parsed = self.parse_diagnostic_report(res)
                parsed["event_type"] = "DIAGNOSIS"
                parsed_items.append(parsed)
            elif rtype == "Observation":
                parsed = self.parse_observation(res)
                parsed["event_type"] = "LABORATORY"
                parsed_items.append(parsed)
        return parsed_items


    # ── Outbound Export: OncoSentinel -> FHIR R4 ──────────────────────────────

    def export_diagnostic_report(
        self,
        request_id: str,
        case_id: str,
        category: str,
        top1_class: str,
        top1_confidence: float,
        calibrated_probabilities: dict[str, float],
        safety_state: str,
        uncertainty: Optional[dict[str, Any]] = None,
        explanation: Optional[dict[str, Any]] = None,
        narrative_synthesis: Optional[str] = None,
        status: str = "preliminary",
    ) -> dict[str, Any]:
        """
        Exports an OncoSentinel multimodal analysis output into a valid
        HL7 FHIR R4 DiagnosticReport resource.
        """
        now_iso = datetime.utcnow().isoformat() + "Z"

        # Extensions for AI decision support & XAI
        extensions: list[dict[str, Any]] = [
            {
                "url": f"{self.system_onco}/ai-decision",
                "valueString": safety_state,
            },
            {
                "url": f"{self.system_onco}/top1-confidence",
                "valueDecimal": round(top1_confidence, 4),
            },
        ]

        if uncertainty:
            extensions.append({
                "url": f"{self.system_onco}/predictive-entropy",
                "valueDecimal": round(uncertainty.get("predictive_uncertainty", 0.0), 4),
            })
            extensions.append({
                "url": f"{self.system_onco}/ood-score",
                "valueDecimal": round(uncertainty.get("ood_score", 0.0), 4),
            })

        if explanation:
            concepts = [
                f"{c.get('display_name', '')}: {c.get('clinical_observation', '')}"
                for c in explanation.get("why", [])
            ]
            extensions.append({
                "url": f"{self.system_onco}/xai-concepts",
                "valueString": " | ".join(concepts[:5]),
            })

        # Encapsulate synthesized clinical narrative
        synthesis_text = (
            narrative_synthesis
            or f"AI Impression: {top1_class.upper()} ({top1_confidence * 100:.1f}% calibrated confidence). "
            f"Safety decision gate: {safety_state}."
        )

        b64_narrative = base64.b64encode(synthesis_text.encode("utf-8")).decode("utf-8")

        return {
            "resourceType": "DiagnosticReport",
            "id": request_id,
            "meta": {
                "profile": ["http://hl7.org/fhir/StructureDefinition/DiagnosticReport"],
                "versionId": "2.0.0",
                "lastUpdated": now_iso,
            },
            "extension": extensions,
            "status": status,
            "category": [
                {
                    "coding": [
                        {
                            "system": self.system_snomed,
                            "code": "394592004",
                            "display": "Clinical oncology specialty",
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": self.system_loinc,
                        "code": "81247-9",
                        "display": "Master oncology diagnostic report",
                    }
                ],
                "text": f"OncoSentinel v2.0 {category.title()} Cancer AI Diagnostic Assessment",
            },
            "subject": {"reference": f"Patient/{case_id}"},
            "effectiveDateTime": now_iso,
            "issued": now_iso,
            "performer": [
                {
                    "display": "OncoSentinel v2.0 Decision Support Engine",
                }
            ],
            "conclusion": f"Diagnostic Assessment: {top1_class.upper()} ({top1_confidence * 100:.1f}% confidence). Decision: {safety_state}.",
            "conclusionCode": [
                {
                    "coding": [
                        {
                            "system": self.system_onco,
                            "code": top1_class,
                            "display": top1_class.replace("_", " ").title(),
                        }
                    ]
                }
            ],
            "presentedForm": [
                {
                    "contentType": "text/markdown",
                    "data": b64_narrative,
                    "title": "OncoSentinel Tri-Part Clinical Synthesis Report",
                }
            ],
        }

    def export_timeline_as_bundle(self, case_id: str, events: list[Any]) -> dict[str, Any]:
        """
        Exports a case's longitudinal timeline events into a FHIR R4
        collection Bundle of Observation resources.
        """
        now_iso = datetime.utcnow().isoformat() + "Z"
        entries = []

        for e in events:
            event_id = getattr(e, "id", str(uuid.uuid4()))
            event_time = getattr(e, "event_time", datetime.utcnow())
            event_type = getattr(e, "event_type", "OBSERVATION")
            source = getattr(e, "source", "OncoSentinel")
            payload = getattr(e, "payload_json", {}) if hasattr(e, "payload_json") else getattr(e, "payload", {})

            time_iso = event_time.isoformat() + ("Z" if not str(event_time).endswith("Z") else "")

            obs = {
                "resourceType": "Observation",
                "id": event_id,
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": event_type.lower(),
                                "display": event_type.title(),
                            }
                        ]
                    }
                ],
                "code": {
                    "text": payload.get("test_name") or f"{event_type} Event",
                },
                "subject": {"reference": f"Patient/{case_id}"},
                "effectiveDateTime": time_iso,
                "performer": [{"display": source}],
                "valueString": str(payload.get("value") or payload),
            }

            entries.append({"resource": obs})

        return {
            "resourceType": "Bundle",
            "id": f"bundle_timeline_{case_id}",
            "type": "collection",
            "timestamp": now_iso,
            "total": len(entries),
            "entry": entries,
        }

    def to_diagnostic_report(
        self,
        prediction_id: str,
        case_id: str,
        category: str,
        top1_class: str,
        top1_confidence: float,
        calibrated_probabilities: dict[str, float],
        uncertainty: Optional[dict[str, Any]] = None,
        explanation: Optional[dict[str, Any]] = None,
        safety_state: str = "PASS",
        status: str = "final",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Convenience method matching FHIR export test signature."""
        now_iso = datetime.utcnow().isoformat() + "Z"
        extensions: list[dict[str, Any]] = [
            {"url": f"{self.system_onco}/ai-decision", "valueString": safety_state},
            {"url": f"{self.system_onco}/top1-confidence", "valueDecimal": round(top1_confidence, 4)},
        ]
        if uncertainty:
            extensions.append({
                "url": f"{self.system_onco}/ai-uncertainty",
                "valueDecimal": round(uncertainty.get("predictive_uncertainty", 0.0), 4),
            })
            extensions.append({
                "url": f"{self.system_onco}/ood-score",
                "valueDecimal": round(uncertainty.get("ood_score", 0.0), 4),
            })
        if explanation:
            extensions.append({
                "url": f"{self.system_onco}/ai-concept-xai",
                "valueString": str(explanation.get("why", [])),
            })

        best_class = max(calibrated_probabilities, key=calibrated_probabilities.get) if calibrated_probabilities else top1_class
        conclusion = f"Primary finding: {best_class} ({top1_confidence * 100:.1f}%). Status: {safety_state}."


        return {
            "resourceType": "DiagnosticReport",
            "id": prediction_id,
            "status": status,
            "subject": {"reference": f"Patient/{case_id}"},
            "effectiveDateTime": now_iso,
            "conclusion": conclusion,
            "extension": extensions,
        }

    def to_observation_bundle(
        self,
        case_id: str,
        timeline_events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Exports timeline events as an HL7 FHIR Bundle of Observations."""
        entries = []
        for e in timeline_events:
            ev_id = e.get("id", str(uuid.uuid4()))
            payload = e.get("payload", {})
            val = payload.get("clinical_finding") or payload.get("value") or e.get("findings", "")
            obs = {
                "resourceType": "Observation",
                "id": ev_id,
                "status": "final",
                "subject": {"reference": f"Patient/{case_id}"},
                "valueString": str(val),
            }
            entries.append({"resource": obs})
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "total": len(entries),
            "entry": entries,
        }


_fhir_adapter_singleton: Optional[FHIRAdapter] = None



def get_fhir_adapter() -> FHIRAdapter:
    global _fhir_adapter_singleton
    if _fhir_adapter_singleton is None:
        _fhir_adapter_singleton = FHIRAdapter()
    return _fhir_adapter_singleton
