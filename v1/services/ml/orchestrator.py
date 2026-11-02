"""
OncoSentinel v2.0 — ML Inference Orchestrator
Satisfies: FR-04, FR-05, SRS §3
Coordinates neural network inference across trained category adapters (MobileNetV3)
and safely refuses execution for categories that remain UNTRAINED.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from PIL import Image

from services.core.config_loader import get_category_config
from services.core.logging import get_logger
from services.ml.adapters.base import (
    BaseModelAdapter,
    ModelPredictionResult,
    UntrainedModelError,
)
from services.ml.adapters.torchvision_adapter import (
    MobileNetV3Adapter,
    UntrainedModelAdapter,
)

logger = get_logger(__name__)


@dataclass
class ModelOutput:
    category: str
    top1_class: str
    top1_index: int
    top1_confidence: float
    class_probabilities: dict[str, float]
    logits: np.ndarray
    embedding: np.ndarray
    feature_map: torch.Tensor
    model_version: str
    architecture: str = "MobileNetV3-Small"
    status: str = "ACTIVE"


class MLOrchestrator:
    """Manages neural network inference across standalone trained adapters and scaffolded categories."""

    def __init__(self, device: Optional[str] = None) -> None:
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.adapters: dict[str, BaseModelAdapter] = {}
        self._initialize_adapters()
        logger.info(
            "ml_orchestrator_initialized",
            device=str(self.device),
            active_models=[k for k, v in self.adapters.items() if v.is_trained],
            untrained_models=[k for k, v in self.adapters.items() if not v.is_trained],
        )

    def _initialize_adapters(self) -> None:
        categories = [
            "breast", "kidney", "all_leukemia", "oral",
            "colon", "lung", "lung_colon", "lymphoma", "brain", "cervical"
        ]

        # Directory roots to discover model checkpoints
        root_dir = Path(__file__).resolve().parents[3]
        search_dirs = [
            root_dir / "models",
            Path("models"),
            Path("../models"),
            Path("artifacts/models"),
            Path("v1/artifacts/models"),
            root_dir,
            Path(".."),
            Path("."),
        ]

        specs = [
            {
                "category": "kidney",
                "filenames": ["kidney_model.pth", "kidney.pth"],
                "default_cls": {0: "normal", 1: "tumor"},
                "version": "v2.0.0-kidney-mbv3s",
                "aliases": ["kidney", "renal"],
            },
            {
                "category": "oral",
                "filenames": ["oral_model.pth", "oral.pth"],
                "default_cls": {0: "normal", 1: "oscc"},
                "version": "v2.0.0-oral-mbv3s",
                "aliases": ["oral", "oscc"],
            },
            {
                "category": "all_leukemia",
                "filenames": ["ALL.pth", "all.pth", "leukemia.pth"],
                "default_cls": {0: "all_benign", 1: "all_early", 2: "all_pre", 3: "all_pro"},
                "version": "v2.0.0-all-mbv3s",
                "aliases": ["all_leukemia", "leukemia", "all"],
            },
            {
                "category": "brain",
                "filenames": ["brain_tumor.pth", "brain.pth"],
                "default_cls": {0: "brain_glioma", 1: "brain_menin", 2: "brain_tumor"},
                "version": "v2.0.0-brain-mbv3s",
                "aliases": ["brain", "brain_tumor"],
            },
            {
                "category": "cervical",
                "filenames": ["Cervical.pth", "cervical.pth"],
                "default_cls": {0: "cervix_dyk", 1: "cervix_koc", 2: "cervix_mep", 3: "cervix_pab", 4: "cervix_sfi"},
                "version": "v2.0.0-cervical-mbv3s",
                "aliases": ["cervical", "cervix"],
            },
            {
                "category": "colon",
                "filenames": ["colon.pth", "colon_model.pth"],
                "default_cls": {0: "colon_aca", 1: "colon_bnt"},
                "version": "v2.0.0-colon-mbv3s",
                "aliases": ["colon"],
            },
            {
                "category": "lung",
                "filenames": ["lung.pth", "lung_model.pth"],
                "default_cls": {0: "lung_aca", 1: "lung_bnt", 2: "lung_scc"},
                "version": "v2.0.0-lung-mbv3s",
                "aliases": ["lung"],
            },
        ]

        for spec in specs:
            cat = spec["category"]
            ckpt = None
            for s_dir in search_dirs:
                if not s_dir.exists():
                    continue
                for fname in spec["filenames"]:
                    candidate = s_dir / fname
                    if candidate.exists() and candidate.is_file():
                        ckpt = candidate
                        break
                if ckpt:
                    break

            try:
                cat_cfg = get_category_config(cat)
                cls_map = cat_cfg.get("class_mapping", spec["default_cls"])
            except Exception:
                cls_map = spec["default_cls"]

            if ckpt:
                try:
                    adapter = MobileNetV3Adapter(
                        category=cat,
                        checkpoint_path=ckpt,
                        class_mapping=cls_map,
                        device=self.device,
                        version=spec["version"],
                    )
                    self.adapters[cat] = adapter
                    for alias in spec["aliases"]:
                        self.adapters[alias] = adapter
                except Exception as exc:
                    logger.error(f"{cat}_adapter_load_failed", error=str(exc))
                    self.adapters[cat] = UntrainedModelAdapter(cat, cls_map)
            else:
                self.adapters[cat] = UntrainedModelAdapter(cat, cls_map)

        # Fallback stubs for remaining categories
        for cat in categories:
            if cat not in self.adapters:
                try:
                    cat_cfg = get_category_config(cat)
                    cls_map = cat_cfg.get("class_mapping", {})
                except Exception:
                    cls_map = {}
                self.adapters[cat] = UntrainedModelAdapter(cat, cls_map)

    def has_trained_model(self, category: str) -> bool:
        norm_cat = category.lower().strip()
        if norm_cat == "lung_colon":
            return self.has_trained_model("colon") or self.has_trained_model("lung")
        adapter = self.adapters.get(norm_cat)
        return adapter is not None and adapter.is_trained

    def preprocess_image(self, image_bytes: bytes) -> torch.Tensor:
        """Preprocesses raw image bytes into normalized (1, 3, 224, 224) tensor."""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((224, 224), Image.Resampling.BILINEAR)
        arr = np.array(img, dtype=np.float32) / 255.0

        # Standard ImageNet normalization
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        arr = (arr - mean) / std

        # HWC -> CHW -> NCHW
        tensor = torch.from_numpy(arr.transpose(2, 0, 1)).unsqueeze(0).to(self.device)
        return tensor

    def predict(self, category: str, image_bytes: bytes) -> ModelOutput:
        """Executes forward pass through trained category adapter."""
        norm_cat = category.lower().strip()
        if norm_cat == "lung_colon":
            c_adapter = self.adapters.get("colon")
            l_adapter = self.adapters.get("lung")
            if (c_adapter and c_adapter.is_trained) and (l_adapter and l_adapter.is_trained):
                tensor = self.preprocess_image(image_bytes)
                res_c = c_adapter.predict(tensor)
                res_l = l_adapter.predict(tensor)
                combined_logits = np.concatenate([res_c.logits, res_l.logits]).astype(np.float32)
                shifted = combined_logits - np.max(combined_logits)
                exp_logits = np.exp(shifted)
                combined_probs = exp_logits / np.sum(exp_logits)
                cls_names = ["colon_aca", "colon_bnt", "lung_aca", "lung_bnt", "lung_scc"]
                class_probs = {cls_names[i]: float(combined_probs[i]) for i in range(len(cls_names))}
                top1_idx = int(np.argmax(combined_probs))
                top1_class = cls_names[top1_idx]
                top1_conf = float(combined_probs[top1_idx])
                chosen = res_c if top1_idx < 2 else res_l
                return ModelOutput(
                    category="lung_colon",
                    top1_class=top1_class,
                    top1_index=top1_idx,
                    top1_confidence=top1_conf,
                    class_probabilities=class_probs,
                    logits=combined_logits,
                    embedding=chosen.embedding,
                    feature_map=chosen.feature_map,
                    model_version=chosen.model_version,
                    architecture=chosen.architecture,
                    status="ACTIVE",
                )
            elif c_adapter and c_adapter.is_trained:
                adapter = c_adapter
            elif l_adapter and l_adapter.is_trained:
                adapter = l_adapter
            else:
                raise UntrainedModelError("lung_colon")
        else:
            if norm_cat not in self.adapters:
                raise KeyError(f"Unsupported category '{category}' in ML orchestrator.")
            adapter = self.adapters[norm_cat]
            if not adapter.is_trained:
                raise UntrainedModelError(norm_cat)

        tensor = self.preprocess_image(image_bytes)
        res = adapter.predict(tensor)

        return ModelOutput(
            category=res.category,
            top1_class=res.top1_class,
            top1_index=res.top1_index,
            top1_confidence=res.top1_confidence,
            class_probabilities=res.class_probabilities,
            logits=res.logits,
            embedding=res.embedding,
            feature_map=res.feature_map,
            model_version=res.model_version,
            architecture=res.architecture,
            status=res.status,
        )


_orchestrator_singleton: Optional[MLOrchestrator] = None


def get_ml_orchestrator() -> MLOrchestrator:
    global _orchestrator_singleton
    if _orchestrator_singleton is None:
        _orchestrator_singleton = MLOrchestrator()
    return _orchestrator_singleton
