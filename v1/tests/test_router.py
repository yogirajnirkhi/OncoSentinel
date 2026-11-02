"""
Tests for Intelligent Router & Safety Gating (FR-03, FR-04, FR-30)
"""
from __future__ import annotations

from services.router.cancer_relevance import CancerRelevanceEvaluator
from services.router.engine import (
    ROUTE_FAIL_PHASE,
    ROUTE_FAIL_QUALITY,
    ROUTE_FAIL_RELEVANCE,
    ROUTE_ML,
    ROUTE_RAG,
    RouterEngine,
)


def test_cancer_relevance_passes_for_oncology_text():
    evaluator = CancerRelevanceEvaluator()
    score, cat, passed = evaluator.evaluate_relevance(
        text="54yo patient with suspicious mass on breast ultrasound showing microcalcifications.",
        category_hint="breast",
    )
    assert passed is True
    assert score >= 0.55
    assert cat == "breast"


def test_cancer_relevance_fails_for_off_topic_text():
    evaluator = CancerRelevanceEvaluator()
    score, cat, passed = evaluator.evaluate_relevance(
        text="What is the weather in Paris today and how do I bake bread?",
        category_hint=None,
    )
    assert passed is False
    assert score < 0.55


def test_router_quality_gate_blocks_low_quality():
    router = RouterEngine()
    result = router.route_request(
        request_id="test_req_01",
        text="breast cancer scan",
        category="breast",
        modality="ultrasound",
        quality_score=0.25,
        quality_passed=False,
        has_image=True,
    )
    assert result.route == ROUTE_FAIL_QUALITY
    assert result.quality_passed is False


def test_router_routes_valid_phase1_ml():
    router = RouterEngine()
    result = router.route_request(
        request_id="test_req_02",
        text="contrast abdominal ct kidney renal mass finding",
        category="kidney",
        modality="ct",
        quality_score=0.85,
        quality_passed=True,
        has_image=True,
    )
    assert result.route == ROUTE_ML
    assert result.category == "kidney"
    assert result.capability_check_passed is True


def test_router_phase_gate_blocks_phase2_category_in_phase1():
    router = RouterEngine()
    orig_phase = router.settings.platform_phase
    router.settings.platform_phase = 1
    try:
        # 'brain' is scheduled for Phase 2
        result = router.route_request(
            request_id="test_req_03",
            text="mri brain tumor glioma",
            category="brain",
            modality="mri",
            quality_score=0.90,
            quality_passed=True,
            has_image=True,
        )
        assert result.route == ROUTE_FAIL_PHASE
        assert "not unlocked in Platform Phase 1" in result.reason
    finally:
        router.settings.platform_phase = orig_phase
