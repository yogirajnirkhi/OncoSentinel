"""
OncoSentinel v2.0 — Neural Checkpoint & Model Weight Manager
Satisfies: FR-26 (Model registry & artifacts), NFR-12 (Reproducibility & versioning)
Grounded in: Architecture v2.0 §2 (Shared backbone + 8 category heads)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import torch

from services.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CheckpointMetadata:
    model_id: str
    category: str
    version: str
    dataset_lineage: str
    sha256_hash: str
    created_at: str
    parameters_count: int
    validation_auc: Optional[float] = None
    expected_ece: Optional[float] = None
    status: str = "SYNTHETIC_BASELINE"
    epoch: Optional[int] = None
    metrics: Optional[dict[str, Any]] = None

    @property
    def weight_sha256(self) -> str:
        return self.sha256_hash


class CheckpointManager:
    """
    Manages loading, saving, and cryptographic validation of neural weights
    for the shared backbone and eight category heads.
    Adheres strictly to Roadmap v2.0: zero unmeasured default metrics.
    """

    def __init__(self, checkpoints_dir: Optional[Path | str] = None, checkpoint_dir: Optional[Path | str] = None) -> None:
        target_dir = checkpoints_dir or checkpoint_dir or (Path("data") / "checkpoints")
        self.checkpoints_dir = Path(target_dir)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

    def _compute_sha256(self, file_path: Path) -> str:
        """Computes SHA-256 cryptographic hash of a weight file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _compute_model_sha256(self, model: torch.nn.Module) -> str:
        """Computes deterministic SHA-256 hash of a model state_dict."""
        hasher = hashlib.sha256()
        state = model.state_dict()
        for k in sorted(state.keys()):
            hasher.update(k.encode("utf-8"))
            hasher.update(state[k].detach().cpu().numpy().tobytes())
        return hasher.hexdigest()

    def save_checkpoint(
        self,
        module: Optional[torch.nn.Module] = None,
        model_id: str = "unnamed_model",
        category: str = "general",
        version: str = "v1.0.0",
        dataset_lineage: str = "unspecified",
        validation_auc: Optional[float] = None,
        expected_ece: Optional[float] = None,
        status: str = "SYNTHETIC_BASELINE",
        epoch: Optional[int] = None,
        metrics: Optional[dict[str, Any]] = None,
        model: Optional[torch.nn.Module] = None,
    ) -> CheckpointMetadata:
        """Serializes module weights and generates metadata with SHA-256 hash.
        Zero fake default metrics: unmeasured values remain None.
        """
        mod = module if module is not None else model
        if mod is None:
            raise ValueError("Must provide either 'module' or 'model' to save_checkpoint.")

        weight_filename = f"{model_id}_{version}.pt" if not model_id.endswith(f"_{version}") else f"{model_id}.pt"
        meta_filename = f"{model_id}_{version}.json" if not model_id.endswith(f"_{version}") else f"{model_id}.json"

        weight_path = self.checkpoints_dir / weight_filename
        meta_path = self.checkpoints_dir / meta_filename

        # Save weights
        torch.save(mod.state_dict(), weight_path)
        sha256 = self._compute_sha256(weight_path)
        param_count = sum(p.numel() for p in mod.parameters())

        meta = CheckpointMetadata(
            model_id=model_id,
            category=category,
            version=version,
            dataset_lineage=dataset_lineage,
            validation_auc=validation_auc,
            expected_ece=expected_ece,
            sha256_hash=sha256,
            created_at=datetime.utcnow().isoformat(),
            parameters_count=param_count,
            status=status,
            epoch=epoch,
            metrics=metrics,
        )

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(asdict(meta), f, indent=2)

        logger.info(
            "model_checkpoint_saved",
            model_id=model_id,
            version=version,
            sha256=sha256[:12],
            status=status,
            path=str(weight_path),
        )
        return meta

    def load_checkpoint(
        self,
        module: Optional[torch.nn.Module] = None,
        model_id: str = "unnamed_model",
        version: str = "v1.0.0",
        verify_integrity: bool = True,
        verify_hash: bool = True,
        model: Optional[torch.nn.Module] = None,
    ) -> CheckpointMetadata:
        """Loads weights into module with SHA-256 integrity check."""
        mod = module if module is not None else model
        if mod is None:
            raise ValueError("Must provide either 'module' or 'model' to load_checkpoint.")

        weight_filename = f"{model_id}_{version}.pt" if not model_id.endswith(f"_{version}") else f"{model_id}.pt"
        meta_filename = f"{model_id}_{version}.json" if not model_id.endswith(f"_{version}") else f"{model_id}.json"

        weight_path = self.checkpoints_dir / weight_filename
        meta_path = self.checkpoints_dir / meta_filename

        # Fallback without version suffix if exact file exists
        if not weight_path.exists() and (self.checkpoints_dir / f"{model_id}.pt").exists():
            weight_path = self.checkpoints_dir / f"{model_id}.pt"
            meta_path = self.checkpoints_dir / f"{model_id}.json"

        if not weight_path.exists():
            raise FileNotFoundError(f"Weight checkpoint not found at {weight_path}")

        meta = None
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_dict = json.load(f)
                meta = CheckpointMetadata(**meta_dict)

            should_verify = verify_integrity and verify_hash
            if should_verify:
                current_hash = self._compute_sha256(weight_path)
                if current_hash != meta.sha256_hash:
                    raise ValueError(
                        f"Integrity check failed for {weight_path}: "
                        f"expected {meta.sha256_hash}, got {current_hash}"
                    )

        state_dict = torch.load(weight_path, map_location="cpu")
        mod.load_state_dict(state_dict)
        logger.info("model_checkpoint_loaded", model_id=model_id, version=version)
        return meta or CheckpointMetadata(
            model_id=model_id,
            category="unknown",
            version=version,
            dataset_lineage="unknown",
            validation_auc=None,
            expected_ece=None,
            sha256_hash=self._compute_sha256(weight_path),
            created_at=datetime.utcnow().isoformat(),
            parameters_count=sum(p.numel() for p in mod.parameters()),
            status="UNVERIFIED",
        )

    def verify_model_weights(self, model: torch.nn.Module, expected_sha256: str) -> bool:
        """Verifies currently loaded model tensors match an expected weight hash."""
        # Check against either file sha256 or in-memory state tensor sha256
        current_hash = self._compute_model_sha256(model)
        # Also check against any matching checkpoint file in checkpoints_dir
        for pt_file in self.checkpoints_dir.glob("*.pt"):
            if self._compute_sha256(pt_file) == expected_sha256:
                try:
                    ref_state = torch.load(pt_file, map_location="cpu")
                    cur_state = model.state_dict()
                    match = True
                    for k in ref_state:
                        if not torch.allclose(ref_state[k], cur_state[k]):
                            match = False
                            break
                    return match
                except Exception:
                    pass
        return current_hash == expected_sha256

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """Lists all registered checkpoints in the checkpoints directory."""
        results: list[dict[str, Any]] = []
        for meta_file in sorted(self.checkpoints_dir.glob("*.json")):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    results.append(data)
            except Exception as exc:
                logger.warning("corrupt_checkpoint_metadata", file=str(meta_file), error=str(exc))
        return results

    def ensure_baseline_checkpoints(self, backbone: torch.nn.Module, heads: dict[str, torch.nn.Module]) -> None:
        """Ensures synthetic baseline checkpoints are recorded with explicit unmeasured state."""
        backbone_path = self.checkpoints_dir / "backbone_v2.0.0.pt"
        if not backbone_path.exists():
            self.save_checkpoint(
                module=backbone,
                model_id="backbone",
                category="shared",
                version="v2.0.0",
                dataset_lineage="multi-cancer-synthetic-baseline",
                validation_auc=None,
                expected_ece=None,
                status="SYNTHETIC_BASELINE",
            )

        for cat, head in heads.items():
            head_path = self.checkpoints_dir / f"head_{cat}_v2.0.0.pt"
            if not head_path.exists():
                self.save_checkpoint(
                    module=head,
                    model_id=f"head_{cat}",
                    category=cat,
                    version="v2.0.0",
                    dataset_lineage=f"{cat}-synthetic-baseline",
                    validation_auc=None,
                    expected_ece=None,
                    status="SYNTHETIC_BASELINE",
                )


_checkpoint_manager_singleton: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    global _checkpoint_manager_singleton
    if _checkpoint_manager_singleton is None:
        _checkpoint_manager_singleton = CheckpointManager()
    return _checkpoint_manager_singleton
