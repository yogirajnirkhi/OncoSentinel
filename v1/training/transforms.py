"""
OncoSentinel v2.0 — Modality-Aware Transforms and Preprocessing
Satisfies: Master Roadmap §5, §9.2
Applies deterministic evaluation transforms and modality-appropriate train transforms.
"""
from __future__ import annotations

from typing import Callable, Tuple

import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image


def get_modality_transforms(
    modality: str,
    image_size: Tuple[int, int] = (224, 224),
    is_training: bool = False,
) -> Callable[[Image.Image | np.ndarray], torch.Tensor]:
    """Returns modality-appropriate data transformation pipeline."""
    norm_mod = modality.lower().strip()

    # Base ImageNet stats for transfer feature extraction
    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]

    if is_training:
        if norm_mod in ["histology", "microscopy", "cytology"]:
            # Histology & cytology benefit from 90-degree rotations, flips, and slight color jitter
            transform = T.Compose([
                T.Resize(image_size),
                T.RandomHorizontalFlip(p=0.5),
                T.RandomVerticalFlip(p=0.5),
                T.ColorJitter(brightness=0.1, contrast=0.1),
                T.ToTensor(),
                T.Normalize(mean=mean, std=std),
            ])
        elif norm_mod == "ct":
            # CT scans benefit from slight scaling and horizontal flips (axial symmetry)
            transform = T.Compose([
                T.Resize(image_size),
                T.RandomHorizontalFlip(p=0.5),
                T.RandomRotation(degrees=10),
                T.ToTensor(),
                T.Normalize(mean=mean, std=std),
            ])
        elif norm_mod == "ultrasound":
            # Ultrasound benefits from mild horizontal flips and small affine shifts
            transform = T.Compose([
                T.Resize(image_size),
                T.RandomHorizontalFlip(p=0.5),
                T.RandomRotation(degrees=7),
                T.ToTensor(),
                T.Normalize(mean=mean, std=std),
            ])
        else:
            # Default MRI or generic training transform
            transform = T.Compose([
                T.Resize(image_size),
                T.RandomHorizontalFlip(p=0.5),
                T.ToTensor(),
                T.Normalize(mean=mean, std=std),
            ])
    else:
        # Deterministic evaluation transforms
        transform = T.Compose([
            T.Resize(image_size),
            T.ToTensor(),
            T.Normalize(mean=mean, std=std),
        ])

    def apply_transform(img_or_arr: Image.Image | np.ndarray) -> torch.Tensor:
        if isinstance(img_or_arr, np.ndarray):
            if img_or_arr.ndim == 2:
                # 2D grayscale -> RGB
                img = Image.fromarray(img_or_arr).convert("RGB")
            else:
                img = Image.fromarray(img_or_arr.astype(np.uint8)).convert("RGB")
        else:
            img = img_or_arr.convert("RGB")
        return transform(img)

    return apply_transform
