"""
OncoSentinel v2.0 — Input Quality Validation Engine
Satisfies: FR-01, FR-02, NFR-01
Grounded in: Kourou et al. (2015) & Zhang et al. (2023) on data quality and normalization
"""
from __future__ import annotations

import io
from typing import Tuple

import numpy as np
from PIL import Image

from services.core.config_loader import get_thresholds
from services.core.logging import get_logger

logger = get_logger(__name__)


class ImageQualityValidator:
    """Validates image quality before routing to ML or RAG pipelines."""

    def __init__(self) -> None:
        thresholds = get_thresholds()
        q_thresh = thresholds.get("global", {}).get("quality", {})
        self.minimum_score = q_thresh.get("minimum_score", 0.40)
        self.review_score = q_thresh.get("review_score", 0.60)

    def assess_image_bytes(self, image_bytes: bytes) -> Tuple[float, list[str], bool]:
        """
        Assess quality of raw image bytes.
        Returns:
            quality_score: float in [0.0, 1.0]
            quality_flags: list of identified quality warnings/flags
            passed: True if score >= minimum_score
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img_gray = img.convert("L")
            arr = np.array(img_gray, dtype=np.float32)
        except Exception as exc:
            logger.warning("image_parse_failed", error=str(exc))
            return 0.0, ["CORRUPT_OR_UNREADABLE_IMAGE"], False

        flags: list[str] = []
        scores: list[float] = []

        # 1. Resolution Check
        width, height = img.size
        min_dim = min(width, height)
        if min_dim < 64:
            flags.append("UNDERSIZED_RESOLUTION")
            scores.append(0.1)
        elif min_dim < 128:
            flags.append("SUBOPTIMAL_RESOLUTION")
            scores.append(0.5)
        else:
            scores.append(1.0)

        # 2. Contrast & Dynamic Range
        std_dev = float(np.std(arr))
        if std_dev < 15.0:
            flags.append("LOW_CONTRAST")
            scores.append(0.3)
        elif std_dev < 30.0:
            flags.append("SUBOPTIMAL_CONTRAST")
            scores.append(0.7)
        else:
            scores.append(1.0)

        # 3. Blur Estimation (Laplacian Variance approximation)
        # Using discrete laplacian kernel [[0, 1, 0], [1, -4, 1], [0, 1, 0]]
        if arr.shape[0] > 4 and arr.shape[1] > 4:
            kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
            # Simple 2D convolution for blur estimation without requiring cv2
            laplacian_var = float(self._approx_laplacian_var(arr))
            if laplacian_var < 50.0:
                flags.append("SEVERE_BLUR")
                scores.append(0.2)
            elif laplacian_var < 150.0:
                flags.append("MILD_BLUR")
                scores.append(0.6)
            else:
                scores.append(1.0)
        else:
            scores.append(0.5)

        # 4. Clipping / Saturation
        saturated_pixels = np.sum((arr > 250) | (arr < 5)) / arr.size
        if saturated_pixels > 0.40:
            flags.append("HIGH_CLIPPING_OR_SATURATION")
            scores.append(0.4)
        else:
            scores.append(1.0)

        composite_score = float(np.mean(scores))
        passed = composite_score >= self.minimum_score

        logger.info(
            "image_quality_assessed",
            score=round(composite_score, 3),
            flags=flags,
            passed=passed,
            needs_review=(self.minimum_score <= composite_score < self.review_score),
        )
        return composite_score, flags, passed

    def _approx_laplacian_var(self, arr: np.ndarray) -> float:
        """Fast Laplacian variance computation for blur detection."""
        # 3x3 difference
        pad = np.pad(arr, 1, mode="edge")
        lap = (
            pad[:-2, 1:-1]
            + pad[2:, 1:-1]
            + pad[1:-1, :-2]
            + pad[1:-1, 2:]
            - 4 * arr
        )
        return float(np.var(lap))
