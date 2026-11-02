"""
OncoSentinel v2.0 — SQLAlchemy ORM Models
Satisfies: FR-16 (append-only timeline), FR-29 (audit trail), SRS §11 data objects

CRITICAL RULES:
- patient_timeline_events: APPEND-ONLY — no UPDATE/DELETE (enforced by trigger + app guard)
- audit_events: INSERT-ONLY — no UPDATE/DELETE (enforced by DB trigger)
- clinical_outcomes: separated schema to prevent training data leakage
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# IDENTITY & RBAC TABLES
# ═══════════════════════════════════════════════════════════════════════════════


class User(Base):
    """
    Authoritative hospital user record for authentication and RBAC.
    Satisfies: NFR-04, SRS §1.4.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    salt: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)  # Primary role
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)  # Assigned privilege roles
    department: Mapped[str] = mapped_column(String(128), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CORE DOMAIN TABLES
# ═══════════════════════════════════════════════════════════════════════════════


class Case(Base):
    """Master case record. FR-01, SRS §11.

    Links a V1 analysis case to the canonical HMS patient and encounter,
    establishing the patient journey: Patient -> Encounter -> Case -> Imaging
    Study -> Inference Job -> Inference Result -> Reviewed Assessment.
    """

    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="active")
    patient_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    encounter_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    # Relationships
    ingestion_events: Mapped[list[IngestionEvent]] = relationship(back_populates="case")
    predictions: Mapped[list[Prediction]] = relationship(back_populates="case")
    timeline_events: Mapped[list[PatientTimelineEvent]] = relationship(back_populates="case")


class Dataset(Base):
    """Dataset registry entry. FR-28, NFR-12."""

    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    license: Mapped[str] = mapped_column(String(64), nullable=False)
    n_train: Mapped[int] = mapped_column(Integer, default=0)
    n_val: Mapped[int] = mapped_column(Integer, default=0)
    n_test: Mapped[int] = mapped_column(Integer, default=0)
    n_external_val: Mapped[int] = mapped_column(Integer, default=0)
    split_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    patient_ids_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    site_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("dataset_id", "version", name="uq_dataset_version"),)


class ModelVersion(Base):
    """Model version registry. FR-28, NFR-12."""

    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    modality: Mapped[list[str]] = mapped_column(JSON, default=list)
    backbone_version: Mapped[str] = mapped_column(String(64), nullable=False)
    calibration_artifact_uri: Mapped[str | None] = mapped_column(Text)
    uncertainty_policy_version: Mapped[str | None] = mapped_column(String(32))
    fairness_report_uri: Mapped[str | None] = mapped_column(Text)
    model_card_uri: Mapped[str | None] = mapped_column(Text)
    xai_eval_uri: Mapped[str | None] = mapped_column(Text)
    rollback_artifact_uri: Mapped[str | None] = mapped_column(Text)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(32),
        default="CANDIDATE",
        nullable=False,
    )
    promotion_gate_results: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("model_id", "version", name="uq_model_version"),
        CheckConstraint(
            "status IN ('CANDIDATE','STAGING','PRODUCTION','ARCHIVED','ROLLED_BACK')",
            name="ck_model_status",
        ),
    )


class IngestionEvent(Base):
    """Each ingest attempt. FR-01."""

    __tablename__ = "ingestion_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    modality: Mapped[str] = mapped_column(String(32), nullable=False)
    file_uri: Mapped[str] = mapped_column(Text, nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float)
    quality_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    ocr_text_uri: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    case: Mapped[Case] = relationship(back_populates="ingestion_events")


class RouterDecision(Base):
    """Router decision record. FR-02, FR-04."""

    __tablename__ = "router_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    route: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64))
    modality_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    intent_label: Mapped[str | None] = mapped_column(String(64))
    cancer_relevance_score: Mapped[float | None] = mapped_column(Float)
    capability_check_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    phase_status: Mapped[str | None] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UncertaintyRecord(Base):
    """Uncertainty record per prediction. FR-05..08."""

    __tablename__ = "uncertainty_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    prediction_id: Mapped[str] = mapped_column(
        ForeignKey("predictions.id"), nullable=False, unique=True
    )
    predictive_uncertainty: Mapped[float] = mapped_column(Float, nullable=False)
    data_uncertainty: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_uncertainty: Mapped[float | None] = mapped_column(Float)
    ood_score: Mapped[float] = mapped_column(Float, nullable=False)
    aggregate_decision: Mapped[str] = mapped_column(String(16), nullable=False)
    threshold_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    calibration_set_version: Mapped[str] = mapped_column(String(32), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_route: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    prediction: Mapped[Prediction] = relationship(back_populates="uncertainty_record")

    __table_args__ = (
        CheckConstraint(
            "aggregate_decision IN ('PASS','REVIEW','ABSTAIN')",
            name="ck_uncertainty_decision",
        ),
    )


class OODRecord(Base):
    """OOD detection record per prediction. FR-08."""

    __tablename__ = "ood_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    prediction_id: Mapped[str] = mapped_column(
        ForeignKey("predictions.id"), nullable=False, unique=True
    )
    mahalanobis_score: Mapped[float] = mapped_column(Float, nullable=False)
    energy_score: Mapped[float] = mapped_column(Float, nullable=False)
    max_softmax_score: Mapped[float] = mapped_column(Float, nullable=False)
    auroc_reference: Mapped[float | None] = mapped_column(Float)
    is_ood: Mapped[bool] = mapped_column(Boolean, nullable=False)
    detector_versions: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    prediction: Mapped[Prediction] = relationship(back_populates="ood_record")


class Prediction(Base):
    """ML prediction — immutable after insert. FR-02..09, SRS §11."""

    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), nullable=False)
    model_version_id: Mapped[str] = mapped_column(ForeignKey("model_versions.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    top1_class: Mapped[str] = mapped_column(String(64), nullable=False)
    top1_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    class_probabilities: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    calibration_set_version: Mapped[str] = mapped_column(String(32), nullable=False)
    longitudinal_context_used: Mapped[bool] = mapped_column(Boolean, default=False)
    authorized_by: Mapped[str | None] = mapped_column(String(64))
    clinician_action: Mapped[str | None] = mapped_column(String(32))
    clinician_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    case: Mapped[Case] = relationship(back_populates="predictions")
    model_version: Mapped[ModelVersion] = relationship()
    uncertainty_record: Mapped[UncertaintyRecord | None] = relationship(back_populates="prediction")
    ood_record: Mapped[OODRecord | None] = relationship(back_populates="prediction")
    explanation: Mapped[Explanation | None] = relationship(back_populates="prediction")
    timeline_influences: Mapped[list[TimelineInfluence]] = relationship(
        back_populates="prediction"
    )


class Explanation(Base):
    """Clinical XAI explanation. FR-13..15."""

    __tablename__ = "explanations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    prediction_id: Mapped[str] = mapped_column(
        ForeignKey("predictions.id"), nullable=False, unique=True
    )
    what: Mapped[str] = mapped_column(Text, nullable=False)
    where_region: Mapped[str | None] = mapped_column(Text)
    why_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    supporting_evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    contradicting_evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    confidence_narrative: Mapped[str] = mapped_column(Text, nullable=False)
    model_evidence_section: Mapped[str] = mapped_column(Text, nullable=False)
    guideline_evidence_section: Mapped[str] = mapped_column(Text, nullable=False)
    generated_synthesis_section: Mapped[str] = mapped_column(Text, nullable=False)
    fidelity_score: Mapped[float | None] = mapped_column(Float)
    robustness_score: Mapped[float | None] = mapped_column(Float)
    localization_score: Mapped[float | None] = mapped_column(Float)
    complexity_score: Mapped[float | None] = mapped_column(Float)
    explanation_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    audit_heatmap_uri: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    prediction: Mapped[Prediction] = relationship(back_populates="explanation")


class PatientTimelineEvent(Base):
    """
    Append-only longitudinal event table. FR-16, FR-17, NFR-09.

    CRITICAL: This table is APPEND-ONLY.
    - No UPDATE or DELETE operations are ever permitted.
    - Corrections are new events that reference the old event via references_event_id.
    - Missingness is EXPLICIT — never treat missing data as absence.
    - A DB-level trigger (see migration) prevents UPDATE/DELETE at the database level.
    """

    __tablename__ = "patient_timeline_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    confidence: Mapped[float | None] = mapped_column(Float)
    missingness_state: Mapped[str] = mapped_column(String(16), nullable=False)
    references_event_id: Mapped[str | None] = mapped_column(String(36), index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    inserted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    case: Mapped[Case] = relationship(back_populates="timeline_events")

    __table_args__ = (
        CheckConstraint(
            "missingness_state IN ('PRESENT','MISSING','IMPUTED','UNKNOWN')",
            name="ck_timeline_missingness",
        ),
        Index("ix_timeline_case_event_time", "case_id", "event_time"),
    )


class TimelineInfluence(Base):
    """Links timeline events to predictions that used them. FR-17."""

    __tablename__ = "timeline_influences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    prediction_id: Mapped[str] = mapped_column(ForeignKey("predictions.id"), nullable=False)
    influence_weight: Mapped[float] = mapped_column(Float, nullable=False)

    prediction: Mapped[Prediction] = relationship(back_populates="timeline_influences")


class FairnessEvaluation(Base):
    """Fairness evaluation record. FR-18, FR-19."""

    __tablename__ = "fairness_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_version_id: Mapped[str] = mapped_column(ForeignKey("model_versions.id"), nullable=False)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), nullable=False)
    strata_config_version: Mapped[str] = mapped_column(String(32), nullable=False)
    gate_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    report_uri: Mapped[str | None] = mapped_column(Text)
    router_rejection_analysis: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    subgroup_metrics: Mapped[list[SubgroupMetrics]] = relationship(
        back_populates="fairness_evaluation"
    )


class SubgroupMetrics(Base):
    """Per-subgroup fairness metrics. FR-18."""

    __tablename__ = "subgroup_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    fairness_eval_id: Mapped[str] = mapped_column(
        ForeignKey("fairness_evaluations.id"), nullable=False
    )
    subgroup_name: Mapped[str] = mapped_column(String(128), nullable=False)
    n_samples: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_size_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    sensitivity: Mapped[float | None] = mapped_column(Float)
    specificity: Mapped[float | None] = mapped_column(Float)
    f1: Mapped[float | None] = mapped_column(Float)
    auc: Mapped[float | None] = mapped_column(Float)
    ece: Mapped[float | None] = mapped_column(Float)
    fnr: Mapped[float | None] = mapped_column(Float)
    fpr: Mapped[float | None] = mapped_column(Float)
    abstention_rate: Mapped[float | None] = mapped_column(Float)
    explanation_utility_score: Mapped[float | None] = mapped_column(Float)
    confidence_intervals: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    fairness_evaluation: Mapped[FairnessEvaluation] = relationship(
        back_populates="subgroup_metrics"
    )


class AuditEvent(Base):
    """
    INSERT-ONLY audit trail. FR-29, NFR-06.

    CRITICAL: No UPDATE or DELETE ever permitted.
    Every route, inference, explanation, review action, and outcome is logged here.
    Traceable by request_id.
    """

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    model_id: Mapped[str | None] = mapped_column(String(64))
    model_version: Mapped[str | None] = mapped_column(String(32))
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    explanation_id: Mapped[str | None] = mapped_column(String(36))
    uncertainty_record_id: Mapped[str | None] = mapped_column(String(36))
    fairness_report_id: Mapped[str | None] = mapped_column(String(36))
    clinician_action: Mapped[str | None] = mapped_column(String(32))
    outcome_id: Mapped[str | None] = mapped_column(String(36))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    service_name: Mapped[str | None] = mapped_column(String(64))
    trace_id: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (Index("ix_audit_request_id", "request_id"),)


# ═══════════════════════════════════════════════════════════════════════════════
# OUTCOMES SCHEMA (isolated from training data)
# ═══════════════════════════════════════════════════════════════════════════════


class Study(Base):
    """Clinical study protocol. FR-21, NFR-10."""

    __tablename__ = "studies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    protocol_version: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    arms: Mapped[list[str]] = mapped_column(JSON, default=list)
    primary_endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    secondary_endpoints: Mapped[list[str]] = mapped_column(JSON, default=list)
    inclusion_criteria: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    exclusion_criteria: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    outcomes: Mapped[list[ClinicalOutcome]] = relationship(back_populates="study")


class ClinicalOutcome(Base):
    """
    Clinical outcome capture. FR-21, NFR-10.
    CRITICAL: This data MUST NEVER be used in model training.
    Enforced by schema separation + application-level guard.
    """

    __tablename__ = "clinical_outcomes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    study_id: Mapped[str] = mapped_column(ForeignKey("studies.id"), nullable=False)
    arm: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(128), nullable=False)
    adjudication_state: Mapped[str] = mapped_column(String(32), default="PENDING")
    adjudicator_id: Mapped[str | None] = mapped_column(String(128))
    subgroup_metadata: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    outcome_value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    study: Mapped[Study] = relationship(back_populates="outcomes")

    __table_args__ = (
        CheckConstraint(
            "adjudication_state IN ('PENDING','ADJUDICATED','DISPUTED')",
            name="ck_outcome_adjudication",
        ),
    )
