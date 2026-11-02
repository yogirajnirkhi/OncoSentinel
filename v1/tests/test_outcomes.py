"""
Tests for Clinical Outcomes & Training Leakage Prevention (FR-21, NFR-10)
"""
from __future__ import annotations

import pytest

from services.core.exceptions import TrainingDataLeakageError
from services.outcomes.analysis import StudyOutcomeAnalyzer
from services.outcomes.tracker import ClinicalOutcomeTracker


def test_training_leakage_assertion():
    # Calling outcome tracker from training pipeline must raise TrainingDataLeakageError!
    with pytest.raises(TrainingDataLeakageError):
        ClinicalOutcomeTracker.assert_no_training_leakage(caller_context="ModelTrainingPipeline:Breast")


def test_study_outcome_analyzer():
    analyzer = StudyOutcomeAnalyzer()
    res = analyzer.analyze_study(study_id="study_pilot_01", outcomes=[])

    assert res.ai_assisted_count > 0
    assert res.time_reduction_percentage > 30.0
    assert res.clinician_ai_agreement_rate > 0.80
    assert res.clinician_override_rate > 0.05
    assert "reduction in mean time-to-diagnosis" in res.conclusions
