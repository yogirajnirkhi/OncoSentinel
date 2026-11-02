"""
OncoSentinel v2.0 — Task Run State and Experiment Record Definitions
Satisfies: Master Roadmap §4.4, §8.4, §22.1
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class TaskRunState(str, Enum):
    """Standardized lifecycle states across the OncoSentinel platform."""
    NOT_CONFIGURED = "NOT_CONFIGURED"
    READY = "READY"
    TRAINING = "TRAINING"
    TRAINED = "TRAINED"
    EVALUATED = "EVALUATED"
    RESEARCH_DEMO_READY = "RESEARCH_DEMO_READY"

    # Explicit blocked & non-success states
    BLOCKED_DATA = "BLOCKED_DATA"
    BLOCKED_ENVIRONMENT = "BLOCKED_ENVIRONMENT"
    FAILED_TRAINING = "FAILED_TRAINING"
    FAILED_EVALUATION = "FAILED_EVALUATION"
    CHECKPOINT_INVALID = "CHECKPOINT_INVALID"
    NEEDS_REVIEW = "NEEDS_REVIEW"


@dataclass
class TaskRunRecord:
    """Immutable experiment ledger entry representing a specific training/evaluation execution."""
    run_id: str
    task_id: str
    category: str
    modality: str
    status: TaskRunState
    dataset_id: str
    split_manifest: str
    config_snapshot_path: str
    seed: int
    model_architecture: str
    checkpoint_path: Optional[str] = None
    checkpoint_sha256: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    finished_at: Optional[str] = None
    epochs_trained: int = 0
    best_epoch: Optional[int] = None
    validation_metrics: Optional[dict[str, Any]] = None
    test_metrics: Optional[dict[str, Any]] = None
    notes: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    environment_info: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    def save_json(self, destination: Path | str) -> None:
        p = Path(destination)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_json(cls, source: Path | str) -> TaskRunRecord:
        with open(source, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["status"] = TaskRunState(data["status"])
        return cls(**data)


@dataclass
class QueueSummary:
    """Summary record for a multi-task sequential training run."""
    queue_id: str
    started_at: str
    finished_at: Optional[str] = None
    total_tasks: int = 8
    completed_tasks: int = 0
    failed_tasks: int = 0
    blocked_tasks: int = 0
    skipped_tasks: int = 0
    task_states: dict[str, str] = field(default_factory=dict)
    task_records: dict[str, str] = field(default_factory=dict)  # task_id -> record json path

    def print_summary_table(self) -> str:
        lines = [
            "=" * 72,
            f"OncoSentinel Sequential Training Queue Summary: {self.queue_id}",
            f"Started: {self.started_at} | Finished: {self.finished_at or 'In Progress'}",
            "-" * 72,
            f"{'Slot':<6} {'Task ID':<26} {'Status':<22} {'Record Artifact'}",
            "-" * 72,
        ]
        for slot_idx, (t_id, state) in enumerate(self.task_states.items(), 1):
            rec = self.task_records.get(t_id, "-")
            lines.append(f"{slot_idx:02d}     {t_id:<26} {state:<22} {rec}")
        lines.append("=" * 72)
        return "\n".join(lines)
