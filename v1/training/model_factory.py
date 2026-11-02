"""
OncoSentinel v2.0 — Hybrid Shared Network Architecture & Model Factory
Satisfies: Master Roadmap §5, §7.2
Architecture: Modality-Aware Encoders (Ultrasound, CT, MRI, Microscopy/Histology) + Task-Specific Output Heads
"""
from __future__ import annotations

from typing import Any, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


class ConvBlock(nn.Module):
    """Basic convolutional residual block for medical image representation."""

    def __init__(self, in_channels: int, out_channels: int, stride: int = 1) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels),
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = F.relu(self.bn1(self.conv1(x)), inplace=True)
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        return F.relu(out, inplace=True)


class ModalityEncoder(nn.Module):
    """
    Modality-aware feature extractor that maps 2D medical images to a 512-dim embedding
    while preserving spatial feature activations for Grad-CAM explainability.
    """

    def __init__(self, modality_name: str, in_channels: int = 3, embedding_dim: int = 512) -> None:
        super().__init__()
        self.modality_name = modality_name
        self.in_channels = in_channels
        self.embedding_dim = embedding_dim

        # Initial stem
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=7, stride=2, padding=3, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1),
        )

        # Multi-scale residual stages
        self.stage1 = ConvBlock(64, 128, stride=2)
        self.stage2 = ConvBlock(128, 256, stride=2)
        self.stage3 = ConvBlock(256, 512, stride=2)

        # Global average pool
        self.gap = nn.AdaptiveAvgPool2d((1, 1))

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        x_stem = self.stem(x)
        x_s1 = self.stage1(x_stem)
        x_s2 = self.stage2(x_s1)
        spatial_features = self.stage3(x_s2)  # [B, 512, H, W]

        pooled = self.gap(spatial_features)    # [B, 512, 1, 1]
        embedding = torch.flatten(pooled, 1)   # [B, 512]
        return embedding, spatial_features


class TaskSpecificHead(nn.Module):
    """Task-specific classification projection head with calibrated logits."""

    def __init__(self, in_features: int = 512, num_classes: int = 2, dropout: float = 0.3) -> None:
        super().__init__()
        self.in_features = in_features
        self.num_classes = num_classes
        self.classifier = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(in_features, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout / 2.0),
            nn.Linear(256, num_classes),
        )

    def forward(self, embedding: torch.Tensor) -> torch.Tensor:
        return self.classifier(embedding)


class HybridMultiTaskModel(nn.Module):
    """
    Unified Hybrid Model composed of a modality-aware branch and a task-specific head.
    Can be loaded independently or connected to shared backbone weights.
    """

    def __init__(
        self,
        task_id: str,
        modality: str,
        num_classes: int,
        embedding_dim: int = 512,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        self.task_id = task_id
        self.modality = modality
        self.num_classes = num_classes
        self.embedding_dim = embedding_dim

        self.encoder = ModalityEncoder(modality_name=modality, embedding_dim=embedding_dim)
        self.head = TaskSpecificHead(in_features=embedding_dim, num_classes=num_classes, dropout=dropout)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        Returns:
            logits: [B, num_classes]
            embedding: [B, 512]
            spatial_features: [B, 512, H, W] (retained for Grad-CAM explainability)
        """
        embedding, spatial_features = self.encoder(x)
        logits = self.head(embedding)
        return logits, embedding, spatial_features


def build_hybrid_model(task_config: dict[str, Any]) -> HybridMultiTaskModel:
    """Factory creating a HybridMultiTaskModel from a task configuration dictionary."""
    task_id = task_config.get("task_id", "unnamed_task")
    modality = task_config.get("modality", "generic")
    model_cfg = task_config.get("model", {})
    num_classes = model_cfg.get("num_classes", len(task_config.get("data", {}).get("class_names", [0, 1])))
    embedding_dim = model_cfg.get("embedding_dim", 512)
    dropout = model_cfg.get("dropout", 0.3)

    return HybridMultiTaskModel(
        task_id=task_id,
        modality=modality,
        num_classes=num_classes,
        embedding_dim=embedding_dim,
        dropout=dropout,
    )
