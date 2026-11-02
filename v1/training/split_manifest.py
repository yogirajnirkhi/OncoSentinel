"""
OncoSentinel v2.0 — Split Manifest Generator and Leakage Verification
Satisfies: Master Roadmap §9.1, §18 Priority 1
Prevents patient-level and study-level data leakage across train, val, and test partitions.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class SplitItem:
    sample_id: str
    relative_path: str
    class_label: int
    class_name: str
    grouping_id: str  # patient_id, study_id, or slide_id to prevent leakage
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SplitManifest:
    task_id: str
    dataset_id: str
    created_at: str
    grouping_key: str
    total_samples: int
    train_count: int
    val_count: int
    test_count: int
    class_distribution: dict[str, dict[str, int]]
    train_samples: list[dict[str, Any]]
    val_samples: list[dict[str, Any]]
    test_samples: list[dict[str, Any]]

    def save(self, destination: Path | str) -> None:
        p = Path(destination)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, source: Path | str) -> SplitManifest:
        with open(source, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def verify_no_leakage(self) -> bool:
        """Verifies that no patient/grouping ID appears in more than one partition."""
        train_groups = {s["grouping_id"] for s in self.train_samples}
        val_groups = {s["grouping_id"] for s in self.val_samples}
        test_groups = {s["grouping_id"] for s in self.test_samples}

        train_val_overlap = train_groups.intersection(val_groups)
        train_test_overlap = train_groups.intersection(test_groups)
        val_test_overlap = val_groups.intersection(test_groups)

        if train_val_overlap or train_test_overlap or val_test_overlap:
            raise ValueError(
                f"Data leakage detected in manifest for {self.task_id}!\n"
                f"Train-Val overlap: {train_val_overlap}\n"
                f"Train-Test overlap: {train_test_overlap}\n"
                f"Val-Test overlap: {val_test_overlap}"
            )
        return True


def create_leakage_resistant_split(
    items: list[SplitItem],
    task_id: str,
    dataset_id: str,
    grouping_key: str = "patient_id",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> SplitManifest:
    """Partitions dataset items by grouping ID (patient/study) to guarantee zero leakage."""
    rng = random.Random(seed)

    # Group items by patient/source entity
    groups: dict[str, list[SplitItem]] = {}
    for item in items:
        groups.setdefault(item.grouping_id, []).append(item)

    group_keys = sorted(groups.keys())
    rng.shuffle(group_keys)

    n_groups = len(group_keys)
    n_train = max(1, int(n_groups * train_ratio))
    n_val = max(1, int(n_groups * val_ratio))

    train_group_keys = set(group_keys[:n_train])
    val_group_keys = set(group_keys[n_train : n_train + n_val])
    test_group_keys = set(group_keys[n_train + n_val :])
    if not test_group_keys:
        # Fallback for very small datasets
        test_group_keys = {group_keys[-1]}
        val_group_keys.discard(group_keys[-1])

    train_samples = [asdict(item) for k in train_group_keys for item in groups[k]]
    val_samples = [asdict(item) for k in val_group_keys for item in groups[k]]
    test_samples = [asdict(item) for k in test_group_keys for item in groups[k]]

    # Compute class distribution across splits
    def count_classes(samples: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in samples:
            counts[s["class_name"]] = counts.get(s["class_name"], 0) + 1
        return counts

    distribution = {
        "train": count_classes(train_samples),
        "val": count_classes(val_samples),
        "test": count_classes(test_samples),
    }

    manifest = SplitManifest(
        task_id=task_id,
        dataset_id=dataset_id,
        created_at=datetime.utcnow().isoformat(),
        grouping_key=grouping_key,
        total_samples=len(items),
        train_count=len(train_samples),
        val_count=len(val_samples),
        test_count=len(test_samples),
        class_distribution=distribution,
        train_samples=train_samples,
        val_samples=val_samples,
        test_samples=test_samples,
    )

    manifest.verify_no_leakage()
    return manifest
