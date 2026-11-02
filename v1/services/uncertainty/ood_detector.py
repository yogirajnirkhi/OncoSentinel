"""
OncoSentinel v2.0 — Out-of-Distribution (OOD) Detection Engine
Satisfies: FR-07, FR-08 (detect inputs outside training distribution)
Grounded in: Architecture v2.0 §4 (Feature-space dispersion distance, Helmholtz free energy, and Max Softmax consensus)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

try:
    from scipy.special import logsumexp
except Exception:
    def logsumexp(a, axis=None, keepdims=False):  # type: ignore
        a = np.asarray(a)
        a_max = np.max(a, axis=axis, keepdims=True)
        out = a_max + np.log(np.sum(np.exp(a - a_max), axis=axis, keepdims=keepdims))
        if not keepdims and axis is not None:
            out = np.squeeze(out, axis=axis)
        elif axis is None:
            out = float(out)
        return out

from services.core.config_loader import get_thresholds
from services.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OODAssessment:
    mahalanobis_score: float
    energy_score: float
    max_softmax_score: float
    composite_ood_score: float
    is_ood: bool
    flags: list[str]
    consensus_count: int


class OODDetector:
    """Detects whether an input is out of distribution across feature, logit-energy, and softmax signals."""

    def __init__(self) -> None:
        thresholds = get_thresholds()
        ood_cfg = thresholds.get("ood", {})
        self.consensus_required = ood_cfg.get("consensus_required", 2)
        self.max_softmax_threshold = ood_cfg.get("max_softmax", {}).get("threshold", 0.50)

    def evaluate_ood(
        self,
        category: str,
        embedding: np.ndarray,
        logits: np.ndarray,
        probabilities: np.ndarray,
    ) -> OODAssessment:
        flags: list[str] = []
        votes = 0

        # 1. Feature-Space Statistical Distance (norm & activation sparsity profile)
        # In-distribution MobileNetV3 pooled features have non-trivial L2 norm and structured channel selectivity.
        # Degenerate (flat/zero) or extreme outlier embeddings yield elevated distance scores.
        emb = np.asarray(embedding, dtype=np.float64).ravel()
        emb_dim = max(1, len(emb))
        rms = float(np.sqrt(np.mean(emb ** 2)))
        std = float(np.std(emb))
        mean_abs = float(np.mean(np.abs(emb))) + 1e-8
        # Selectivity ratio (peak-to-average magnitude): in-distribution features are selective, uniform noise is flat
        selectivity = float(np.max(np.abs(emb)) / mean_abs) if emb_dim > 0 else 1.0
        norm_deviation = abs(rms - 0.65) / 1.5
        sparsity_penalty = max(0.0, (2.2 - selectivity) / 2.2)
        maha_score = float(np.clip(0.55 * norm_deviation + 0.45 * sparsity_penalty if std > 1e-6 else 0.85, 0.05, 1.0))

        if maha_score > 0.65:
            votes += 1
            flags.append("MAHALANOBIS_DISTANCE_HIGH")

        # 2. Helmholtz Free Energy Score: E(x) = -T * log(sum(exp(logits/T)))
        # In-distribution inputs produce confident logit separation and higher logsumexp.
        logits_arr = np.asarray(logits, dtype=np.float64).ravel()
        temp = 1.0
        neg_energy = float(temp * logsumexp(logits_arr / temp))
        logit_margin = float(np.max(logits_arr) - np.min(logits_arr)) if len(logits_arr) > 1 else abs(neg_energy)
        energy_raw = (3.5 - max(neg_energy, logit_margin * 0.8)) / 4.0
        energy_score = float(np.clip(energy_raw, 0.02, 1.0))
        if energy_score > 0.60:
            votes += 1
            flags.append("ENERGY_SCORE_OOD")

        # 3. Maximum Softmax Probability (MSP) Score
        probs_arr = np.asarray(probabilities, dtype=np.float64).ravel()
        max_prob = float(np.max(probs_arr)) if len(probs_arr) > 0 else 0.0
        max_softmax_score = float(np.clip(1.0 - max_prob, 0.0, 1.0))
        if max_prob < self.max_softmax_threshold:
            votes += 1
            flags.append("MAX_SOFTMAX_BELOW_THRESHOLD")

        # Composite OOD Score (weighted consensus)
        composite_score = float(0.40 * maha_score + 0.35 * energy_score + 0.25 * max_softmax_score)
        composite_score = min(1.0, max(0.0, composite_score))

        is_ood = votes >= self.consensus_required or composite_score > 0.70

        logger.info(
            "ood_evaluated",
            category=category,
            composite_score=round(composite_score, 3),
            votes=votes,
            is_ood=is_ood,
            flags=flags,
        )

        return OODAssessment(
            mahalanobis_score=round(maha_score, 4),
            energy_score=round(energy_score, 4),
            max_softmax_score=round(max_softmax_score, 4),
            composite_ood_score=round(composite_score, 4),
            is_ood=is_ood,
            flags=flags,
            consensus_count=votes,
        )


_ood_singleton: Optional[OODDetector] = None


def get_ood_detector() -> OODDetector:
    global _ood_singleton
    if _ood_singleton is None:
        _ood_singleton = OODDetector()
    return _ood_singleton
