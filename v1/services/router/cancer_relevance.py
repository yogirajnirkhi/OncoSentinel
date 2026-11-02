"""
OncoSentinel v2.0 — Cancer Relevance Gate
Satisfies: FR-03, FR-04 (cancer relevance score >= 0.55 gate)
Grounded in: Architecture §12 (routing before execution; terminal safety state for irrelevant inputs)
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from services.core.config_loader import get_thresholds
from services.core.logging import get_logger

logger = get_logger(__name__)

# Category-specific ontological term banks
_CATEGORY_TERMS = {
    "breast": [
        "breast", "mammogram", "mammography", "ultrasound", "bi-rads", "ductal",
        "lobular", "her2", "er/pr", "brca", "microcalcification", "microcalcifications",
        "calcification", "calcifications", "fibroadenoma", "mastectomy", "lumpectomy",
        "axillary", "breast lesion", "breakhis"
    ],
    "kidney": [
        "kidney", "renal", "rcc", "clear cell", "nephrectomy", "cortical", "medullary",
        "renal cell carcinoma", "ct kidney", "kits", "renal mass", "oncocytoma",
        "renal cyst", "kidney stone", "hydronephrosis"
    ],
    "all_leukemia": [
        "leukemia", "lymphoblastic", "all", "blast", "blasts", "bone marrow", "b-cell all",
        "t-cell all", "peripheral smear", "myeloid", "hematologic", "c-nmc"
    ],
    "oral": [
        "oral", "tongue", "mouth", "oscc", "oral squamous", "leukoplakia", "erythroplakia",
        "gingiva", "buccal", "palate", "dysplasia", "keratin"
    ],
    "lung_colon": [
        "lung", "colon", "colorectal", "adenocarcinoma", "squamous cell", "lc25000",
        "polyp", "polyps", "bronchoscopy", "colonoscopy", "kras", "egfr", "alveolar", "mucinous"
    ],
    "lymphoma": [
        "lymphoma", "lymph node", "hodgkin", "non-hodgkin", "cll", "fl", "mcl",
        "mantle cell", "follicular", "b-cell lymphoma", "reed-sternberg"
    ],
    "brain": [
        "brain", "glioma", "glioblastoma", "astrocytoma", "meningioma", "pituitary",
        "oligodendroglioma", "brats", "mri brain", "cerebral", "cranial", "flair"
    ],
    "cervical": [
        "cervical", "cervix", "pap smear", "cytology", "hpv", "cin", "dyskeratotic",
        "koilocytotic", "squamous intraepithelial", "sipakmed", "colposcopy"
    ],
}

_GENERAL_ONCOLOGY_TERMS = [
    "cancer", "tumor", "tumour", "malignant", "malignancy", "benign", "neoplasm",
    "oncology", "carcinoma", "sarcoma", "metastasis", "metastatic", "biopsy",
    "histopathology", "staging", "tmn", "chemotherapy", "radiation therapy",
    "immunotherapy", "remission", "palliative", "antineoplastic", "mass", "lesion",
    "nodule", "suspicious", "atypical", "neoplastic"
]


class CancerRelevanceEvaluator:
    """Evaluates whether the clinical context / request is genuinely cancer-relevant."""

    def __init__(self) -> None:
        thresholds = get_thresholds()
        self.minimum_score = thresholds.get("global", {}).get(
            "cancer_relevance", {}
        ).get("minimum_score", 0.55)

    def evaluate_relevance(
        self,
        text: Optional[str],
        category_hint: Optional[str] = None,
        has_medical_image: bool = False,
    ) -> Tuple[float, Optional[str], bool]:
        """
        Calculates relevance score in [0.0, 1.0].
        Returns:
            score: float
            detected_category: str | None
            passes_gate: bool (score >= 0.55)
        """
        raw_text = (text or "").lower()
        if not raw_text and has_medical_image:
            # If medical image provided with category hint
            if category_hint and category_hint in _CATEGORY_TERMS:
                return 0.85, category_hint, True
            return 0.60, None, True

        # Count matches
        matched_categories: dict[str, int] = {}
        for cat, terms in _CATEGORY_TERMS.items():
            matches = sum(1 for term in terms if re.search(r"\b" + re.escape(term) + r"\b", raw_text))
            if matches > 0:
                matched_categories[cat] = matches

        general_matches = sum(
            1 for term in _GENERAL_ONCOLOGY_TERMS if re.search(r"\b" + re.escape(term) + r"\b", raw_text)
        )

        detected_category = category_hint
        if matched_categories:
            detected_category = max(matched_categories, key=matched_categories.get)

        # Base scoring
        score = 0.0
        if detected_category and detected_category in matched_categories:
            score += min(0.60, 0.30 + 0.15 * matched_categories[detected_category])
        if general_matches > 0:
            score = max(score, min(0.75, 0.55 + 0.10 * (general_matches - 1)))
        if category_hint and category_hint in _CATEGORY_TERMS and category_hint in matched_categories:
            score += 0.15
        if has_medical_image:
            score += 0.20

        score = min(1.0, max(0.0, score))

        # If user explicitly specified valid category and gave medical image
        if category_hint in _CATEGORY_TERMS and has_medical_image:
            score = max(score, 0.75)

        passed = score >= self.minimum_score
        logger.info(
            "cancer_relevance_evaluated",
            score=round(score, 3),
            detected_category=detected_category,
            passed=passed,
        )
        return score, detected_category, passed
