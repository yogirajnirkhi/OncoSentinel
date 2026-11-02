"""
Tests for Subgroup Fairness & Disparity Release Gates (FR-18, FR-19, NFR-08)
"""
from __future__ import annotations

from services.fairness.evaluator import FairnessEvaluator
from services.fairness.gate import FairnessReleaseGate
from services.fairness.reporting import FairnessReportGenerator


def test_fairness_evaluator_subgroups():
    evaluator = FairnessEvaluator()
    summary = evaluator.evaluate_subgroups(model_version="breast_v2.0.0", category="breast")

    assert summary.overall_samples > 500
    assert len(summary.subgroup_metrics) >= 6
    assert summary.max_sensitivity_disparity <= 0.15
    assert isinstance(summary.gate_passed, bool)


def test_fairness_release_gate():
    evaluator = FairnessEvaluator()
    gate = FairnessReleaseGate()

    summary = evaluator.evaluate_subgroups(model_version="breast_v2.0.0", category="breast")
    passed, reasons = gate.evaluate_gate(summary)
    assert passed is True
    assert len(reasons) == 0


def test_fairness_report_markdown():
    evaluator = FairnessEvaluator()
    summary = evaluator.evaluate_subgroups(model_version="breast_v2.0.0", category="breast")
    md = FairnessReportGenerator.generate_markdown(summary)

    assert "# OncoSentinel Fairness & Subgroup Evaluation Report" in md
    assert "Disparity Summary" in md
    assert "Subgroup Performance Matrix" in md
