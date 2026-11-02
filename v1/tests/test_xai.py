"""
Tests for Clinical XAI, Concept Mapping, and Sangwan (2024) Quantitative Evaluation
"""
from __future__ import annotations

import numpy as np
import torch

from services.xai.clinical_explainer import ClinicalExplanationEngine
from services.xai.concept_mapper import ConceptMapper
from services.xai.evaluator import XAIEvaluator


def test_concept_mapper_extracts_supporting_and_counter_evidence():
    mapper = ConceptMapper()
    dummy_emb = np.random.randn(512)

    supporting, counter = mapper.extract_concepts(
        category="breast",
        predicted_class="malignant",
        embedding=dummy_emb,
    )
    assert len(supporting) > 0
    assert all(c.polarity == "SUPPORTING" for c in supporting)
    assert any(c.concept_id in ["mass_shape", "mass_margin", "calcification_pattern"] for c in supporting)


def test_quantitative_xai_evaluator():
    evaluator = XAIEvaluator()
    dummy_heatmap = np.zeros((224, 224), dtype=np.float32)
    dummy_heatmap[80:140, 80:140] = 0.90  # Focal concentration

    metrics = evaluator.evaluate_explanation(
        heatmap=dummy_heatmap,
        concept_saliences=[0.85, 0.78, 0.90],
    )
    assert metrics.fidelity_score >= 0.50
    assert metrics.robustness_score >= 0.50
    assert metrics.localization_score >= 0.40
    assert isinstance(metrics.passes_thresholds, bool)


def test_clinical_explanation_engine(sample_image_bytes):
    engine = ClinicalExplanationEngine()
    dummy_emb = np.random.randn(512)
    dummy_feature_map = torch.randn(1, 512, 14, 14)

    explanation = engine.generate_explanation(
        category="breast",
        predicted_class="malignant",
        calibrated_probability=0.914,
        raw_probability=0.942,
        embedding=dummy_emb,
        feature_map=dummy_feature_map,
        image_bytes=sample_image_bytes,
        prediction_id="pred_test_123",
        uncertainty_decision="PASS",
    )

    assert "MALIGNANT" in explanation.what
    assert len(explanation.why_json) > 0
    assert "INTERNAL MODEL ACTIVATION" in explanation.model_evidence_section
    assert "CLINICAL GUIDELINE" in explanation.guideline_evidence_section
    assert "CLINICAL DECISION-SUPPORT SYNTHESIS" in explanation.generated_synthesis_section
