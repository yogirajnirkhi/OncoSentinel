"""
OncoSentinel v2.0 — Multi-Cancer Category Heads
Satisfies: FR-05, SRS §2 (Authoritative Multi-Cancer taxonomy)
Classes strictly synchronized with configs/taxonomy.yaml and models/*.pth
"""
from __future__ import annotations

import torch
import torch.nn as nn


class CategoryHead(nn.Module):
    """Base classification head for cancer categories."""

    def __init__(self, in_features: int, num_classes: int, dropout: float = 0.2) -> None:
        super().__init__()
        self.num_classes = num_classes
        self.classifier = nn.Sequential(
            nn.Linear(in_features, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(256, num_classes),
        )

    def forward(self, embedding: torch.Tensor) -> torch.Tensor:
        return self.classifier(embedding)


class BreastHead(CategoryHead):
    """Breast Cancer Head: 2 classes (benign, malignant)."""
    def __init__(self, in_features: int = 512) -> None:
        super().__init__(in_features=in_features, num_classes=2)


class KidneyHead(CategoryHead):
    """Kidney Cancer Head: 2 classes (normal, tumor)."""
    def __init__(self, in_features: int = 512) -> None:
        super().__init__(in_features=in_features, num_classes=2)


class AllLeukemiaHead(CategoryHead):
    """Acute Lymphoblastic Leukemia Head: 4 classes (all_benign, all_early, all_pre, all_pro)."""
    def __init__(self, in_features: int = 512) -> None:
        super().__init__(in_features=in_features, num_classes=4)


class OralHead(CategoryHead):
    """Oral Cancer Head: 2 classes (normal, oscc)."""
    def __init__(self, in_features: int = 512) -> None:
        super().__init__(in_features=in_features, num_classes=2)


class ColonHead(CategoryHead):
    """Colon Cancer Head: 2 classes (colon_aca, colon_bnt)."""
    def __init__(self, in_features: int = 512) -> None:
        super().__init__(in_features=in_features, num_classes=2)


class LungHead(CategoryHead):
    """Lung Cancer Head: 3 classes (lung_aca, lung_bnt, lung_scc)."""
    def __init__(self, in_features: int = 512) -> None:
        super().__init__(in_features=in_features, num_classes=3)


class LungColonHead(CategoryHead):
    """Lung & Colon Head: 5 classes (colon_aca, colon_bnt, lung_aca, lung_bnt, lung_scc)."""
    def __init__(self, in_features: int = 512) -> None:
        super().__init__(in_features=in_features, num_classes=5)


class LymphomaHead(CategoryHead):
    """Lymphoma Head: 3 classes (cll, fl, mcl)."""
    def __init__(self, in_features: int = 512) -> None:
        super().__init__(in_features=in_features, num_classes=3)


class BrainHead(CategoryHead):
    """Brain Tumor Head: 3 classes (brain_glioma, brain_menin, brain_tumor)."""
    def __init__(self, in_features: int = 512) -> None:
        super().__init__(in_features=in_features, num_classes=3)


class CervicalHead(CategoryHead):
    """Cervical Cancer Head: 5 classes (cervix_dyk, cervix_koc, cervix_mep, cervix_pab, cervix_sfi)."""
    def __init__(self, in_features: int = 512) -> None:
        super().__init__(in_features=in_features, num_classes=5)


HEAD_REGISTRY: dict[str, type[CategoryHead]] = {
    "breast": BreastHead,
    "kidney": KidneyHead,
    "all_leukemia": AllLeukemiaHead,
    "oral": OralHead,
    "colon": ColonHead,
    "lung": LungHead,
    "lung_colon": LungColonHead,
    "lymphoma": LymphomaHead,
    "brain": BrainHead,
    "cervical": CervicalHead,
}


def build_category_head(category: str, in_features: int = 512) -> CategoryHead:
    """Factory creating the specific category head based on taxonomy configuration."""
    norm_cat = category.lower().strip()
    if norm_cat not in HEAD_REGISTRY:
        raise KeyError(f"Unsupported category head: '{category}'. Must be one of {list(HEAD_REGISTRY.keys())}")
    return HEAD_REGISTRY[norm_cat](in_features=in_features)
