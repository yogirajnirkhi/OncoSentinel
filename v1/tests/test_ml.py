"""
Tests for MobileNetV3 Adapters, Shared Backbone, and Category Heads (FR-05, SRS §2, §3)
"""
from __future__ import annotations

import pytest
import torch

from services.ml.adapters.base import UntrainedModelError
from services.ml.backbone import SharedBackbone
from services.ml.heads import HEAD_REGISTRY, build_category_head
from services.ml.orchestrator import MLOrchestrator


def test_shared_backbone_output_shapes():
    backbone = SharedBackbone(embedding_dim=512)
    dummy_input = torch.randn(2, 3, 224, 224)
    embedding, feature_map = backbone(dummy_input)

    assert embedding.shape == (2, 512)
    assert feature_map.shape[0] == 2
    assert feature_map.shape[1] == 512
    assert len(feature_map.shape) == 4  # (B, C, H, W)


def test_eight_category_heads_num_classes():
    expected_classes = {
        "breast": 2,
        "kidney": 2,  # Synchronized with user's binary CT model
        "all_leukemia": 4,
        "oral": 2,
        "lung_colon": 5,
        "colon": 2,
        "lung": 3,
        "lymphoma": 3,
        "brain": 3,
        "cervical": 5,
    }
    for cat, num_cls in expected_classes.items():
        head = build_category_head(cat, in_features=512)
        dummy_emb = torch.randn(2, 512)
        logits = head(dummy_emb)
        assert logits.shape == (2, num_cls), f"Head for '{cat}' expected {num_cls} classes, got {logits.shape[1]}"


def test_ml_orchestrator_predict_kidney(sample_image_bytes):
    orchestrator = MLOrchestrator(device="cpu")
    out = orchestrator.predict(category="kidney", image_bytes=sample_image_bytes)

    assert out.category == "kidney"
    assert out.top1_class in ["normal", "tumor"]
    assert 0.0 <= out.top1_confidence <= 1.0
    assert len(out.class_probabilities) == 2
    assert out.embedding.shape == (576,)
    assert out.architecture == "MobileNetV3-Small"
    assert out.status == "ACTIVE"


def test_ml_orchestrator_predict_oral(sample_image_bytes):
    orchestrator = MLOrchestrator(device="cpu")
    out = orchestrator.predict(category="oral", image_bytes=sample_image_bytes)

    assert out.category == "oral"
    assert out.top1_class in ["normal", "oscc"]
    assert 0.0 <= out.top1_confidence <= 1.0
    assert len(out.class_probabilities) == 2
    assert out.embedding.shape == (576,)
    assert out.architecture == "MobileNetV3-Small"
    assert out.status == "ACTIVE"


def test_ml_orchestrator_untrained_refusal(sample_image_bytes):
    orchestrator = MLOrchestrator(device="cpu")
    with pytest.raises(UntrainedModelError):
        orchestrator.predict(category="breast", image_bytes=sample_image_bytes)
