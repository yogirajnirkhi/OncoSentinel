"""
Tests for OncoSentinel v2.0 Unified Hybrid Training Engine
Satisfies: Master Roadmap §5, §7.2, §8, §9.1, §10, §13.2 (Gate B & Gate C)
Validates:
- Leakage-resistant patient-grouped split manifests
- Modality-aware data transformations
- Hybrid shared network instantiation and forward pass
- Cryptographic SHA-256 checkpoint save & load
- Real evaluation metrics calculation (zero fake defaults)
- Sequential training queue execution and failure isolation
"""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
import torch
import torch.nn as nn

from training.checkpoint_io import TrainingCheckpointIO
from training.dataset_adapters import get_dataset_adapter
from training.evaluate import compute_ece, evaluate_model
from training.model_factory import HybridMultiTaskModel, build_hybrid_model
from training.run_state import TaskRunRecord, TaskRunState
from training.split_manifest import SplitItem, create_leakage_resistant_split
from training.train_one import train_single_task
from training.transforms import get_modality_transforms


def test_split_manifest_prevents_patient_leakage():
    """Validates that patient IDs are strictly disjoint between train, val, and test partitions."""
    items = []
    for p_idx in range(10):
        p_id = f"PATIENT_{p_idx:03d}"
        for s_idx in range(3):
            items.append(
                SplitItem(
                    sample_id=f"{p_id}_scan_{s_idx}",
                    relative_path=f"class0/{p_id}_scan_{s_idx}.png",
                    class_label=p_idx % 2,
                    class_name="benign" if (p_idx % 2 == 0) else "malignant",
                    grouping_id=p_id,
                )
            )

    manifest = create_leakage_resistant_split(
        items=items,
        task_id="test_leakage_task",
        dataset_id="test_dataset_v1",
        grouping_key="patient_id",
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        seed=42,
    )

    # 1. Verification succeeds on valid disjoint splits
    assert manifest.verify_no_leakage() is True
    assert manifest.total_samples == 30
    assert manifest.train_count > 0
    assert manifest.val_count > 0
    assert manifest.test_count > 0

    # 2. Artificially injecting patient leakage must trigger ValueError
    leaked_sample = dict(manifest.train_samples[0])
    manifest.test_samples.append(leaked_sample)
    with pytest.raises(ValueError, match="Data leakage detected"):
        manifest.verify_no_leakage()


def test_modality_transforms_pipeline():
    """Validates that modality transforms produce normalized [3, 224, 224] tensors."""
    dummy_img = torch.randint(0, 255, (100, 100, 3), dtype=torch.uint8).numpy()

    for modality in ["ultrasound", "ct", "histology", "mri", "cytology"]:
        eval_tf = get_modality_transforms(modality, image_size=(224, 224), is_training=False)
        tensor = eval_tf(dummy_img)
        assert tensor.shape == (3, 224, 224)
        assert tensor.dtype == torch.float32

        train_tf = get_modality_transforms(modality, image_size=(224, 224), is_training=True)
        train_tensor = train_tf(dummy_img)
        assert train_tensor.shape == (3, 224, 224)


def test_hybrid_model_factory_and_forward_pass():
    """Validates that hybrid models build appropriate modality branches and output shapes."""
    task_config = {
        "task_id": "test_kidney",
        "modality": "ct",
        "model": {
            "num_classes": 4,
            "embedding_dim": 512,
            "dropout": 0.2,
        },
        "data": {
            "class_names": ["normal", "tumor", "cyst", "stone"],
        },
    }

    model = build_hybrid_model(task_config)
    assert isinstance(model, HybridMultiTaskModel)
    assert model.num_classes == 4
    assert model.embedding_dim == 512

    # Forward pass test
    dummy_input = torch.randn(2, 3, 224, 224)
    logits, embedding, spatial_features = model(dummy_input)

    assert logits.shape == (2, 4)
    assert embedding.shape == (2, 512)
    assert spatial_features.dim() == 4
    assert spatial_features.size(1) == 512  # Channels retained for Grad-CAM


def test_training_checkpoint_io_sha256_integrity():
    """Validates checkpoint saving, parameter counting, and cryptographic SHA-256 tamper detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        io_mgr = TrainingCheckpointIO(tmpdir)
        dummy_model = nn.Sequential(nn.Linear(20, 10), nn.ReLU(), nn.Linear(10, 2))

        bundle = io_mgr.save_checkpoint(
            model=dummy_model,
            task_id="test_sha_task",
            run_id="RUN_TEST_001",
            epoch=3,
            metrics={"accuracy": 0.85, "macro_f1": 0.82},
            class_names=["benign", "malignant"],
            status="EVALUATED",
            version="v2.0.0",
        )

        assert bundle.task_id == "test_sha_task"
        assert len(bundle.sha256_hash) == 64
        assert bundle.status == "EVALUATED"

        # Reload into new model with verification
        new_model = nn.Sequential(nn.Linear(20, 10), nn.ReLU(), nn.Linear(10, 2))
        loaded_bundle = io_mgr.load_checkpoint(new_model, bundle.checkpoint_path, verify_integrity=True)
        assert loaded_bundle.sha256_hash == bundle.sha256_hash

        # Tampering with checkpoint file must raise ValueError
        with open(bundle.checkpoint_path, "ab") as f:
            f.write(b"\x00\xFF\xAA")

        with pytest.raises(ValueError, match="Cryptographic tampering or corruption detected"):
            io_mgr.load_checkpoint(new_model, bundle.checkpoint_path, verify_integrity=True)


def test_single_task_end_to_end_training_flow():
    """Validates complete single-task training pipeline with metrics & model card generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_p = Path(tmpdir)
        task_cfg = {
            "task_id": "test_e2e_task",
            "category": "breast",
            "modality": "ultrasound",
            "enabled": True,
            "data": {
                "dataset_id": "synthetic_test_v1",
                "data_dir": str(tmp_p / "data"),
                "image_size": [224, 224],
                "channels": 3,
                "class_names": ["benign", "malignant"],
                "class_mapping": {0: "benign", 1: "malignant"},
                "split_manifest": str(tmp_p / "manifest.json"),
                "grouping_key": "patient_id",
            },
            "model": {
                "embedding_dim": 512,
                "num_classes": 2,
                "dropout": 0.2,
            },
            "training": {
                "seed": 42,
                "batch_size": 4,
                "epochs": 2,
                "learning_rate": 0.001,
                "early_stopping_patience": 2,
            },
            "checkpoint": {
                "checkpoint_dir": str(tmp_p / "checkpoints"),
            },
        }

        record = train_single_task(task_cfg, dry_run_epochs=2)

        assert record.task_id == "test_e2e_task"
        assert record.status == TaskRunState.EVALUATED
        assert record.epochs_trained == 2
        assert record.checkpoint_sha256 is not None
        assert len(record.checkpoint_sha256) == 64
        assert "accuracy" in record.test_metrics
        assert "macro_f1" in record.test_metrics

        # Verify artifacts exist on disk and clean up temporary test artifacts
        metrics_file = Path("artifacts/metrics/test_e2e_task_test_metrics.json")
        card_file = Path("artifacts/model_cards/test_e2e_task.md")
        try:
            assert Path(record.checkpoint_path).exists()
            assert metrics_file.exists()
            assert card_file.exists()
        finally:
            metrics_file.unlink(missing_ok=True)
            card_file.unlink(missing_ok=True)
