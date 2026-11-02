"""
OncoSentinel v2.0 — Fairness Release Gate
Satisfies: FR-18, FR-19 (flag unacceptable disparities, release gating)
"""
from __future__ import annotations

from services.core.logging import get_logger
from services.fairness.evaluator import FairnessEvaluationSummary

logger = get_logger(__name__)


class FairnessReleaseGate:
    """Evaluates candidate model fairness report against strict clinical release criteria."""

    def evaluate_gate(self, summary: FairnessEvaluationSummary) -> tuple[bool, list[str]]:
        reasons: list[str] = []

        if summary.max_sensitivity_disparity > 0.10:
            reasons.append(
                f"Sensitivity disparity ({summary.max_sensitivity_disparity:.2%}) exceeds 10% maximum tolerance."
            )

        if summary.max_ece_disparity > 0.06:
            reasons.append(
                f"Calibration ECE disparity ({summary.max_ece_disparity:.2%}) exceeds 6% tolerance."
            )

        if summary.max_fnr_disparity > 0.08:
            reasons.append(
                f"False Negative Rate disparity ({summary.max_fnr_disparity:.2%}) exceeds 8% tolerance."
            )

        passed = len(reasons) == 0
        if not passed:
            logger.warning("fairness_gate_failed", reasons=reasons)
        else:
            logger.info("fairness_gate_passed", model=summary.model_version)

        return passed, reasons
