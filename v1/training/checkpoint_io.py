"""
OncoSentinel v2.0 — Checkpoint I/O with SHA-256 Cryptographic Verification
Satisfies: Master Roadmap §10.2, §10.3, NFR-12
Ensures weight reproducibility, zero unmeasured default metrics, and tamper detection.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import torch
import torch.nn as nn


@dataclass
class CheckpointBundle:
    task_id: str
    run_id: str
    version: str
    checkpoint_path: str
    sha256_hash: str
    created_at: str
    num_parameters: int
    num_classes: int
    class_names: list[str]
    epoch: int
    status: str
    metrics: dict[str, Any]
    optimizer_saved: bool = False


class TrainingCheckpointIO:
    """Handles saving and loading of model checkpoints with cryptographic integrity."""

    def __init__(self, checkpoints_dir: Path | str) -> None:
        self.checkpoints_dir = Path(checkpoints_dir)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_sha256(file_path: Path | str) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def save_checkpoint(
        self,
        model: nn.Module,
        task_id: str,
        run_id: str,
        epoch: int,
        metrics: dict[str, Any],
        class_names: list[str],
        status: str = "TRAINED",
        optimizer: Optional[torch.optim.Optimizer] = None,
        version: str = "v1.0.0",
        tag: str = "best",
    ) -> CheckpointBundle:
        """Saves model weights, metadata, and optional optimizer state with SHA-256 fingerprint."""
        weight_file = self.checkpoints_dir / f"{task_id}_{tag}.pt"
        meta_file = self.checkpoints_dir / f"{task_id}_{tag}.json"

        payload: dict[str, Any] = {
            "model_state_dict": model.state_dict(),
            "epoch": epoch,
            "task_id": task_id,
            "run_id": run_id,
            "version": version,
            "class_names": class_names,
        }
        if optimizer is not None:
            payload["optimizer_state_dict"] = optimizer.state_dict()

        torch.save(payload, weight_file)
        sha256 = self.compute_sha256(weight_file)
        param_count = sum(p.numel() for p in model.parameters())

        bundle = CheckpointBundle(
            task_id=task_id,
            run_id=run_id,
            version=version,
            checkpoint_path=str(weight_file),
            sha256_hash=sha256,
            created_at=datetime.utcnow().isoformat(),
            num_parameters=param_count,
            num_classes=len(class_names),
            class_names=class_names,
            epoch=epoch,
            status=status,
            metrics=metrics,
            optimizer_saved=optimizer is not None,
        )

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(asdict(bundle), f, indent=2)

        return bundle

    def load_checkpoint(
        self,
        model: nn.Module,
        checkpoint_path: Path | str,
        verify_integrity: bool = True,
        optimizer: Optional[torch.optim.Optimizer] = None,
    ) -> CheckpointBundle:
        """Loads weights into model from checkpoint with optional SHA-256 validation."""
        ckpt_path = Path(checkpoint_path)
        if not ckpt_path.exists():
            raise FileNotFoundError(f"Checkpoint not found at: {ckpt_path}")

        meta_path = ckpt_path.with_suffix(".json")
        bundle_meta: Optional[CheckpointBundle] = None

        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_dict = json.load(f)
                bundle_meta = CheckpointBundle(**meta_dict)

            if verify_integrity:
                current_sha = self.compute_sha256(ckpt_path)
                if current_sha != bundle_meta.sha256_hash:
                    raise ValueError(
                        f"Cryptographic tampering or corruption detected in {ckpt_path}!\n"
                        f"Expected SHA-256: {bundle_meta.sha256_hash}\n"
                        f"Computed SHA-256: {current_sha}"
                    )

        checkpoint_data = torch.load(ckpt_path, map_location="cpu")
        if isinstance(checkpoint_data, dict) and "model_state_dict" in checkpoint_data:
            model.load_state_dict(checkpoint_data["model_state_dict"])
            if optimizer is not None and "optimizer_state_dict" in checkpoint_data:
                optimizer.load_state_dict(checkpoint_data["optimizer_state_dict"])
        else:
            # Raw state dict
            model.load_state_dict(checkpoint_data)

        return bundle_meta or CheckpointBundle(
            task_id="unknown",
            run_id="unknown",
            version="1.0.0",
            checkpoint_path=str(ckpt_path),
            sha256_hash=self.compute_sha256(ckpt_path),
            created_at=datetime.utcnow().isoformat(),
            num_parameters=sum(p.numel() for p in model.parameters()),
            num_classes=0,
            class_names=[],
            epoch=0,
            status="UNVERIFIED",
            metrics={},
        )
