"""
OncoSentinel v2.0 — Uncertainty Aggregator
Satisfies: FR-05, FR-06, FR-07, FR-08, NFR-01
Grounded in: Architecture v2.0 §4 (Uncertainty before autonomy; PASS | REVIEW | ABSTAIN decision mapping)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from services.core.config_loader import get_uncertainty_thresholds
from services.core.logging import get_logger
from services.uncertainty.ood_detector import OODAssessment

logger = get_logger(__name__)

DECISION_PASS = "PASS"
DECISION_REVIEW = "REVIEW"
DECISION_ABSTAIN = "ABSTAIN"


@dataclass
class UncertaintySummary:
    predictive_uncertainty: float  # Normalized entropy [0.0, 1.0]
    data_uncertainty: float        # Derived from image quality / noise [0.0, 1.0]
    evidence_uncertainty: Optional[float]
    ood_score: float
    aggregate_decision: str        # PASS | REVIEW | ABSTAIN
    threshold_policy_version: str
    reasons: list[str]


class UncertaintyAggregator:
    """Combines predictive entropy, data quality degradation, and OOD assessment into a clinical decision gate."""

    def __init__(self) -> None:
        self.policy_version = "policy_v2.0.0"

    def aggregate(
        self,
        category: str,
        probabilities: dict[str, float],
        quality_score: float,
        ood_assessment: OODAssessment,
        evidence_score: Optional[float] = None,
    ) -> UncertaintySummary:
        cat_thresh = get_uncertainty_thresholds(category)
        pred_thresh = cat_thresh.get("uncertainty", {}).get("predictive", {})
        pass_below = pred_thresh.get("pass_below", 0.40)
        review_below = pred_thresh.get("review_below", 0.70)

        ood_thresh = cat_thresh.get("ood_composite", {})
        ood_pass = ood_thresh.get("pass_below", 0.30)
        ood_review = ood_thresh.get("review_below", 0.60)

        # 1. Predictive Uncertainty (Normalized Shannon Entropy)
        # H(p) = - sum(p_i * ln(p_i)) / ln(K)
        probs_vec = np.array(list(probabilities.values()), dtype=np.float64)
        probs_vec = np.maximum(probs_vec, 1e-12)
        k = len(probs_vec)
        raw_entropy = -float(np.sum(probs_vec * np.log(probs_vec)))
        max_entropy = math.log(k) if k > 1 else 1.0
        normalized_entropy = float(raw_entropy / max_entropy)
        normalized_entropy = min(1.0, max(0.0, normalized_entropy))

        # 2. Data Uncertainty (Complement of quality score)
        data_uncertainty = float(1.0 - min(1.0, max(0.0, quality_score)))

        # 3. Evidence Uncertainty (if RAG used)
        evidence_uncertainty = (
            float(1.0 - min(1.0, max(0.0, evidence_score)))
            if evidence_score is not None
            else None
        )

        # 4. Aggregate Decision Logic
        reasons: list[str] = []
        decision = DECISION_PASS

        # Evaluate Predictive Uncertainty
        if normalized_entropy >= review_below:
            decision = DECISION_ABSTAIN
            reasons.append(
                f"Predictive entropy ({normalized_entropy:.2f}) exceeds safe abstention threshold ({review_below:.2f})."
            )
        elif normalized_entropy >= pass_below:
            if decision != DECISION_ABSTAIN:
                decision = DECISION_REVIEW
            reasons.append(
                f"Predictive entropy ({normalized_entropy:.2f}) requires clinician review (threshold: {pass_below:.2f})."
            )

        # Evaluate OOD Detection
        if ood_assessment.is_ood or ood_assessment.composite_ood_score >= ood_review:
            decision = DECISION_ABSTAIN
            reasons.append(
                f"Input identified as Out-of-Distribution (OOD score: {ood_assessment.composite_ood_score:.2f}). Consensus votes: {ood_assessment.consensus_count}."
            )
        elif ood_assessment.composite_ood_score >= ood_pass:
            if decision != DECISION_ABSTAIN:
                decision = DECISION_REVIEW
            reasons.append(
                f"Elevated OOD score ({ood_assessment.composite_ood_score:.2f}) suggests distribution drift."
            )

        # Evaluate Data Uncertainty
        if data_uncertainty > 0.50:
            if decision != DECISION_ABSTAIN:
                decision = DECISION_REVIEW
            reasons.append(
                f"Suboptimal input quality (data uncertainty: {data_uncertainty:.2f}) warrants verification."
            )

        if decision == DECISION_PASS:
            reasons.append("Uncertainty metrics within established safety thresholds.")

        logger.info(
            "uncertainty_aggregated",
            category=category,
            decision=decision,
            entropy=round(normalized_entropy, 3),
            ood_score=round(ood_assessment.composite_ood_score, 3),
            reasons=reasons,
        )

        return UncertaintySummary(
            predictive_uncertainty=round(normalized_entropy, 4),
            data_uncertainty=round(data_uncertainty, 4),
            evidence_uncertainty=(
                round(evidence_uncertainty, 4) if evidence_uncertainty is not None else None
            ),
            ood_score=round(ood_assessment.composite_ood_score, 4),
            aggregate_decision=decision,
            threshold_policy_version=self.policy_version,
            reasons=reasons,
        )


_aggregator_singleton: Optional[UncertaintyAggregator] = None


def get_uncertainty_aggregator() -> UncertaintyAggregator:
    global _aggregator_singleton
    if _aggregator_singleton is None:
        _aggregator_singleton = UncertaintyAggregator()
    return _aggregator_singleton
