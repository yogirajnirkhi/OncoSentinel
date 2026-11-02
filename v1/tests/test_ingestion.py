"""
Tests for Ingestion & Quality Validation (FR-01, FR-02)
"""
from __future__ import annotations

from services.ingestion.validator import ImageQualityValidator


def test_valid_image_passes_quality_gate(sample_image_bytes):
    validator = ImageQualityValidator()
    score, flags, passed = validator.assess_image_bytes(sample_image_bytes)
    assert passed is True
    assert score >= 0.40


def test_degraded_image_fails_quality_gate(degraded_image_bytes):
    validator = ImageQualityValidator()
    score, flags, passed = validator.assess_image_bytes(degraded_image_bytes)
    assert passed is False
    assert score < 0.40
    assert "UNDERSIZED_RESOLUTION" in flags or "LOW_CONTRAST" in flags


def test_corrupt_bytes_graceful_handling():
    validator = ImageQualityValidator()
    score, flags, passed = validator.assess_image_bytes(b"not_an_image")
    assert passed is False
    assert score == 0.0
    assert "CORRUPT_OR_UNREADABLE_IMAGE" in flags
