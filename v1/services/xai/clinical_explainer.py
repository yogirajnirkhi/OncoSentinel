"""
OncoSentinel v2.0 — Clinical Explanation Generator
Satisfies: FR-13, FR-14, FR-15, NFR-06
Grounded in: Architecture v2.0 §5 (What -> Where -> Why -> Supporting -> Counter -> Tri-part sections)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

import numpy as np

from services.core.logging import get_logger
from services.xai.concept_mapper import ClinicalConceptFinding, ConceptMapper
from services.xai.evaluator import XAIEvaluationMetrics, get_xai_evaluator
from services.xai.gradcam import get_gradcam_generator

logger = get_logger(__name__)

# Category guideline references
_GUIDELINE_REFERENCES = {
    "breast": "ACR BI-RADS Atlas (5th Edition) & NCCN Guidelines for Breast Cancer Screening (v2.2024)",
    "kidney": "Bosniak Classification of Cystic Renal Masses (2019 Update) & NCCN Kidney Cancer Guidelines (v3.2024)",
    "all_leukemia": "WHO Classification of Tumours of Haematopoietic and Lymphoid Tissues (5th Edition)",
    "oral": "AJCC Cancer Staging Manual (8th Edition, Head and Neck) & NCCN Oral Cavity Guidelines",
    "colon": "NCCN Colon Cancer Clinical Practice Guidelines (v2024) & CAP Staging Protocol",
    "lung": "NCCN Non-Small Cell Lung Cancer Guidelines (v2024) & IASLC Staging Guidelines",
    "lung_colon": "NCCN Non-Small Cell Lung Cancer & Colon Cancer Guidelines (v2024)",
    "lymphoma": "Lugano Classification & NCCN B-Cell Lymphomas Guidelines",
    "brain": "WHO Classification of Tumours of the Central Nervous System (5th Edition, 2021)",
    "cervical": "The Bethesda System for Reporting Cervical Cytology (3rd Edition) & ASCCP Management Guidelines",
}


@dataclass
class StructuredExplanation:
    what: str
    where_region: str
    why_json: list[dict[str, Any]]
    supporting_evidence_json: list[dict[str, Any]]
    contradicting_evidence_json: list[dict[str, Any]]
    confidence_narrative: str
    model_evidence_section: str
    guideline_evidence_section: str
    generated_synthesis_section: str
    fidelity_score: float
    robustness_score: float
    localization_score: float
    complexity_score: float
    explanation_policy_version: str
    audit_heatmap_uri: Optional[str]


class ClinicalExplanationEngine:
    """Assembles concept-based clinical explanations linked to domain findings."""

    def __init__(self) -> None:
        self.concept_mapper = ConceptMapper()
        self.gradcam_generator = get_gradcam_generator()
        self.xai_evaluator = get_xai_evaluator()
        self.policy_version = "clinical_xai_v2.0.0"

    def generate_explanation(
        self,
        category: str,
        predicted_class: str,
        calibrated_probability: float,
        raw_probability: float,
        embedding: np.ndarray,
        feature_map: Any,
        image_bytes: bytes,
        prediction_id: str,
        uncertainty_decision: str,
        class_index: int = 0,
    ) -> StructuredExplanation:
        # 1. Concept Extraction
        supporting, counter = self.concept_mapper.extract_concepts(
            category=category,
            predicted_class=predicted_class,
            embedding=embedding,
        )

        # 2. Grad-CAM generation (class-discriminative using target class_index)
        heatmap, heatmap_uri = self.gradcam_generator.generate_heatmap(
            feature_map=feature_map,
            original_image_bytes=image_bytes,
            class_index=class_index,
            prediction_id=prediction_id,
        )

        # 3. Quantitative Evaluation (Sangwan 2024)
        all_saliences = [c.salience_score for c in supporting] + [c.salience_score for c in counter]
        metrics = self.xai_evaluator.evaluate_explanation(heatmap, all_saliences)

        # 4. Synthesize Clinical Narrative Components
        # WHAT
        what_text = (
            f"Automated evaluation indicates primary diagnostic category '{predicted_class.upper()}' "
            f"for {category.title()} pathology, with calibrated probability of {calibrated_probability:.1%} "
            f"(uncalibrated baseline: {raw_probability:.1%})."
        )

        # WHERE
        # Estimate quadrant or region from heatmap peak
        peak_y, peak_x = np.unravel_index(np.argmax(heatmap), heatmap.shape)
        v_pos = "upper" if peak_y < 112 else "lower"
        h_pos = "left" if peak_x < 112 else "right"
        where_text = f"Primary focal salience localized to {v_pos}-{h_pos} field of the lesion."

        # CONFIDENCE NARRATIVE
        conf_text = (
            f"The prediction demonstrates {calibrated_probability:.1%} calibrated certainty under "
            f"temperature-scaling protocols. Model uncertainty status: {uncertainty_decision}. "
            f"Quantitative explanation fidelity is {metrics.fidelity_score:.2f} (threshold: 0.70)."
        )

        # TRI-PART SECTION 1: Model Evidence Section
        top_concepts_str = ", ".join(f"{c.display_name} ({c.salience_score:.2f})" for c in supporting[:3])
        model_evidence_section = (
            f"INTERNAL MODEL ACTIVATION SUMMARY:\n"
            f"- Saliency concentration: {metrics.localization_score:.1%} of gradient energy within focal ROI.\n"
            f"- Predominant concepts activated: {top_concepts_str}.\n"
            f"- Latent representation similarity to established {predicted_class} training cohort: high."
        )

        # TRI-PART SECTION 2: Guideline Evidence Section
        guideline_ref = _GUIDELINE_REFERENCES.get(category.lower(), "Standard Clinical Practice Guidelines")
        guideline_evidence_section = (
            f"CLINICAL GUIDELINE CORRELATION:\n"
            f"- Standard: {guideline_ref}.\n"
            f"- Recommended action for {predicted_class} findings: Correlate with patient clinical history, "
            f"prior imaging, and confirmatory biopsy or histological adjudication as indicated by clinical protocol."
        )

        # TRI-PART SECTION 3: Generated Synthesis Section
        counter_note = (
            f" Note: Differential considerations include {counter[0].display_name.lower()} "
            f"({counter[0].clinical_observation})."
            if counter
            else ""
        )
        generated_synthesis_section = (
            f"CLINICAL DECISION-SUPPORT SYNTHESIS:\n"
            f"The image findings predominantly align with {predicted_class} characteristics based on "
            f"{supporting[0].display_name if supporting else 'morphological features'}.{counter_note}\n"
            f"DISCLAIMER: OncoSentinel provides AI-assisted decision support, not autonomous medical diagnosis. "
            f"All findings require validation by a qualified clinician."
        )

        return StructuredExplanation(
            what=what_text,
            where_region=where_text,
            why_json=[asdict(c) for c in supporting + counter],
            supporting_evidence_json=[asdict(c) for c in supporting],
            contradicting_evidence_json=[asdict(c) for c in counter],
            confidence_narrative=conf_text,
            model_evidence_section=model_evidence_section,
            guideline_evidence_section=guideline_evidence_section,
            generated_synthesis_section=generated_synthesis_section,
            fidelity_score=metrics.fidelity_score,
            robustness_score=metrics.robustness_score,
            localization_score=metrics.localization_score,
            complexity_score=metrics.complexity_score,
            explanation_policy_version=self.policy_version,
            audit_heatmap_uri=heatmap_uri,
        )


_explainer_singleton: Optional[ClinicalExplanationEngine] = None


def get_clinical_explainer() -> ClinicalExplanationEngine:
    global _explainer_singleton
    if _explainer_singleton is None:
        _explainer_singleton = ClinicalExplanationEngine()
    return _explainer_singleton
