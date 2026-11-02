"""
Tests for Clinical RAG, Grounded Reasoning, and Verification (FR-09..12, FR-30)
"""
from __future__ import annotations

import pytest

from services.rag.llm_reasoning import GroundedClinicalLLM
from services.rag.retriever import HybridRetriever
from services.rag.vector_store import ClinicalVectorStore
from services.rag.verifier import AnswerVerifier


def test_vector_store_retrieves_relevant_guidelines():
    store = ClinicalVectorStore()
    results = store.search_similar(query="breast core needle biopsy BI-RADS 4", category="breast", top_k=2)

    assert len(results) > 0
    top_chunk, score = results[0]
    assert "BI-RADS" in top_chunk.content or "breast" in top_chunk.category


def test_hybrid_retriever_evidence_scoring():
    retriever = HybridRetriever()
    result = retriever.retrieve(query="solid renal cortical mass enhancement", category="kidney")

    assert result.has_sufficient_evidence is True
    assert result.aggregate_evidence_score >= 0.20
    assert len(result.citation_ids) > 0


@pytest.mark.asyncio
async def test_grounded_llm_synthesizes_with_citations():
    retriever = HybridRetriever()
    llm = GroundedClinicalLLM()
    verifier = AnswerVerifier()

    retrieval_res = retriever.retrieve(query="BI-RADS 4 core needle biopsy recommendations", category="breast")
    reasoning_out = await llm.generate_grounded_response(
        query="BI-RADS 4 core needle biopsy recommendations",
        retrieval_result=retrieval_res,
    )

    assert reasoning_out.is_grounded is True
    assert len(reasoning_out.cited_sources) > 0

    verification = verifier.verify(reasoning_out, retrieval_res)
    assert verification.is_valid is True
    assert verification.safety_state in ["VERIFIED", "REVIEW_REQUIRED"]


@pytest.mark.asyncio
async def test_verifier_triggers_no_grounded_answer_on_empty_evidence():
    retriever = HybridRetriever()
    llm = GroundedClinicalLLM()

    # Empty mock retrieval result
    from services.rag.retriever import RetrievalResult
    empty_retrieval = RetrievalResult(
        query="obscure unknown topic",
        items=[],
        aggregate_evidence_score=0.05,
        citation_ids=[],
        has_sufficient_evidence=False,
    )

    out = await llm.generate_grounded_response(query="obscure", retrieval_result=empty_retrieval)
    assert out.is_grounded is False
    assert "NO_GROUNDED_ANSWER" in out.response_text
