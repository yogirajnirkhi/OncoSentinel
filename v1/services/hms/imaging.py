"""
OncoSentinel — HMS Imaging & Inference Workflow
Integrates V1's actual AI scanning pipeline into the HMS diagnostic workflow.

Workflow:
  Patient -> Encounter -> Radiology Study/Order -> Image Upload -> V1 Inference
  -> Persisted Prediction + Uncertainty + Explanation -> Radiology Report
  -> Longitudinal Timeline Event -> Audit

All inference is real V1 model inference (MobileNetV3-Small, kidney/oral).
No mock predictions, no manufactured confidence scores.
"""
from __future__ import annotations

import base64
import io
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import numpy as np
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.core.logging import get_logger
from services.db.models import (
    Case,
    IngestionEvent,
    OODRecord,
    Prediction,
    Prediction as PredictionModel,
    UncertaintyRecord,
    Explanation,
    PatientTimelineEvent,
    AuditEvent,
    ModelVersion,
)
from services.db.session import AsyncSessionLocal
from services.gateway.auth import UserPrincipal
from services.ingestion.storage import get_storage_service
from services.ingestion.validator import ImageQualityValidator
from services.ml.orchestrator import get_ml_orchestrator, MLOrchestrator
from services.ml.adapters.base import UntrainedModelError
from services.router.engine import (
    RouterEngine,
    ROUTE_ML,
    ROUTE_FAIL_QUALITY,
    ROUTE_FAIL_RELEVANCE,
    ROUTE_FAIL_MODALITY,
    ROUTE_FAIL_PHASE,
    ROUTE_FAIL_UNTRAINED,
    ROUTE_RAG,
)
from services.uncertainty.aggregator import get_uncertainty_aggregator
from services.uncertainty.calibration import get_calibration_engine
from services.uncertainty.ood_detector import get_ood_detector
from services.xai.clinical_explainer import get_clinical_explainer
from services.hms.models import (
    Patients,
    Encounters,
    RadiologyStudies,
    RadiologyOrders,
    RadiologyReports,
    MODELS,
)
from services.hms.exceptions import HMSError
from services.audit.service import AuditService

logger = get_logger(__name__)

# Service singletons (shared with gateway routes)
_router_engine = RouterEngine()
_quality_validator = ImageQualityValidator()
_ml_orchestrator = get_ml_orchestrator()
_calibration_engine = get_calibration_engine()
_ood_detector = get_ood_detector()
_uncertainty_aggregator = get_uncertainty_aggregator()
_clinical_explainer = get_clinical_explainer()


class ImagingWorkflowError(HMSError):
    """Raised when the imaging/inference workflow cannot complete safely."""


async def _get_or_create_case(
    session: AsyncSession,
    patient_id: str,
    encounter_id: str,
    actor_id: str,
    request_id: str,
    category: str,
) -> Case:
    """Get existing case for patient/encounter or create a new one."""
    # Look for an existing open case for this patient + encounter
    stmt = select(Case).where(
        Case.patient_id == patient_id,
        Case.encounter_id == encounter_id,
        Case.status == "active",
    )
    result = await session.execute(stmt)
    case = result.scalar_one_or_none()
    if case is not None:
        return case

    case = Case(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        encounter_id=encounter_id,
        status="active",
        metadata_json={
            "source": "hms_imaging_workflow",
            "actor_id": actor_id,
            "request_id": request_id,
            "category": category,
        },
    )
    session.add(case)
    await session.flush()
    return case


async def _persist_prediction(
    session: AsyncSession,
    case: Case,
    request_id: str,
    model_out: Any,
    calib_res: Any,
    unc_summary: Any,
    ood_res: Any,
    explanation: Any,
    category: str,
) -> tuple[str, str, str]:
    """Persist prediction, uncertainty, OOD, and explanation records. Returns (prediction_id, uncertainty_id, explanation_id)."""
    prediction_id = str(uuid.uuid4())
    uncertainty_id = str(uuid.uuid4())
    explanation_id = str(uuid.uuid4())

    # Resolve model version record
    model_version_rec = (
        await session.execute(
            select(ModelVersion).where(
                ModelVersion.category == category,
                ModelVersion.status == "PRODUCTION",
            )
        )
    ).scalar_one_or_none()
    if model_version_rec is None:
        model_version_rec = ModelVersion(
            id=str(uuid.uuid4()),
            model_id=f"onco_{category}_classifier",
            version="v2.0.0",
            category=category,
            modality=[category],
            backbone_version="MobileNetV3-Small",
            status="PRODUCTION",
        )
        session.add(model_version_rec)
        await session.flush()

    class_probs = dict(model_out.class_probabilities)

    prediction = PredictionModel(
        id=prediction_id,
        request_id=request_id,
        case_id=case.id,
        model_version_id=model_version_rec.id,
        category=category,
        top1_class=model_out.top1_class,
        top1_confidence=float(model_out.top1_confidence),
        class_probabilities=class_probs,
        calibration_set_version="policy_v2.0.0",
        longitudinal_context_used=False,
    )
    session.add(prediction)

    uncertainty = UncertaintyRecord(
        id=uncertainty_id,
        prediction_id=prediction_id,
        predictive_uncertainty=float(unc_summary.predictive_uncertainty),
        data_uncertainty=float(unc_summary.data_uncertainty),
        evidence_uncertainty=unc_summary.evidence_uncertainty,
        ood_score=float(unc_summary.ood_score),
        aggregate_decision=unc_summary.aggregate_decision,
        threshold_policy_version=unc_summary.threshold_policy_version,
        calibration_set_version="policy_v2.0.0",
        model_version=model_out.model_version,
        decision_route=ROUTE_ML,
    )
    session.add(uncertainty)

    ood = OODRecord(
        id=str(uuid.uuid4()),
        prediction_id=prediction_id,
        mahalanobis_score=float(getattr(ood_res, "mahalanobis_score", 0.0)),
        energy_score=float(getattr(ood_res, "energy_score", 0.0)),
        max_softmax_score=float(getattr(ood_res, "max_softmax_score", 0.0)),
        auroc_reference=None,
        is_ood=bool(getattr(ood_res, "is_ood", False)),
        detector_versions={},
    )
    session.add(ood)

    explanation_rec = Explanation(
        id=explanation_id,
        prediction_id=prediction_id,
        what=explanation.what,
        where_region=explanation.where_region,
        why_json=explanation.why_json,
        supporting_evidence_json=explanation.supporting_evidence_json,
        contradicting_evidence_json=explanation.contradicting_evidence_json,
        confidence_narrative=explanation.confidence_narrative,
        model_evidence_section=explanation.model_evidence_section,
        guideline_evidence_section=explanation.guideline_evidence_section,
        generated_synthesis_section=explanation.generated_synthesis_section,
        fidelity_score=explanation.fidelity_score,
        robustness_score=explanation.robustness_score,
        localization_score=explanation.localization_score,
        complexity_score=explanation.complexity_score,
        explanation_policy_version=explanation.explanation_policy_version,
        audit_heatmap_uri=explanation.audit_heatmap_uri,
    )
    session.add(explanation_rec)

    await session.flush()
    return prediction_id, uncertainty_id, explanation_id


async def run_imaging_scan(
    *,
    session: AsyncSession,
    principal: UserPrincipal,
    patient_id: str,
    encounter_id: str,
    radiology_order_id: Optional[str],
    category: str,
    modality: str,
    image_b64: str,
    text_query: Optional[str] = None,
) -> dict[str, Any]:
    """
    Execute the complete imaging + inference workflow and persist all results.

    Returns a dict with request_id, case_id, prediction_id, route, and
    inference results (top1_class, confidence, uncertainty, etc.).
    """
    request_id = str(uuid.uuid4())
    actor_id = principal.user_id
    actor_role = principal.role

    # 1. Validate patient and encounter exist and are linked
    patient = await session.get(Patients, UUID(patient_id))
    if patient is None:
        raise ImagingWorkflowError(f"Patient '{patient_id}' not found", "patient_not_found")
    encounter = await session.get(Encounters, UUID(encounter_id))
    if encounter is None:
        raise ImagingWorkflowError(f"Encounter '{encounter_id}' not found", "encounter_not_found")
    if str(encounter.patient_id) != patient_id:
        raise ImagingWorkflowError(
            "Encounter does not belong to the specified patient", "encounter_patient_mismatch"
        )

    # 2. Validate radiology order if provided (must belong to patient/encounter)
    order = None
    if radiology_order_id:
        order = await session.get(RadiologyOrders, UUID(radiology_order_id))
        if order is None:
            raise ImagingWorkflowError(
                f"Radiology order '{radiology_order_id}' not found", "order_not_found"
            )
        if str(order.patient_id) != patient_id or str(order.encounter_id) != encounter_id:
            raise ImagingWorkflowError(
                "Radiology order does not belong to this patient/encounter",
                "order_patient_encounter_mismatch",
            )

    # 3. Decode image bytes
    try:
        b64_str = image_b64
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        raw_image_bytes = base64.b64decode(b64_str)
    except Exception as exc:
        raise ImagingWorkflowError("Invalid base64 encoding for image.", "invalid_image_encoding") from exc

    # 4. Image quality validation (V1 pipeline)
    q_score, q_flags, q_passed = _quality_validator.assess_image_bytes(raw_image_bytes)

    # 5. Router decision (V1 pipeline)
    route_result = _router_engine.route_request(
        request_id=request_id,
        text=text_query,
        category=category,
        modality=modality,
        quality_score=q_score,
        quality_passed=q_passed,
        has_image=True,
    )

    # Audit route decision
    await AuditService.record_audit_async(
        db=session,
        request_id=request_id,
        actor_id=actor_id,
        actor_role=actor_role,
        action="IMAGING_ROUTE_DECISION",
        model_id=f"onco_{category}_classifier",
        metadata={
            "category": route_result.category,
            "route": route_result.route,
            "quality_score": q_score,
            "quality_flags": q_flags,
            "patient_id": patient_id,
            "encounter_id": encounter_id,
        },
    )

    if route_result.route in [
        ROUTE_FAIL_QUALITY,
        ROUTE_FAIL_RELEVANCE,
        ROUTE_FAIL_MODALITY,
        ROUTE_FAIL_PHASE,
        ROUTE_FAIL_UNTRAINED,
    ]:
        # Persist the ingestion event even for terminal failures (honest recording)
        storage = get_storage_service()
        file_uri = storage.store_file(
            bucket_name="onco-images",
            file_bytes=raw_image_bytes,
            file_extension="png",
            object_id=request_id,
        )
        case = await _get_or_create_case(
            session, patient_id, encounter_id, actor_id, request_id, category
        )
        ingestion = IngestionEvent(
            id=str(uuid.uuid4()),
            case_id=case.id,
            request_id=request_id,
            modality=modality,
            file_uri=file_uri,
            quality_score=q_score,
            quality_flags=q_flags,
            status="REJECTED",
            rejection_reason=route_result.reason,
        )
        session.add(ingestion)
        await session.flush()

        # Add timeline event for the rejected scan
        await _append_timeline_event(
            session=session,
            case_id=case.id,
            event_time=datetime.now(timezone.utc),
            event_type="IMAGING",
            source="hms_imaging_workflow",
            payload={
                "category": category,
                "modality": modality,
                "quality_score": q_score,
                "quality_flags": q_flags,
                "status": "REJECTED",
                "reason": route_result.reason,
            },
            actor_id=actor_id,
            request_id=request_id,
        )
        await session.commit()

        return {
            "request_id": request_id,
            "case_id": case.id,
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "route": route_result.route,
            "category": route_result.category,
            "modality": modality,
            "safety_state": "SAFE_FAIL_TERMINAL",
            "status_message": route_result.reason,
            "quality_score": round(q_score, 3),
            "quality_flags": q_flags,
            "quality_passed": q_passed,
            "persisted": True,
        }

    # 6. ML inference route (V1 pipeline) — real model inference
    if route_result.route != ROUTE_ML:
        # Fallback to RAG — not a diagnostic scan
        raise ImagingWorkflowError(
            f"Request routed to {route_result.route}, not ML inference. Cannot produce diagnostic prediction.",
            "not_ml_route",
        )

    # Run actual V1 inference
    try:
        model_out = _ml_orchestrator.predict(category=category, image_bytes=raw_image_bytes)
    except UntrainedModelError as ume:
        raise ImagingWorkflowError(str(ume), "model_untrained") from ume
    except KeyError as exc:
        raise ImagingWorkflowError(f"Unsupported category '{category}'.", "unsupported_category") from exc

    # Calibration
    calib_res = _calibration_engine.calibrate(
        category=category,
        logits=model_out.logits,
        class_mapping=dict(enumerate(model_out.class_probabilities.keys())),
    )

    # OOD detection
    ood_res = _ood_detector.evaluate_ood(
        category=category,
        embedding=model_out.embedding,
        logits=model_out.logits,
        probabilities=np.array(list(calib_res.calibrated_probabilities.values())),
    )

    # Uncertainty aggregation
    unc_summary = _uncertainty_aggregator.aggregate(
        category=category,
        probabilities=calib_res.calibrated_probabilities,
        quality_score=q_score,
        ood_assessment=ood_res,
    )

    # Clinical XAI explanation
    prediction_id_tmp = str(uuid.uuid4())
    explanation = _clinical_explainer.generate_explanation(
        category=category,
        predicted_class=model_out.top1_class,
        calibrated_probability=calib_res.calibrated_probabilities.get(
            model_out.top1_class, model_out.top1_confidence
        ),
        raw_probability=model_out.top1_confidence,
        embedding=model_out.embedding,
        feature_map=model_out.feature_map,
        image_bytes=raw_image_bytes,
        prediction_id=prediction_id_tmp,
        uncertainty_decision=unc_summary.aggregate_decision,
        class_index=model_out.top1_index,
    )

    # 7. Get or create case linked to patient/encounter
    case = await _get_or_create_case(
        session, patient_id, encounter_id, actor_id, request_id, category
    )

    # 8. Persist prediction + uncertainty + OOD + explanation
    prediction_id, uncertainty_id, explanation_id = await _persist_prediction(
        session=session,
        case=case,
        request_id=request_id,
        model_out=model_out,
        calib_res=calib_res,
        unc_summary=unc_summary,
        ood_res=ood_res,
        explanation=explanation,
        category=category,
    )

    # 9. Store the image file
    storage = get_storage_service()
    file_uri = storage.store_file(
        bucket_name="onco-images",
        file_bytes=raw_image_bytes,
        file_extension="png",
        object_id=request_id,
    )

    # 10. Persist ingestion event
    ingestion = IngestionEvent(
        id=str(uuid.uuid4()),
        case_id=case.id,
        request_id=request_id,
        modality=modality,
        file_uri=file_uri,
        quality_score=q_score,
        quality_flags=q_flags,
        status="INGESTED",
    )
    session.add(ingestion)

    # 11. Create or update radiology report linked to the order
    report_id = None
    if order is not None:
        existing_report = (
            await session.execute(
                select(RadiologyReports).where(RadiologyReports.order_id == order.id)
            )
        ).scalar_one_or_none()
        if existing_report is None:
            report = RadiologyReports(
                id=str(uuid.uuid4()),
                order_id=order.id,
                findings=(
                    f"AI-assisted detection: {model_out.top1_class} "
                    f"(calibrated confidence {calib_res.calibrated_probabilities.get(model_out.top1_class, model_out.top1_confidence):.1%}). "
                    f"Uncertainty decision: {unc_summary.aggregate_decision}."
                ),
                impression=(
                    f"Findings consistent with {model_out.top1_class} "
                    f"on {modality} imaging. Requires radiologist correlation and sign-off."
                ),
                image_uri=file_uri,
                dicom_metadata={
                    "modality": modality,
                    "category": category,
                    "model_version": model_out.model_version,
                    "architecture": model_out.architecture,
                },
                diagnostic_use=True,
                signer_id=actor_id,
                signed_at=datetime.now(timezone.utc),
                quality_evidence={
                    "quality_score": q_score,
                    "quality_flags": q_flags,
                    "uncertainty_decision": unc_summary.aggregate_decision,
                    "ood_score": unc_summary.ood_score,
                },
            )
            session.add(report)
            await session.flush()
            report_id = str(report.id)

            # Update order status to reported
            order.status = "reported"
            order.version += 1
            order.request_id = request_id
            await session.flush()
        else:
            report_id = str(existing_report.id)

    # 12. Append timeline events (imaging + inference)
    await _append_timeline_event(
        session=session,
        case_id=case.id,
        event_time=datetime.now(timezone.utc),
        event_type="IMAGING",
        source="hms_imaging_workflow",
        payload={
            "category": category,
            "modality": modality,
            "image_uri": file_uri,
            "quality_score": q_score,
            "radiology_order_id": radiology_order_id,
            "radiology_report_id": report_id,
        },
        actor_id=actor_id,
        request_id=request_id,
    )
    await _append_timeline_event(
        session=session,
        case_id=case.id,
        event_time=datetime.now(timezone.utc),
        event_type="DIAGNOSIS",
        source="hms_ai_inference",
        payload={
            "category": category,
            "top1_class": model_out.top1_class,
            "top1_confidence": float(model_out.top1_confidence),
            "calibrated_probabilities": calib_res.calibrated_probabilities,
            "uncertainty_decision": unc_summary.aggregate_decision,
            "prediction_id": prediction_id,
            "model_version": model_out.model_version,
            "disclaimer": "AI-assisted decision support, not autonomous diagnosis.",
        },
        actor_id=actor_id,
        request_id=request_id,
    )

    # 13. Audit inference completion
    await AuditService.record_audit_async(
        db=session,
        request_id=request_id,
        actor_id=actor_id,
        actor_role=actor_role,
        action="ML_INFERENCE_COMPLETED",
        model_id=f"onco_{category}_classifier",
        model_version=model_out.model_version,
        explanation_id=explanation_id,
        uncertainty_record_id=uncertainty_id,
        metadata={
            "decision": unc_summary.aggregate_decision,
            "top1": model_out.top1_class,
            "confidence": float(model_out.top1_confidence),
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "case_id": case.id,
            "radiology_report_id": report_id,
        },
    )

    await session.commit()

    calibrated_top1 = float(
        calib_res.calibrated_probabilities.get(model_out.top1_class, model_out.top1_confidence)
    )

    return {
        "request_id": request_id,
        "case_id": case.id,
        "patient_id": patient_id,
        "encounter_id": encounter_id,
        "prediction_id": prediction_id,
        "route": ROUTE_ML,
        "category": category,
        "modality": modality,
        "top1_class": model_out.top1_class,
        "top1_confidence": round(float(model_out.top1_confidence), 3),
        "calibrated_top1_confidence": round(calibrated_top1, 3),
        "calibrated_probabilities": calib_res.calibrated_probabilities,
        "raw_probabilities": model_out.class_probabilities,
        "uncertainty": {
            "predictive_uncertainty": unc_summary.predictive_uncertainty,
            "data_uncertainty": unc_summary.data_uncertainty,
            "evidence_uncertainty": unc_summary.evidence_uncertainty,
            "ood_score": unc_summary.ood_score,
            "aggregate_decision": unc_summary.aggregate_decision,
            "reasons": unc_summary.reasons,
        },
        "explanation": {
            "what": explanation.what,
            "where_region": explanation.where_region,
            "confidence_narrative": explanation.confidence_narrative,
            "fidelity_score": explanation.fidelity_score,
            "localization_score": explanation.localization_score,
            "audit_heatmap_uri": explanation.audit_heatmap_uri,
        },
        "model_version": model_out.model_version,
        "architecture": model_out.architecture,
        "image_uri": file_uri,
        "radiology_report_id": report_id,
        "radiology_order_id": radiology_order_id,
        "quality_score": round(q_score, 3),
        "quality_flags": q_flags,
        "safety_state": unc_summary.aggregate_decision,
        "status_message": (
            f"ML analysis completed. Decision gate: {unc_summary.aggregate_decision}. "
            "Results persisted to patient record."
        ),
        "persisted": True,
    }


async def _append_timeline_event(
    *,
    session: AsyncSession,
    case_id: str,
    event_time: datetime,
    event_type: str,
    source: str,
    payload: dict[str, Any],
    actor_id: str,
    request_id: str,
) -> None:
    """Append an immutable timeline event to the case."""
    event = PatientTimelineEvent(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_time=event_time,
        event_type=event_type,
        source=source,
        provenance_json={"actor_id": actor_id, "request_id": request_id},
        confidence=None,
        missingness_state="PRESENT",
        references_event_id=None,
        payload_json=payload,
    )
    session.add(event)
    await session.flush()


async def get_imaging_results_for_patient(
    *,
    session: AsyncSession,
    patient_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Retrieve all imaging studies and inference results for a patient,
    ordered by most recent first. Used for the longitudinal patient record.
    """
    # Verify patient exists
    patient = await session.get(Patients, UUID(patient_id))
    if patient is None:
        raise ImagingWorkflowError(f"Patient '{patient_id}' not found", "patient_not_found")

    # Get cases for this patient, joined with predictions
    stmt = (
        select(Case, PredictionModel, UncertaintyRecord, IngestionEvent)
        .outerjoin(PredictionModel, PredictionModel.case_id == Case.id)
        .outerjoin(UncertaintyRecord, UncertaintyRecord.prediction_id == PredictionModel.id)
        .outerjoin(IngestionEvent, IngestionEvent.case_id == Case.id)
        .where(Case.patient_id == patient_id)
        .order_by(Case.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Group by case
    cases_map: dict[str, dict[str, Any]] = {}
    for case, prediction, uncertainty, ingestion in rows:
        if case.id not in cases_map:
            cases_map[case.id] = {
                "case_id": case.id,
                "patient_id": case.patient_id,
                "encounter_id": case.encounter_id,
                "status": case.status,
                "created_at": case.created_at.isoformat() if case.created_at else None,
                "imaging_studies": [],
                "inference_results": [],
            }
        entry = cases_map[case.id]

        if ingestion:
            entry["imaging_studies"].append({
                "request_id": ingestion.request_id,
                "modality": ingestion.modality,
                "file_uri": ingestion.file_uri,
                "quality_score": ingestion.quality_score,
                "quality_flags": ingestion.quality_flags,
                "status": ingestion.status,
                "created_at": ingestion.created_at.isoformat() if ingestion.created_at else None,
            })

        if prediction:
            entry["inference_results"].append({
                "prediction_id": prediction.id,
                "request_id": prediction.request_id,
                "category": prediction.category,
                "top1_class": prediction.top1_class,
                "top1_confidence": prediction.top1_confidence,
                "class_probabilities": prediction.class_probabilities,
                "model_version": prediction.model_version_id,
                "created_at": prediction.created_at.isoformat() if prediction.created_at else None,
                "uncertainty": {
                    "aggregate_decision": uncertainty.aggregate_decision if uncertainty else None,
                    "ood_score": uncertainty.ood_score if uncertainty else None,
                    "predictive_uncertainty": uncertainty.predictive_uncertainty if uncertainty else None,
                } if uncertainty else None,
            })

    return list(cases_map.values())
