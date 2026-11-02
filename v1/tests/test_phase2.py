"""
Tests for Phase 2 Multi-Cancer Expansion (SRS §2, §3, FR-04, FR-05)
Validates all 6 Phase 2 categories: brain, all_leukemia, oral, lung_colon, lymphoma, cervical.
"""
from __future__ import annotations

import numpy as np
import pytest

from services.ml.adapters.base import UntrainedModelError
from services.ml.orchestrator import MLOrchestrator
from services.rag.vector_store import VectorStore
from services.router.engine import ROUTE_FAIL_UNTRAINED, ROUTE_ML, RouterEngine
from services.xai.concept_mapper import ConceptMapper


@pytest.fixture
def phase2_router():
    router = RouterEngine()
    orig = router.settings.platform_phase
    router.settings.platform_phase = 2
    yield router
    router.settings.platform_phase = orig



def test_phase2_router_unlocks_all_categories(phase2_router):
    active_phase2_cases = [
        ("brain", "mri", "Brain MRI showing ring enhancing frontal mass"),
        ("all_leukemia", "microscopy", "Peripheral smear showing immature blast cells"),
        ("oral", "histology", "Tongue biopsy invasive squamous cell carcinoma"),
        ("lung_colon", "histology", "Lung biopsy atypical glandular proliferation"),
        ("cervical", "cytology", "Pap smear revealing dyskeratotic squames HSIL"),
        ("colon", "histology", "Colonic biopsy glandular adenocarcinoma"),
        ("lung", "histology", "Lung biopsy squamous cell carcinoma"),
    ]

    for cat, mod, txt in active_phase2_cases:
        res = phase2_router.route_request(
            request_id=f"test_p2_{cat}",
            text=txt,
            category=cat,
            modality=mod,
            quality_score=0.92,
            quality_passed=True,
            has_image=True,
        )
        assert res.route == ROUTE_ML, f"Category {cat} failed to route to ML: {res.reason}"
        assert res.category == cat
        assert res.modality_validated is True

    # Lymphoma is unlocked in Phase 2 but has no trained checkpoint -> TERMINAL_MODEL_UNTRAINED
    res_lymph = phase2_router.route_request(
        request_id="test_p2_lymphoma",
        text="Lymph node biopsy effaced architecture with centrocytes",
        category="lymphoma",
        modality="histology",
        quality_score=0.92,
        quality_passed=True,
        has_image=True,
    )
    assert res_lymph.route == ROUTE_FAIL_UNTRAINED


def test_phase2_ml_orchestrator_all_heads(sample_image_bytes):
    orchestrator = MLOrchestrator(device="cpu")

    category_class_counts = {
        "brain": 3,
        "all_leukemia": 4,
        "oral": 2,
        "lung_colon": 5,
        "cervical": 5,
        "colon": 2,
        "lung": 3,
    }

    for cat, expected_count in category_class_counts.items():
        out = orchestrator.predict(category=cat, image_bytes=sample_image_bytes)
        assert out.category == cat
        assert len(out.class_probabilities) == expected_count, (
            f"Expected {expected_count} classes for '{cat}', got {len(out.class_probabilities)}"
        )
        assert 0.0 <= out.top1_confidence <= 1.0
        assert sum(out.class_probabilities.values()) == pytest.approx(1.0, abs=1e-3)

    with pytest.raises(UntrainedModelError):
        orchestrator.predict(category="lymphoma", image_bytes=sample_image_bytes)


def test_phase2_concept_mapper_coverage():
    mapper = ConceptMapper()
    dummy_emb = np.random.randn(512)

    phase2_categories = [
        ("brain", "glioma"),
        ("all_leukemia", "all_blast"),
        ("oral", "squamous_cell_carcinoma"),
        ("lung_colon", "adenocarcinoma"),
        ("lymphoma", "follicular_lymphoma"),
        ("cervical", "hsil"),
    ]

    for cat, pred_cls in phase2_categories:
        supporting, counter = mapper.extract_concepts(
            category=cat,
            predicted_class=pred_cls,
            embedding=dummy_emb,
        )
        assert len(supporting) > 0, f"No supporting concepts extracted for category '{cat}'"
        assert all(c.polarity == "SUPPORTING" for c in supporting)
        assert all(len(c.clinical_observation) > 0 for c in supporting)


def test_phase2_guideline_retrieval():
    vs = VectorStore()
    queries = [
        ("all_leukemia", "What are the NCCN criteria for acute lymphoblastic leukemia blast percentage?"),
        ("oral", "What margin is required for oral squamous cell carcinoma resection?"),
        ("lung_colon", "What immunohistochemical markers differentiate lung adenocarcinoma from colon metastasis?"),
        ("lymphoma", "How does WHO 5th edition define follicular lymphoma grading?"),
        ("cervical", "What is the recommended management for HSIL on cervical cytology?"),
    ]

    for cat, q in queries:
        docs = vs.query_evidence(query_text=q, category=cat, top_k=2)
        assert len(docs) > 0, f"No guidelines retrieved for query on '{cat}'"
        assert docs[0].similarity_score > 0.0
