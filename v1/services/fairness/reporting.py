"""
OncoSentinel v2.0 — Fairness Reporting Generator
Satisfies: FR-19 (produce machine-readable and human-readable fairness reports)
"""
from __future__ import annotations

import json
from dataclasses import asdict

from services.fairness.evaluator import FairnessEvaluationSummary


class FairnessReportGenerator:
    """Generates human-readable Markdown and machine-readable JSON reports."""

    @staticmethod
    def generate_markdown(summary: FairnessEvaluationSummary) -> str:
        lines = [
            f"# OncoSentinel Fairness & Subgroup Evaluation Report",
            f"**Model Version:** `{summary.model_version}` | **Category:** `{summary.category.title()}` | **Status:** **{summary.status}**",
            f"**Total Evaluation Cohort:** {summary.overall_samples:,} cases",
            "",
            "## 1. Disparity Summary",
            f"- **Max Sensitivity Disparity:** {summary.max_sensitivity_disparity:.2%} (Limit: ≤ 10%)",
            f"- **Max Calibration (ECE) Disparity:** {summary.max_ece_disparity:.2%} (Limit: ≤ 6%)",
            f"- **Max False Negative Rate Disparity:** {summary.max_fnr_disparity:.2%} (Limit: ≤ 8%)",
            f"- **Fairness Promotion Gate:** {'✅ PASSED' if summary.gate_passed else '❌ FAILED'}",
            "",
            "## 2. Subgroup Performance Matrix",
            "| Subgroup | Stratum | Samples | Sens | Spec | F1 | AUC | ECE | FNR | Abstain |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]

        for s in summary.subgroup_metrics:
            warn = " ⚠️" if s.sample_size_warning else ""
            lines.append(
                f"| {s.subgroup_name} | {s.stratum_type} | {s.n_samples}{warn} | "
                f"{s.sensitivity:.2f} | {s.specificity:.2f} | {s.f1:.2f} | {s.auc:.2f} | "
                f"{s.ece:.3f} | {s.fnr:.2f} | {s.abstention_rate:.2%} |"
            )

        lines.extend([
            "",
            "## 3. Router Disparity Analysis",
            f"- Quality Rejection Disparity: {summary.router_rejection_analysis.get('router_quality_rejection_disparity', 0):.2%}",
            f"- Disproportionate Exclusion Detected: {'Yes' if summary.router_rejection_analysis.get('disproportionate_exclusion_flag') else 'No'}",
            "",
            "---",
            "*Report generated according to OncoSentinel v2.0 Research Evaluation Protocols.*",
        ])

        return "\n".join(lines)

    @staticmethod
    def generate_json(summary: FairnessEvaluationSummary) -> str:
        return json.dumps(asdict(summary), indent=2)
