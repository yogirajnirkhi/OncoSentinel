"""
Tests for Checkpoint Manager & Weight Cryptographic Verification (FR-26, NFR-12)
Validates SHA-256 integrity checks, metadata tracking, and model weight persistence.
"""
from __future__ import annotations

import tempfile
import torch
import torch.nn as nn

from services.ml.checkpoints import CheckpointManager


class TinyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(10, 2)

    def forward(self, x):
        return self.fc(x)


def test_checkpoint_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = CheckpointManager(checkpoint_dir=tmpdir)
        model = TinyModel()

        # Set specific weight to verify restoration
        with torch.no_grad():
            model.fc.weight.fill_(3.1415)

        ckpt_info = mgr.save_checkpoint(
            model=model,
            model_id="test_tiny_v1",
            category="breast",
            epoch=5,
            metrics={"val_loss": 0.215, "val_auc": 0.942},
        )

        assert ckpt_info.model_id == "test_tiny_v1"
        assert ckpt_info.epoch == 5
        assert len(ckpt_info.weight_sha256) == 64  # Valid SHA-256 hex string

        # Load into fresh model
        new_model = TinyModel()
        loaded_info = mgr.load_checkpoint(
            model_id="test_tiny_v1",
            model=new_model,
            verify_hash=True,
        )

        assert loaded_info.model_id == "test_tiny_v1"
        assert torch.allclose(new_model.fc.weight, torch.tensor(3.1415))


def test_checkpoint_hash_verification():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = CheckpointManager(checkpoint_dir=tmpdir)
        model = TinyModel()

        ckpt_info = mgr.save_checkpoint(
            model=model,
            model_id="test_verify_hash",
            category="kidney",
        )

        # Verification against matching hash succeeds
        assert mgr.verify_model_weights(model, ckpt_info.weight_sha256) is True

        # Mutate model weights
        with torch.no_grad():
            model.fc.weight[0, 0] += 1.0

        # Verification against previous hash must fail (tampering / drift detected)
        assert mgr.verify_model_weights(model, ckpt_info.weight_sha256) is False


def test_checkpoint_list_checkpoints():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = CheckpointManager(checkpoint_dir=tmpdir)
        model1 = TinyModel()
        model2 = TinyModel()

        mgr.save_checkpoint(model1, "breast_chk_01", category="breast")
        mgr.save_checkpoint(model2, "brain_chk_02", category="brain")

        ckpts = mgr.list_checkpoints()
        ids = [c["model_id"] for c in ckpts]
        assert "breast_chk_01" in ids
        assert "brain_chk_02" in ids
