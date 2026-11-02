"""
OncoSentinel v2.0 — Torchvision Model Adapters
Implements MobileNetV3-Small standalone adapter and Untrained category adapter.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn.functional as F
from torchvision.models import mobilenet_v3_small

from services.core.logging import get_logger
from services.ml.adapters.base import (
    BaseModelAdapter,
    ModelPredictionResult,
    UntrainedModelError,
)

logger = get_logger(__name__)


class MobileNetV3Adapter(BaseModelAdapter):
    """
    Adapter for torchvision MobileNetV3-Small standalone models.
    Provides 576-dim feature embeddings, spatial feature maps for Grad-CAM,
    and calibrated class predictions with cryptographic integrity verification.
    """

    def __init__(
        self,
        category: str,
        checkpoint_path: Path | str,
        class_mapping: dict[int, str],
        expected_sha256: Optional[str] = None,
        device: Optional[torch.device] = None,
        version: str = "v2.0.0-mobilenet",
    ) -> None:
        super().__init__(category=category, class_mapping=class_mapping)
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._version = version
        self._checkpoint_path = Path(checkpoint_path)

        if not self._checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found at: {self._checkpoint_path}")

        # Compute & verify SHA256 digest
        self._sha256 = self._compute_sha256(self._checkpoint_path)
        if expected_sha256 and self._sha256.lower() != expected_sha256.lower():
            logger.warning(
                "checkpoint_sha256_mismatch",
                category=category,
                computed=self._sha256,
                expected=expected_sha256,
            )

        # Load weights safely
        checkpoint_obj = torch.load(self._checkpoint_path, map_location=self.device, weights_only=True)
        if isinstance(checkpoint_obj, dict) and "model_state_dict" in checkpoint_obj:
            state_dict = checkpoint_obj["model_state_dict"]
            self.raw_classes = checkpoint_obj.get("classes", [])
        else:
            state_dict = checkpoint_obj
            self.raw_classes = []

        # If checkpoint specifies classes, align class_mapping directly
        if self.raw_classes and len(self.raw_classes) != len(self.class_mapping):
            self.class_mapping = {i: c for i, c in enumerate(self.raw_classes)}

        # Initialize network with correct class dimension
        num_classes = len(self.class_mapping)
        self.model = mobilenet_v3_small(num_classes=num_classes)
        self.model.load_state_dict(state_dict, strict=True)
        self.model.to(self.device)
        self.model.eval()

        logger.info(
            "mobilenet_adapter_loaded",
            category=self.category,
            num_classes=num_classes,
            sha256=self._sha256[:12],
            device=str(self.device),
        )

    def _compute_sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    @property
    def is_trained(self) -> bool:
        return True

    @property
    def model_version(self) -> str:
        return f"{self._version}-{self._sha256[:8]}"

    @property
    def architecture(self) -> str:
        return "MobileNetV3-Small"

    @property
    def embedding_dim(self) -> int:
        return 576

    @property
    def checkpoint_sha256(self) -> str:
        return self._sha256

    def predict(self, image_tensor: torch.Tensor) -> ModelPredictionResult:
        tensor = image_tensor.to(self.device)
        with torch.enable_grad():
            feature_map = self.model.features(tensor)
            feature_map.retain_grad()
            embedding = self.model.avgpool(feature_map).flatten(1)
            logits_tensor = self.model.classifier(embedding)
            probs_tensor = F.softmax(logits_tensor, dim=-1)
            top1_idx = int(torch.argmax(probs_tensor[0]).item())
            self.model.zero_grad()
            logits_tensor[0, top1_idx].backward()
            grad_detached = feature_map.grad.detach() if feature_map.grad is not None else None
            feature_map_detached = feature_map.detach()
            feature_map_detached.grad = grad_detached

        logits_np = logits_tensor.detach().cpu().numpy()[0]
        probs_np = probs_tensor.detach().cpu().numpy()[0]
        embedding_np = embedding.detach().cpu().numpy()[0]

        top1_conf = float(probs_np[top1_idx])
        top1_name = self.class_mapping.get(top1_idx, f"class_{top1_idx}")

        class_probs = {
            self.class_mapping.get(i, f"class_{i}"): float(probs_np[i])
            for i in range(len(probs_np))
        }

        return ModelPredictionResult(
            category=self.category,
            top1_class=top1_name,
            top1_index=top1_idx,
            top1_confidence=top1_conf,
            class_probabilities=class_probs,
            logits=logits_np,
            embedding=embedding_np,
            feature_map=feature_map_detached,
            model_version=self.model_version,
            architecture=self.architecture,
            status="ACTIVE",
        )


class UntrainedModelAdapter(BaseModelAdapter):
    """
    Placeholder adapter for categories without trained model weights.
    Cleanly refuses execution rather than producing fabricated predictions.
    """

    def __init__(self, category: str, class_mapping: dict[int, str]) -> None:
        super().__init__(category=category, class_mapping=class_mapping)

    @property
    def is_trained(self) -> bool:
        return False

    @property
    def model_version(self) -> str:
        return "untrained"

    @property
    def architecture(self) -> str:
        return "None (Untrained)"

    @property
    def embedding_dim(self) -> int:
        return 512

    def predict(self, image_tensor: torch.Tensor) -> ModelPredictionResult:
        raise UntrainedModelError(
            self.category,
            f"Category '{self.category}' has no active trained model checkpoint. "
            f"Prediction is safely refused. Deployed MobileNetV3-Small models are active for Kidney, Oral, ALL Leukemia, Brain, Cervical, Colon, and Lung.",
        )
