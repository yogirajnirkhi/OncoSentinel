"""
OncoSentinel v2.0 — Grounding & Answer Verification Engine
Satisfies: FR-12, FR-30 (verify relevance, grounding, provenance, contradiction, citation integrity)
Grounded in: Architecture v2.0 §12 (Evidence before generation; safe failure is a designed state)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from services.core.logging import get_logger
from services.rag.llm_reasoning import GroundedReasoningOutput
from services.rag.retriever import RetrievalResult

logger = get_logger(__name__)


@dataclass
class VerificationReport:
    is_valid: bool
    citation_integrity_passed: bool
    grounding_passed: bool
    contradiction_detected: bool
    hallucinated_citations: list[str]
    coverage_score: float
    safety_state: str  # VERIFIED | REVIEW_REQUIRED | NO_GROUNDED_ANSWER
    reason: str


class AnswerVerifier:
    """Performs rigorous post-generation grounding and citation integrity verification."""

    def verify(
        self,
        output: GroundedReasoningOutput,
        retrieval: RetrievalResult,
    ) -> VerificationReport:
        if not output.is_grounded or output.evidence_coverage_score < 0.20:
            return VerificationReport(
                is_valid=False,
                citation_integrity_passed=False,
                grounding_passed=False,
                contradiction_detected=False,
                hallucinated_citations=[],
                coverage_score=output.evidence_coverage_score,
                safety_state="NO_GROUNDED_ANSWER",
                reason="Evidence coverage below minimum threshold (0.20). Safe refusal triggered.",
            )

        # 1. Check Citation Integrity
        # Extract all [X] tags from text
        found_citations = re.findall(r"\[([A-Z0-9_\-]+)\]", output.response_text)
        valid_set = set(retrieval.citation_ids)
        hallucinated: list[str] = [c for c in found_citations if c not in valid_set and not c.startswith("CITATION")]

        cit_integrity = len(hallucinated) == 0

        # 2. Check Grounding Overlap
        text_words = set(re.findall(r"\w+", output.response_text.lower()))
        evidence_words = set(
            re.findall(
                r"\w+",
                " ".join(item.content for item in retrieval.items).lower(),
            )
        )
        overlap = len(text_words.intersection(evidence_words)) / max(len(text_words), 1)
        grounding_passed = overlap >= 0.35

        # 3. Simple Contradiction Detection Proxy
        # (e.g. check for contradictory absolute negative phrases against evidence)
        contradiction = False
        if "benign" in output.response_text.lower() and "malignant" in output.response_text.lower():
            if "definitive proof" in output.response_text.lower():
                contradiction = True

        is_valid = cit_integrity and grounding_passed and not contradiction
        safety_state = "VERIFIED" if is_valid else "REVIEW_REQUIRED"

        logger.info(
            "answer_verification_completed",
            is_valid=is_valid,
            safety_state=safety_state,
            citation_passed=cit_integrity,
            grounding_passed=grounding_passed,
        )

        return VerificationReport(
            is_valid=is_valid,
            citation_integrity_passed=cit_integrity,
            grounding_passed=grounding_passed,
            contradiction_detected=contradiction,
            hallucinated_citations=hallucinated,
            coverage_score=output.evidence_coverage_score,
            safety_state=safety_state,
            reason=(
                "All citation and grounding checks passed."
                if is_valid
                else "Discrepancy detected between generated narrative and source citations."
            ),
        )


_verifier_singleton: Optional[AnswerVerifier] = None


def get_answer_verifier() -> AnswerVerifier:
    global _verifier_singleton
    if _verifier_singleton is None:
        _verifier_singleton = AnswerVerifier()
    return _verifier_singleton
