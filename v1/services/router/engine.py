"""
OncoSentinel v2.0 — Router Engine
Satisfies: FR-03, FR-04, FR-30 (Intelligent routing + terminal safety states)
Grounded in: Architecture §12 (routing before execution; specialized models before generic reasoning)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from services.core.config_loader import is_category_available
from services.core.logging import get_logger
from services.core.settings import get_settings
from services.router.cancer_relevance import CancerRelevanceEvaluator
from services.router.intent_classifier import (
    INTENT_DIAGNOSTIC,
    INTENT_EVIDENCE,
    INTENT_LONGITUDINAL,
    INTENT_OUTCOME,
    IntentClassifier,
)
from services.router.modality_checker import ModalityChecker

logger = get_logger(__name__)

# Primary Execution Routes
ROUTE_ML = "ML_INFERENCE"
ROUTE_RAG = "RAG_RETRIEVAL"
ROUTE_LONGITUDINAL = "LONGITUDINAL_TIMELINE"
ROUTE_OUTCOME = "OUTCOME_EVALUATION"

# Terminal Safety States (SRS FR-30)
ROUTE_FAIL_QUALITY = "TERMINAL_LOW_QUALITY"
ROUTE_FAIL_RELEVANCE = "TERMINAL_NOT_CANCER_RELEVANT"
ROUTE_FAIL_MODALITY = "TERMINAL_UNSUPPORTED_MODALITY"
ROUTE_FAIL_PHASE = "TERMINAL_PHASE_NOT_AVAILABLE"
ROUTE_FAIL_UNTRAINED = "TERMINAL_MODEL_UNTRAINED"


@dataclass
class RoutingResult:
    request_id: str
    route: str
    category: Optional[str]
    intent: str
    cancer_relevance_score: float
    modality_validated: bool
    quality_passed: bool
    capability_check_passed: bool
    phase_status: str
    reason: str


class RouterEngine:
    """Central intelligent router implementing the OncoSentinel decision gate."""

    def __init__(self) -> None:
        self.intent_classifier = IntentClassifier()
        self.relevance_evaluator = CancerRelevanceEvaluator()
        self.modality_checker = ModalityChecker()
        self.settings = get_settings()

    def route_request(
        self,
        request_id: str,
        text: Optional[str],
        category: Optional[str],
        modality: Optional[str],
        quality_score: float,
        quality_passed: bool,
        has_image: bool,
    ) -> RoutingResult:
        # Step 1: Input Quality Gate (FR-02)
        if has_image and not quality_passed:
            return RoutingResult(
                request_id=request_id,
                route=ROUTE_FAIL_QUALITY,
                category=category,
                intent=INTENT_DIAGNOSTIC,
                cancer_relevance_score=0.0,
                modality_validated=False,
                quality_passed=False,
                capability_check_passed=False,
                phase_status=f"Phase {self.settings.platform_phase}",
                reason=f"Input failed quality gate (score: {quality_score:.2f}). Below minimum threshold 0.40.",
            )

        # Step 2: Intent Classification (FR-03)
        intent = self.intent_classifier.classify_intent(
            text=text, has_image=has_image, modality=modality
        )

        # Step 3: Cancer Relevance Gate (FR-03, FR-04)
        relevance_score, detected_category, rel_passed = self.relevance_evaluator.evaluate_relevance(
            text=text,
            category_hint=category,
            has_medical_image=has_image,
        )
        resolved_category = category or detected_category

        if not rel_passed:
            return RoutingResult(
                request_id=request_id,
                route=ROUTE_FAIL_RELEVANCE,
                category=resolved_category,
                intent=intent,
                cancer_relevance_score=relevance_score,
                modality_validated=False,
                quality_passed=quality_passed,
                capability_check_passed=False,
                phase_status=f"Phase {self.settings.platform_phase}",
                reason=f"Input cancer relevance score {relevance_score:.2f} is below minimum gate (0.55).",
            )

        # Step 4: Branch on Intent
        if intent == INTENT_LONGITUDINAL:
            return RoutingResult(
                request_id=request_id,
                route=ROUTE_LONGITUDINAL,
                category=resolved_category,
                intent=intent,
                cancer_relevance_score=relevance_score,
                modality_validated=True,
                quality_passed=quality_passed,
                capability_check_passed=True,
                phase_status=f"Phase {self.settings.platform_phase}",
                reason="Routed to Longitudinal Timeline engine for trajectory analysis.",
            )

        if intent == INTENT_OUTCOME:
            return RoutingResult(
                request_id=request_id,
                route=ROUTE_OUTCOME,
                category=resolved_category,
                intent=intent,
                cancer_relevance_score=relevance_score,
                modality_validated=True,
                quality_passed=quality_passed,
                capability_check_passed=True,
                phase_status=f"Phase {self.settings.platform_phase}",
                reason="Routed to Clinical Outcome capture & analysis layer.",
            )

        if intent == INTENT_EVIDENCE or (not has_image and text):
            return RoutingResult(
                request_id=request_id,
                route=ROUTE_RAG,
                category=resolved_category,
                intent=intent,
                cancer_relevance_score=relevance_score,
                modality_validated=True,
                quality_passed=quality_passed,
                capability_check_passed=True,
                phase_status=f"Phase {self.settings.platform_phase}",
                reason="Routed to RAG & Clinical Knowledge engine for evidence-grounded retrieval.",
            )

        # Step 5: ML Diagnostic Diagnostic Routing
        if has_image:
            if not resolved_category:
                return RoutingResult(
                    request_id=request_id,
                    route=ROUTE_FAIL_MODALITY,
                    category=None,
                    intent=intent,
                    cancer_relevance_score=relevance_score,
                    modality_validated=False,
                    quality_passed=quality_passed,
                    capability_check_passed=False,
                    phase_status=f"Phase {self.settings.platform_phase}",
                    reason="No cancer category could be mapped to this image request.",
                )

            # Check Platform Phase Availability (FR-04, Phase plan v2.0)
            if not is_category_available(resolved_category, self.settings.platform_phase):
                return RoutingResult(
                    request_id=request_id,
                    route=ROUTE_FAIL_PHASE,
                    category=resolved_category,
                    intent=intent,
                    cancer_relevance_score=relevance_score,
                    modality_validated=False,
                    quality_passed=quality_passed,
                    capability_check_passed=False,
                    phase_status=f"Phase {self.settings.platform_phase}",
                    reason=f"Category '{resolved_category}' is not unlocked in Platform Phase {self.settings.platform_phase}.",
                )

            # Check Model Deployment Status (Active Trained Checkpoint vs Untrained)
            from services.ml.orchestrator import get_ml_orchestrator
            orch = get_ml_orchestrator()
            if not orch.has_trained_model(resolved_category):
                return RoutingResult(
                    request_id=request_id,
                    route=ROUTE_FAIL_UNTRAINED,
                    category=resolved_category,
                    intent=intent,
                    cancer_relevance_score=relevance_score,
                    modality_validated=True,
                    quality_passed=quality_passed,
                    capability_check_passed=False,
                    phase_status=f"Phase {self.settings.platform_phase}",
                    reason=f"Model for category '{resolved_category}' is currently UNTRAINED. Active trained models are deployed for Kidney, Oral, ALL Leukemia, Brain, Cervical, Colon, and Lung cancer.",
                )

            # Check Modality compatibility with taxonomy (FR-04)
            if modality:
                mod_ok, supported = self.modality_checker.check(resolved_category, modality)
                if not mod_ok:
                    return RoutingResult(
                        request_id=request_id,
                        route=ROUTE_FAIL_MODALITY,
                        category=resolved_category,
                        intent=intent,
                        cancer_relevance_score=relevance_score,
                        modality_validated=False,
                        quality_passed=quality_passed,
                        capability_check_passed=False,
                        phase_status=f"Phase {self.settings.platform_phase}",
                        reason=f"Modality '{modality}' is unsupported for '{resolved_category}'. Supported: {supported}",
                    )

            # All Gates Passed -> Route to ML Orchestrator!
            return RoutingResult(
                request_id=request_id,
                route=ROUTE_ML,
                category=resolved_category,
                intent=intent,
                cancer_relevance_score=relevance_score,
                modality_validated=True,
                quality_passed=quality_passed,
                capability_check_passed=True,
                phase_status=f"Phase {self.settings.platform_phase}",
                reason="All quality, relevance, modality, and phase gates passed. Executing ML inference pipeline.",
            )

        # Fallback
        return RoutingResult(
            request_id=request_id,
            route=ROUTE_RAG,
            category=resolved_category,
            intent=intent,
            cancer_relevance_score=relevance_score,
            modality_validated=True,
            quality_passed=quality_passed,
            capability_check_passed=True,
            phase_status=f"Phase {self.settings.platform_phase}",
            reason="Defaulting to RAG clinical evidence retrieval.",
        )
