"""
OncoSentinel v2.0 — API Pydantic Schemas
Satisfies: SRS §11 (Data Model Additions), SRS §12 (API Requirements)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Request Context & Ingestion ───────────────────────────────────────────────
class IngestRequest(BaseModel):
    case_id: Optional[str] = None
    modality: str = Field(..., description="ultrasound, ct, mri, histology, cytology, text")
    content_b64: Optional[str] = None
    text_content: Optional[str] = None
    file_name: Optional[str] = None


class IngestResponse(BaseModel):
    request_id: str
    case_id: str
    file_uri: str
    modality: str
    quality_score: float
    quality_flags: list[str]
    quality_passed: bool
    status: str


# ── Full Multimodal Analysis ──────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    case_id: Optional[str] = None
    category_hint: Optional[str] = Field(None, description="breast, kidney, etc.")
    category: Optional[str] = None
    modality: Optional[str] = None
    text_query: Optional[str] = None
    text: Optional[str] = None
    image_b64: Optional[str] = None
    patient_context: Optional[dict[str, Any]] = None


class ExplanationDTO(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    what: str
    where_region: str
    why: list[dict[str, Any]]
    supporting_evidence: list[dict[str, Any]]
    contradicting_evidence: list[dict[str, Any]]
    confidence_narrative: str
    model_evidence_section: str
    guideline_evidence_section: str
    generated_synthesis_section: str
    fidelity_score: float
    robustness_score: float
    localization_score: float
    audit_heatmap_uri: Optional[str] = None


class UncertaintyDTO(BaseModel):
    predictive_uncertainty: float
    data_uncertainty: float
    evidence_uncertainty: Optional[float] = None
    ood_score: float
    aggregate_decision: str  # PASS | REVIEW | ABSTAIN
    reasons: list[str]


class AnalyzeResponse(BaseModel):
    request_id: str
    prediction_id: Optional[str] = None
    case_id: str
    route: str
    category: Optional[str] = None
    top1_class: Optional[str] = None
    top1_confidence: Optional[float] = None
    calibrated_probabilities: Optional[dict[str, float]] = None
    raw_probabilities: Optional[dict[str, float]] = None
    uncertainty: Optional[UncertaintyDTO] = None
    explanation: Optional[ExplanationDTO] = None
    rag_response: Optional[str] = None
    cited_sources: list[str] = Field(default_factory=list)
    evidence_cards: list[dict[str, Any]] = Field(default_factory=list)
    quality_evidence: Optional[dict[str, Any]] = None
    relevance_score: Optional[float] = None
    safety_state: str  # VERIFIED, REVIEW_REQUIRED, ABSTAIN, NO_GROUNDED_ANSWER, TERMINAL_*
    status_message: str


# ── Clinician Review ──────────────────────────────────────────────────────────
class ClinicianReviewRequest(BaseModel):
    action: str = Field(..., description="ACCEPT | REJECT | EDIT | REQUEST_EVIDENCE | ABSTAIN")
    notes: Optional[str] = None
    edited_diagnosis: Optional[str] = None


class ClinicianReviewResponse(BaseModel):
    prediction_id: str
    clinician_action: str
    status: str
    timestamp: datetime


# ── Longitudinal Timeline ────────────────────────────────────────────────────
class TimelineEventCreate(BaseModel):
    event_time: datetime
    event_type: str = Field(..., description="DIAGNOSIS, IMAGING, PATHOLOGY, LABORATORY, TREATMENT, RESPONSE, OUTCOME")
    source: str
    payload: dict[str, Any]
    confidence: Optional[float] = None
    missingness_state: str = Field("PRESENT", description="PRESENT, MISSING, IMPUTED, UNKNOWN")
    references_event_id: Optional[str] = None


class TimelineEventDTO(BaseModel):
    id: str
    case_id: str
    event_time: datetime
    event_type: str
    source: str
    missingness_state: str
    payload: dict[str, Any]
    inserted_at: datetime


class TimelineResponse(BaseModel):
    case_id: str
    total_events: int
    events: list[TimelineEventDTO]
    trajectory_summary: dict[str, Any]


# ── Clinical Outcomes ────────────────────────────────────────────────────────
class OutcomeCreateRequest(BaseModel):
    case_id: str
    study_id: str
    arm: str = Field(..., description="AI_ASSISTED | STANDARD_OF_CARE")
    endpoint: str
    value: dict[str, Any]
    subgroup_metadata: Optional[dict[str, str]] = None


class OutcomeResponse(BaseModel):
    outcome_id: str
    case_id: str
    study_id: str
    adjudication_state: str
    timestamp: datetime


# ── Federated Learning ───────────────────────────────────────────────────────
class FederatedRoundRequest(BaseModel):
    category: str = "breast"
    participating_sites: int = 3


class FederatedRoundResponse(BaseModel):
    round_id: int
    participating_sites: list[str]
    total_local_samples: int
    global_model_version: str
    pre_round_loss: float
    post_round_loss: float
    unseen_site_auc: float
    out_of_site_improvement_pct: float
    status: str


# ── Model Registry & Calibration / Drift ─────────────────────────────────────
class ModelCalibrationResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str
    version: str
    category: str
    calibration_method: str
    temperature_factor: float
    ece_estimate: float
    brier_score: float
    calibration_passed: bool


class ModelDriftResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str
    version: str
    data_drift_score: float
    concept_drift_score: float
    subgroup_drift_detected: bool
    status: str


# ── HMS Imaging & Inference ──────────────────────────────────────────────────
class ImagingScanRequest(BaseModel):
    patient_id: str = Field(..., description="HMS patient UUID")
    encounter_id: str = Field(..., description="HMS encounter UUID")
    radiology_order_id: Optional[str] = Field(
        None, description="HMS radiology order UUID (optional)"
    )
    category: str = Field(..., description="Cancer category (kidney, oral, etc.)")
    modality: str = Field(..., description="Imaging modality (ct, histology, etc.)")
    image_b64: str = Field(..., description="Base64-encoded image bytes")
    text_query: Optional[str] = Field(None, description="Clinical context / query")


class ImagingScanResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    request_id: str
    case_id: str
    patient_id: str
    encounter_id: str
    prediction_id: Optional[str] = None
    route: str
    category: str
    modality: str
    top1_class: Optional[str] = None
    top1_confidence: Optional[float] = None
    calibrated_top1_confidence: Optional[float] = None
    calibrated_probabilities: Optional[dict[str, float]] = None
    raw_probabilities: Optional[dict[str, float]] = None
    uncertainty: Optional[dict[str, Any]] = None
    explanation: Optional[dict[str, Any]] = None
    model_version: Optional[str] = None
    architecture: Optional[str] = None
    image_uri: Optional[str] = None
    radiology_report_id: Optional[str] = None
    radiology_order_id: Optional[str] = None
    quality_score: Optional[float] = None
    quality_passed: Optional[bool] = None
    quality_flags: list[str] = Field(default_factory=list)
    safety_state: str
    status_message: str
    persisted: bool


class ImagingResultItem(BaseModel):
    case_id: str
    patient_id: Optional[str] = None
    encounter_id: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    imaging_studies: list[dict[str, Any]] = Field(default_factory=list)
    inference_results: list[dict[str, Any]] = Field(default_factory=list)


class ImagingResultsResponse(BaseModel):
    patient_id: str
    results: list[ImagingResultItem]
