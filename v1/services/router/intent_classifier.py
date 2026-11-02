"""
OncoSentinel v2.0 — Intent Classification Engine
Satisfies: FR-03 (determine user intent, modality, and capability fit)
"""
from __future__ import annotations

import re
from typing import Optional

from services.core.logging import get_logger

logger = get_logger(__name__)

INTENT_DIAGNOSTIC = "DIAGNOSTIC_ANALYSIS"
INTENT_EVIDENCE = "EVIDENCE_QUERY"
INTENT_LONGITUDINAL = "LONGITUDINAL_REVIEW"
INTENT_OUTCOME = "OUTCOME_EVALUATION"
INTENT_UNKNOWN = "UNKNOWN"

_EVIDENCE_KEYWORDS = [
    r"\bguideline\b",
    r"\breference\b",
    r"\bliterature\b",
    r"\bprotocol\b",
    r"\btrial\b",
    r"\bstudy\b",
    r"\bwhat is the standard\b",
    r"\brecommendation\b",
    r"\bnccn\b",
    r"\besmo\b",
    r"\basco\b",
    r"\bpubmed\b",
    r"\bwhat does\b",
    r"\bhow does\b",
]

_LONGITUDINAL_KEYWORDS = [
    r"\btimeline\b",
    r"\bhistory\b",
    r"\btrajectory\b",
    r"\bserial\b",
    r"\bprevious scan\b",
    r"\bprior scan\b",
    r"\bover time\b",
    r"\brecurrence\b",
    r"\bprogression\b",
    r"\btrend\b",
    r"\bresponse to therapy\b",
    r"\bbaseline comparison\b",
]

_OUTCOME_KEYWORDS = [
    r"\bendpoint\b",
    r"\badjudication\b",
    r"\boutcome\b",
    r"\btime to diagnosis\b",
    r"\boverride rate\b",
    r"\bclinical study arm\b",
]


class IntentClassifier:
    """Classifies user intent from text query and input modality."""

    def classify_intent(self, text: Optional[str], has_image: bool, modality: Optional[str] = None) -> str:
        text_lower = (text or "").lower()

        # If image or scan is present, default is diagnostic analysis unless explicitly querying evidence
        if has_image and modality != "text":
            # Check if user is asking a purely educational/literature question about an image without clinical diagnostic intent
            if re.search(r"^(what\s+is|what\s+are|guidelines\s+for|explain\s+literature)", text_lower):
                return INTENT_EVIDENCE
            return INTENT_DIAGNOSTIC

        # Check longitudinal inquiries
        if any(re.search(kw, text_lower) for kw in _LONGITUDINAL_KEYWORDS):
            return INTENT_LONGITUDINAL

        # Check outcome evaluation
        if any(re.search(kw, text_lower) for kw in _OUTCOME_KEYWORDS):
            return INTENT_OUTCOME

        # Check evidence / guideline queries
        if any(re.search(kw, text_lower) for kw in _EVIDENCE_KEYWORDS):
            return INTENT_EVIDENCE

        # Check if text contains clinical diagnostic inquiry
        if any(w in text_lower for w in ["diagnose", "classify", "biopsy", "histology", "stage", "malignant", "benign"]):
            return INTENT_DIAGNOSTIC

        # Default fallback
        if len(text_lower.strip()) > 0:
            return INTENT_EVIDENCE
        return INTENT_UNKNOWN
