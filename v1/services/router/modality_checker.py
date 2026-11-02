"""
OncoSentinel v2.0 — Modality Checker
Satisfies: FR-03, FR-04 (validate modality against taxonomy per category)
"""
from __future__ import annotations

from typing import Tuple

from services.core.config_loader import get_supported_modalities
from services.core.logging import get_logger

logger = get_logger(__name__)


class ModalityChecker:
    """Verifies that the provided imaging/data modality is supported for the category."""

    def check(self, category: str, modality: str) -> Tuple[bool, list[str]]:
        """
        Returns:
            is_valid: bool
            supported_modalities: list[str]
        """
        try:
            supported = get_supported_modalities(category)
        except KeyError:
            return False, []

        norm_modality = modality.lower().strip()
        is_valid = norm_modality in [m.lower() for m in supported]
        return is_valid, supported
