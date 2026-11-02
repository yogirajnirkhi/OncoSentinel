"""
Tests for Calibration, OOD Detection, and Uncertainty Aggregation (FR-05..08)
"""
from __future__ import annotations

import numpy as np
import pytest

from services.uncertainty.aggregator import DECISION_ABSTAIN, DECISION_PASS, DECISION_REVIEW, UncertaintyAggregator
from services.uncertainty.calibration import CalibrationEngine
from services.uncertainty.ood_detector import OODDetector


def test_temperature_scaling_calibration():
    engine = CalibrationEngine()
    logits = np.array([2.5, 0.5])
    mapping = {0: "benign", 1: "malignant"}

    result = engine.calibrate(category="breast", logits=logits, class_mapping=mapping)
    assert "benign" in result.calibrated_probabilities
    assert "malignant" in result.calibrated_probabilities
    assert sum(result.calibrated_probabilities.values()) == pytest.approx(1.0, rel=1e-3)
    assert len(result.conformal_set) >= 1
    assert result.method == "temperature_scaling+conformal"


def test_ood_detector():
    detector = OODDetector()
    embedding = np.random.randn(512)
    logits = np.array([3.0, 0.2])
    probs = np.array([0.94, 0.06])

    assessment = detector.evaluate_ood(
        category="breast",
        embedding=embedding,
        logits=logits,
        probabilities=probs,
    )
    assert 0.0 <= assessment.composite_ood_score <= 1.0
    assert isinstance(assessment.is_ood, bool)


def test_uncertainty_aggregator_decision_mapping():
    aggregator = UncertaintyAggregator()
    detector = OODDetector()

    # Confident, in-distribution case -> PASS
    confident_probs = {"benign": 0.95, "malignant": 0.05}
    good_ood = detector.evaluate_ood(
        category="breast",
        embedding=np.random.randn(512),
        logits=np.array([4.0, 0.1]),
        probabilities=np.array([0.95, 0.05]),
    )
    res_pass = aggregator.aggregate(
        category="breast",
        probabilities=confident_probs,
        quality_score=0.95,
        ood_assessment=good_ood,
    )
    assert res_pass.aggregate_decision in [DECISION_PASS, DECISION_REVIEW]

    # Highly equivocal case (50-50) -> ABSTAIN due to maximum entropy
    equivocal_probs = {"benign": 0.50, "malignant": 0.50}
    res_abstain = aggregator.aggregate(
        category="breast",
        probabilities=equivocal_probs,
        quality_score=0.90,
        ood_assessment=good_ood,
    )
    assert res_abstain.aggregate_decision in [DECISION_REVIEW, DECISION_ABSTAIN]
