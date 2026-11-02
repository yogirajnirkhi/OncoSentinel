"""
OncoSentinel v2.0 — Pluggable Model Adapter Interface
Allows standalone custom neural architectures (e.g. MobileNetV3, ResNet, EfficientNet)
to seamlessly integrate with the OncoSentinel inference, XAI, and safety pipeline.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
import torch


class UntrainedModelError(RuntimeError):
    """Raised when an inference is requested for a category without a trained model checkpoint."""

    def __init__(self, category: str, message: Optional[str] = None) -> None:
        self.category = category
        super().__init__(
            message
            or f"Category '{category}' has no trained model checkpoint deployed (status: UNTRAINED)."
        )


@dataclass
class ModelPredictionResult:
    category: str
    top1_class: str
    top1_index: int
    top1_confidence: float
    class_probabilities: dict[str, float]
    logits: np.ndarray
    embedding: np.ndarray
    feature_map: torch.Tensor
    model_version: str
    architecture: str
    status: str  # ACTIVE | UNTRAINED


class BaseModelAdapter(ABC):
    """Abstract base class for all category model adapters."""

    def __init__(self, category: str, class_mapping: dict[int, str]) -> None:
        self.category = category
        self.class_mapping = class_mapping

    @property
    @abstractmethod
    def is_trained(self) -> bool:
        pass

    @property
    @abstractmethod
    def model_version(self) -> str:
        pass

    @property
    @abstractmethod
    def architecture(self) -> str:
        pass

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        pass

    @abstractmethod
    def predict(self, image_tensor: torch.Tensor) -> ModelPredictionResult:
        """
        Executes forward pass given a normalized (1, 3, 224, 224) image tensor.
        """
        pass
