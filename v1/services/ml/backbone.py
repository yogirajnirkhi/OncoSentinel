"""
OncoSentinel v2.0 — Shared Feature Backbone
Satisfies: FR-05, SRS §3 (Shared Backbone -> Category Head architecture)
Grounded in: Architecture v2.0 §2 canonical shared-backbone design
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class SharedBackbone(nn.Module):
    """
    Multi-scale convolutional backbone providing:
    1. Spatial feature map (for Grad-CAM localization & XAI)
    2. Pooled latent embedding vector (dimension 512, for classification & OOD detection)
    """

    def __init__(self, embedding_dim: int = 512) -> None:
        super().__init__()
        # Stage 1: Initial conv + stem
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        # Stage 2: Feature extraction blocks
        self.layer1 = self._make_block(64, 128, stride=2)
        self.layer2 = self._make_block(128, 256, stride=2)
        self.layer3 = self._make_block(256, embedding_dim, stride=2)

        # Global average pooling
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))

    def _make_block(self, in_c: int, out_c: int, stride: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Conv2d(in_c, out_c, kernel_size=3, stride=stride, padding=1, bias=False),
            nn.BatchNorm2d(out_c),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_c, out_c, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(out_c),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Returns:
            embedding: (B, embedding_dim) pooled feature vector
            feature_map: (B, embedding_dim, H, W) final spatial activations for Grad-CAM
        """
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        feature_map = self.layer3(x)  # Retain spatial dimensions

        pooled = self.avgpool(feature_map)
        embedding = torch.flatten(pooled, 1)

        return embedding, feature_map
