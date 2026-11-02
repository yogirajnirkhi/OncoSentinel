"""
OncoSentinel v2.0 — Model Adapters Package
"""
from services.ml.adapters.base import (
    BaseModelAdapter,
    ModelPredictionResult,
    UntrainedModelError,
)
from services.ml.adapters.torchvision_adapter import (
    MobileNetV3Adapter,
    UntrainedModelAdapter,
)

__all__ = [
    "BaseModelAdapter",
    "ModelPredictionResult",
    "UntrainedModelError",
    "MobileNetV3Adapter",
    "UntrainedModelAdapter",
]
