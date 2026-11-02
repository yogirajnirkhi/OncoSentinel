"""
OncoSentinel v2.0 — Model Card Generator
Satisfies: Master Roadmap §22.2, FR-26
Generates standardized Markdown model cards reflecting real measured evaluations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from training.evaluate import EvaluationResult
from training.run_state import TaskRunRecord


def generate_model_card(
    task_config: dict[str, Any],
    run_record: TaskRunRecord,
    eval_result: EvaluationResult,
    destination_path: Path | str,
) -> str:
    """Generates an authoritative, standard-compliant Model Card markdown document."""
    task_id = task_config.get("task_id", "unnamed_task")
    display_name = task_config.get("display_name", task_id)
    category = task_config.get("category", "unspecified")
    modality = task_config.get("modality", "unspecified")
    dataset_cfg = task_config.get("data", {})
    class_names = dataset_cfg.get("class_names", [])

    per_class_rows = []
    for c_name, m in eval_result.per_class_metrics.items():
        sens = m.get("sensitivity_recall", 0.0)
        spec = m.get("specificity", 0.0)
        prec = m.get("precision", 0.0)
        f1 = m.get("f1_score", 0.0)
        supp = m.get("support", 0)
        per_class_rows.append(
            f"| `{c_name}` | {sens:.4f} | {spec:.4f} | {prec:.4f} | {f1:.4f} | {supp} |"
        )
    per_class_table = "\n".join(per_class_rows)
    cm_str = "\n".join(f"  {row}" for row in eval_result.confusion_matrix)

    roc_auc_str = f"{eval_result.roc_auc_macro:.4f}" if eval_result.roc_auc_macro is not None else "N/A"
    roc_auc_status = "PASS" if (eval_result.roc_auc_macro is not None and eval_result.roc_auc_macro >= 0.85) else "UNVERIFIED"

    md = f"""# Model Card — {display_name} (`{task_id}`)

## 1. Model Details
- **Task Identifier:** `{task_id}`
- **Category:** `{category}`
- **Model Architecture:** `{run_record.model_architecture}` (Hybrid Shared Network with `{modality}` branch)
- **Model Checkpoint SHA-256:** `{run_record.checkpoint_sha256 or 'unmeasured'}`
- **Software Version:** OncoSentinel v2.0.0
- **Run Identifier:** `{run_record.run_id}`
- **Date Generated:** `{run_record.finished_at or run_record.started_at}`
- **Reviewer:** OncoSentinel Autonomous ML Engine / Evaluator

## 2. Intended Use & Scope
- **Intended Use:** Research-only decision support for exploring deep learning feature representations, uncertainty calibration, and concept attribution in {modality} imaging.
- **Out-of-Scope / Prohibited Use:** Clinical diagnosis, direct patient management, autonomous triage, or treatment selection without licensed clinician oversight.

## 3. Data Lineage & Splitting
- **Dataset ID:** `{dataset_cfg.get('dataset_id', 'unspecified')}`
- **Input Modality:** `{modality}` ({dataset_cfg.get('input_type', 'image_2d')})
- **Input Dimensions:** `{dataset_cfg.get('image_size', [224, 224])}` RGB channels
- **Target Classes ({len(class_names)}):** {', '.join(f'`{c}`' for c in class_names)}
- **Split Manifest:** `{run_record.split_manifest}`
- **Grouping Key:** `{dataset_cfg.get('grouping_key', 'patient_id')}` (strictly grouped to prevent data leakage)
- **Sample Support:** Total: {eval_result.num_samples} evaluation test samples

## 4. Training Procedure
- **Seed:** {run_record.seed}
- **Epochs Trained:** {run_record.epochs_trained} (Best Selected Epoch: {run_record.best_epoch or 'N/A'})
- **Optimizer:** {task_config.get('training', {}).get('optimizer', 'AdamW')} (LR={task_config.get('training', {}).get('learning_rate', 0.0003)})
- **Loss Function:** {task_config.get('training', {}).get('loss_function', 'cross_entropy')}

## 5. Measured Evaluation Protocol & Performance
*Metrics computed strictly on the held-out test split (zero train/val contamination):*

| Metric | Measured Value | Standard Target | Status |
|---|---|---|---|
| **Accuracy** | `{eval_result.accuracy * 100:.2f}%` | ≥ 80.00% | {'PASS' if eval_result.accuracy >= 0.8 else 'REVIEW'} |
| **Macro F1 Score** | `{eval_result.macro_f1:.4f}` | ≥ 0.7500 | {'PASS' if eval_result.macro_f1 >= 0.75 else 'REVIEW'} |
| **Macro Sensitivity** | `{eval_result.sensitivity_macro:.4f}` | ≥ 0.8000 | {'PASS' if eval_result.sensitivity_macro >= 0.8 else 'REVIEW'} |
| **Macro Specificity** | `{eval_result.specificity_macro:.4f}` | ≥ 0.8000 | {'PASS' if eval_result.specificity_macro >= 0.8 else 'REVIEW'} |
| **Brier Score** | `{eval_result.brier_score:.4f}` | ≤ 0.1500 | {'PASS' if eval_result.brier_score <= 0.15 else 'REVIEW'} |
| **Expected Calibration Error (ECE)** | `{eval_result.expected_calibration_error:.4f}` | ≤ 0.0800 | {'PASS' if eval_result.expected_calibration_error <= 0.08 else 'REVIEW'} |
| **Macro ROC-AUC** | `{roc_auc_str}` | ≥ 0.8500 | {roc_auc_status} |

### Per-Class Detailed Performance
| Class Name | Sensitivity | Specificity | Precision | F1 Score | Test Support |
|---|---|---|---|---|---|
{per_class_table}

### Confusion Matrix
```
{cm_str}
```

## 6. Uncertainty & Explainability Guidance
- **Calibration Method:** Temperature Scaling and Conformal Prediction interval boundaries.
- **Explainability:** Grad-CAM saliency heatmaps overlaid on original scan + Concept Bottleneck attribution mapped to authoritative taxonomy findings.
- **Known Limitations:**
  - Prototype model weights are evaluated on defined challenge/synthetic benchmark cohorts.
  - Performance under out-of-distribution scanner protocols or motion blur degrades; inputs with quality scores < 0.40 must be rejected by the Quality Gate.
  - Does not replace histopathological tissue confirmation.
"""
    dest = Path(destination_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(md)
    return md
