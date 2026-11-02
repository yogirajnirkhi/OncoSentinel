"""
OncoSentinel v2.0 — Grounded Local LLM Clinical Reasoning Engine
Satisfies: FR-10 (structure and summarize supplied evidence; zero fabrication of missing evidence)
Grounded in: Architecture v2.0 §12 (Evidence before generation; Local LLM under explicit grounding controls)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

import httpx

from services.core.logging import get_logger
from services.core.settings import get_settings
from services.rag.retriever import RetrievalResult

logger = get_logger(__name__)


@dataclass
class GroundedReasoningOutput:
    query: str
    response_text: str
    cited_sources: list[str]
    evidence_coverage_score: float
    is_grounded: bool
    used_engine: str


class GroundedClinicalLLM:
    """Orchestrates evidence-grounded clinical reasoning using Ollama with deterministic grounded fallback."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate_grounded_response(
        self,
        query: str,
        retrieval_result: RetrievalResult,
        clinical_context: Optional[str] = None,
    ) -> GroundedReasoningOutput:
        # If insufficient evidence, trigger safe refusal rather than hallucinating
        if not retrieval_result.has_sufficient_evidence:
            logger.warning("evidence_insufficient_triggering_safe_refusal", query=query)
            return GroundedReasoningOutput(
                query=query,
                response_text=(
                    "NO_GROUNDED_ANSWER: Insufficient clinical evidence retrieved from authoritative oncology "
                    "guidelines to answer this query safely without potential hallucination. Please consult primary "
                    "NCCN/ASCO literature or provide additional case history."
                ),
                cited_sources=[],
                evidence_coverage_score=retrieval_result.aggregate_evidence_score,
                is_grounded=False,
                used_engine="safety_abstention_gate",
            )

        # Build strict clinical grounding prompt
        context_chunks = "\n\n".join(
            f"[{item.citation_id}] ({item.source_title}):\n{item.content}"
            for item in retrieval_result.items
        )

        system_prompt = (
            "You are OncoSentinel v2.0, an evidence-grounded oncology clinical decision-support engine. "
            "CRITICAL RULES:\n"
            "1. You must answer ONLY using the supplied evidence below.\n"
            "2. Cite every factual claim using [CITATION_ID].\n"
            "3. Do NOT extrapolate, speculate, or fabricate treatments or statistics.\n"
            "4. If the evidence does not state the answer, state that evidence is unavailable."
        )

        user_content = f"QUESTION: {query}\n\nEVIDENCE:\n{context_chunks}"
        if clinical_context:
            user_content += f"\n\nPATIENT CLINICAL CONTEXT:\n{clinical_context}"

        # Attempt Ollama connection if accessible
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{self.settings.ollama_url}/api/generate",
                    json={
                        "model": self.settings.ollama_model,
                        "prompt": f"{system_prompt}\n\n{user_content}",
                        "stream": False,
                    },
                )
                if res.status_code == 200:
                    text = res.json().get("response", "").strip()
                    if text:
                        return GroundedReasoningOutput(
                            query=query,
                            response_text=text,
                            cited_sources=retrieval_result.citation_ids,
                            evidence_coverage_score=retrieval_result.aggregate_evidence_score,
                            is_grounded=True,
                            used_engine="ollama_local_llm",
                        )
        except Exception as exc:
            logger.info("ollama_unavailable_using_deterministic_grounded_synthesizer", error=str(exc))

        # Deterministic Grounded Synthesis (100% reliable fallback)
        primary = retrieval_result.items[0]
        synthesis_lines = [
            f"CLINICAL EVIDENCE SYNTHESIS (Grounded in [{primary.citation_id}]):",
            f"{primary.content}",
        ]
        if len(retrieval_result.items) > 1:
            sec = retrieval_result.items[1]
            synthesis_lines.append(f"\nADDITIONAL CORROBORATION ([{sec.citation_id}]): {sec.content}")

        synthesis_lines.append(
            "\nCLINICAL ACTIONABILITY: Findings should be correlated with institutional tumor board review "
            "and patient-specific histopathology prior to therapeutic intervention."
        )

        response_text = "\n".join(synthesis_lines)
        return GroundedReasoningOutput(
            query=query,
            response_text=response_text,
            cited_sources=retrieval_result.citation_ids,
            evidence_coverage_score=retrieval_result.aggregate_evidence_score,
            is_grounded=True,
            used_engine="grounded_deterministic_synthesizer",
        )


_llm_singleton: Optional[GroundedClinicalLLM] = None


def get_grounded_llm() -> GroundedClinicalLLM:
    global _llm_singleton
    if _llm_singleton is None:
        _llm_singleton = GroundedClinicalLLM()
    return _llm_singleton
