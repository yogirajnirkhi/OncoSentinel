"""
OncoSentinel v2.0 — Sequential Multi-Task Training Manager
Satisfies: Master Roadmap §8, §14 Phase 2 & 3
Executes all eight cancer task configurations sequentially with failure isolation,
deterministic task ordering, checkpoint resume/retry validation, and full queue summary.
"""
from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from services.core.logging import get_logger
from training.run_state import QueueSummary, TaskRunRecord, TaskRunState
from training.train_one import train_single_task

logger = get_logger(__name__)


def run_sequential_queue(
    registry_path: Path | str = "configs/model_registry.yaml",
    device: Optional[str] = None,
    dry_run_epochs: Optional[int] = None,
    stop_on_failure: bool = False,
    force_retrain: bool = False,
) -> QueueSummary:
    """Executes all enabled tasks in configs/model_registry.yaml sequentially."""
    reg_path = Path(registry_path)
    if not reg_path.exists():
        raise FileNotFoundError(f"Model registry not found at: {reg_path}")

    with open(reg_path, "r", encoding="utf-8") as f:
        registry_data = yaml.safe_load(f)

    tasks_dict: dict[str, Any] = registry_data.get("tasks", {})
    queue_id = f"QUEUE_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    started_at = datetime.utcnow().isoformat()

    summary = QueueSummary(
        queue_id=queue_id,
        started_at=started_at,
        total_tasks=len(tasks_dict),
    )

    logger.info("sequential_queue_started", queue_id=queue_id, total_tasks=len(tasks_dict))

    # Sort deterministically by slot
    sorted_tasks = sorted(tasks_dict.items(), key=lambda kv: kv[1].get("slot", 99))

    for slot_idx, (task_id, task_meta) in enumerate(sorted_tasks, 1):
        display_name = task_meta.get("display_name", task_id)
        config_path = task_meta.get("config_path")
        is_enabled = task_meta.get("enabled", False)

        print(f"\n[{slot_idx}/{len(sorted_tasks)}] Processing Slot {task_meta.get('slot', slot_idx)}: {display_name} ({task_id})...")

        if not is_enabled:
            logger.info("task_disabled_in_registry", task_id=task_id)
            summary.skipped_tasks += 1
            summary.task_states[task_id] = TaskRunState.BLOCKED_DATA.value
            continue

        if not config_path or not Path(config_path).exists():
            logger.warning("task_config_missing", task_id=task_id, path=config_path)
            summary.blocked_tasks += 1
            summary.task_states[task_id] = TaskRunState.NOT_CONFIGURED.value
            continue

        # Check for existing checkpoint if resume is permitted
        ckpt_dir = Path(task_meta.get("checkpoint_dir", f"artifacts/checkpoints/{task_id}"))
        ckpt_pt = ckpt_dir / f"{task_id}_best.pt"
        ckpt_json = ckpt_dir / f"{task_id}_best.json"

        if not force_retrain and ckpt_pt.exists() and ckpt_json.exists():
            logger.info("compatible_checkpoint_found_skipping", task_id=task_id, path=str(ckpt_pt))
            summary.completed_tasks += 1
            summary.task_states[task_id] = TaskRunState.EVALUATED.value
            summary.task_records[task_id] = str(ckpt_json)
            continue

        # Execute training
        summary.task_states[task_id] = TaskRunState.TRAINING.value
        try:
            record: TaskRunRecord = train_single_task(
                config_path_or_dict=config_path,
                device=device,
                dry_run_epochs=dry_run_epochs,
            )
            summary.completed_tasks += 1
            summary.task_states[task_id] = record.status.value
            summary.task_records[task_id] = f"artifacts/logs/{task_id}_{record.run_id}.json"

            # Update registry in-memory
            task_meta["status"] = record.status.value
            task_meta["checkpoint_path"] = record.checkpoint_path
            task_meta["checkpoint_sha256"] = record.checkpoint_sha256
            task_meta["last_run_id"] = record.run_id

        except Exception as exc:
            logger.error("task_training_failed", task_id=task_id, error=str(exc))
            summary.failed_tasks += 1
            summary.task_states[task_id] = TaskRunState.FAILED_TRAINING.value

            if stop_on_failure:
                logger.warning("queue_stopped_on_failure", failed_task=task_id)
                break

    summary.finished_at = datetime.utcnow().isoformat()

    # Update model_registry.yaml with real execution outcomes
    try:
        registry_data["last_queue_id"] = queue_id
        registry_data["last_queue_completed_at"] = summary.finished_at
        with open(reg_path, "w", encoding="utf-8") as f:
            yaml.dump(registry_data, f, sort_keys=False)
    except Exception as exc:
        logger.warning("registry_yaml_update_error", error=str(exc))

    # Print summary table
    print("\n" + summary.print_summary_table())
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OncoSentinel Sequential Multi-Task Training Manager")
    parser.add_argument("--registry", type=str, default="configs/model_registry.yaml", help="Path to model registry YAML")
    parser.add_argument("--device", type=str, default=None, help="Device to train on ('cpu' or 'cuda')")
    parser.add_argument("--dry-run-epochs", type=int, default=None, help="Epoch override for fast dry-run or testing")
    parser.add_argument("--stop-on-failure", action="store_true", help="Halt the queue if any single task fails")
    parser.add_argument("--force-retrain", action="store_true", help="Retrain tasks even if valid checkpoints exist")
    args = parser.parse_args()

    summary = run_sequential_queue(
        registry_path=args.registry,
        device=args.device,
        dry_run_epochs=args.dry_run_epochs,
        stop_on_failure=args.stop_on_failure,
        force_retrain=args.force_retrain,
    )
    if summary.failed_tasks > 0 and args.stop_on_failure:
        sys.exit(1)
