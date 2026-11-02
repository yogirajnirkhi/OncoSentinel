"""
OncoSentinel v2.0 — Multi-Metric Evaluation & Calibration Analysis
Satisfies: Master Roadmap §10.1
Calculates accuracy, macro F1, sensitivity, specificity, confusion matrix, Brier score, and ECE.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader


@dataclass
class EvaluationResult:
    task_id: str
    split_name: str
    num_samples: int
    accuracy: float
    macro_f1: float
    sensitivity_macro: float
    specificity_macro: float
    brier_score: float
    expected_calibration_error: float
    roc_auc_macro: Optional[float]
    per_class_metrics: dict[str, dict[str, float]]
    confusion_matrix: list[list[int]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, destination: Path | str) -> None:
        p = Path(destination)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)


def compute_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    """Computes Expected Calibration Error (ECE) across confidence bins."""
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = (predictions == labels).astype(float)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]

        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        prop_in_bin = np.mean(in_bin)

        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(accuracies[in_bin])
            avg_confidence_in_bin = np.mean(confidences[in_bin])
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin

    return float(ece)


def evaluate_model(
    model: nn.Module,
    dataloader: DataLoader,
    class_names: list[str],
    task_id: str = "unnamed_task",
    split_name: str = "test",
    device: Optional[torch.device | str] = None,
) -> EvaluationResult:
    """Runs evaluation over a dataloader and calculates comprehensive metrics."""
    dev = device or (torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    model.eval()

    all_preds: list[int] = []
    all_labels: list[int] = []
    all_probs: list[np.ndarray] = []

    with torch.no_grad():
        for batch in dataloader:
            inputs, labels, _ = batch
            inputs = inputs.to(dev)
            logits, _, _ = model(inputs)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()

            preds = np.argmax(probs, axis=1).tolist()
            all_preds.extend(preds)
            all_labels.extend(labels.numpy().tolist())
            all_probs.append(probs)

    y_true = np.array(all_labels)
    y_pred = np.array(all_preds)
    probs_matrix = np.vstack(all_probs)
    num_classes = len(class_names)

    # 1. Accuracy
    accuracy = float(np.mean(y_true == y_pred)) if len(y_true) > 0 else 0.0

    # 2. Confusion Matrix
    cm = [[0 for _ in range(num_classes)] for _ in range(num_classes)]
    for t, p in zip(y_true, y_pred):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            cm[t][p] += 1

    # 3. Per-class sensitivity, specificity, precision, F1
    per_class: dict[str, dict[str, float]] = {}
    sensitivities: list[float] = []
    specificities: list[float] = []
    f1_scores: list[float] = []

    for c_idx, c_name in enumerate(class_names):
        tp = cm[c_idx][c_idx]
        fn = sum(cm[c_idx][j] for j in range(num_classes) if j != c_idx)
        fp = sum(cm[i][c_idx] for i in range(num_classes) if i != c_idx)
        tn = sum(cm[i][j] for i in range(num_classes) for j in range(num_classes) if i != c_idx and j != c_idx)

        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = (2 * precision * sensitivity) / (precision + sensitivity) if (precision + sensitivity) > 0 else 0.0

        sensitivities.append(sensitivity)
        specificities.append(specificity)
        f1_scores.append(f1)

        per_class[c_name] = {
            "sensitivity_recall": float(sensitivity),
            "specificity": float(specificity),
            "precision": float(precision),
            "f1_score": float(f1),
            "support": int(tp + fn),
        }

    macro_f1 = float(np.mean(f1_scores)) if f1_scores else 0.0
    macro_sens = float(np.mean(sensitivities)) if sensitivities else 0.0
    macro_spec = float(np.mean(specificities)) if specificities else 0.0

    # 4. Multi-class Brier score: mean squared difference from one-hot ground truth
    one_hot = np.zeros_like(probs_matrix)
    for idx, label in enumerate(y_true):
        if 0 <= label < num_classes:
            one_hot[idx, label] = 1.0
    brier = float(np.mean(np.sum((probs_matrix - one_hot) ** 2, axis=1)))

    # 5. Expected Calibration Error (ECE)
    ece = compute_ece(probs_matrix, y_true, n_bins=10)

    # 6. ROC-AUC (calculated if multi-class / binary conditions valid)
    roc_auc: Optional[float] = None
    try:
        from sklearn.metrics import roc_auc_score
        if num_classes == 2 and len(np.unique(y_true)) == 2:
            roc_auc = float(roc_auc_score(y_true, probs_matrix[:, 1]))
        elif len(np.unique(y_true)) == num_classes:
            roc_auc = float(roc_auc_score(y_true, probs_matrix, multi_class="ovr", average="macro"))
    except Exception:
        roc_auc = None

    return EvaluationResult(
        task_id=task_id,
        split_name=split_name,
        num_samples=len(y_true),
        accuracy=accuracy,
        macro_f1=macro_f1,
        sensitivity_macro=macro_sens,
        specificity_macro=macro_spec,
        brier_score=brier,
        expected_calibration_error=ece,
        roc_auc_macro=roc_auc,
        per_class_metrics=per_class,
        confusion_matrix=cm,
    )
