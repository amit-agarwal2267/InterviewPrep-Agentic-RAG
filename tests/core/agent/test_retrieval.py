import pytest

from interview_prep_qna.core.agent.retrieval import RAGPipeline, reciprocal_rank_fusion
from interview_prep_qna.core.agent.state import RetrievedEvidence


def _evidence(chunk_id: str, *, source: str = "notion") -> RetrievedEvidence:
    return RetrievedEvidence(
        chunk_id=chunk_id,
        document_id=f"document-{chunk_id}",
        content=f"content for {chunk_id}",
        source_type=source,
    )


def test_reciprocal_rank_fusion_rewards_results_from_both_searches() -> None:
    dense = [_evidence("shared"), _evidence("dense-only")]
    lexical = [_evidence("lexical-only"), _evidence("shared")]

    results = reciprocal_rank_fusion(dense, lexical, limit=3, rrf_k=60)

    assert results[0].chunk_id == "shared"
    assert results[0].dense_rank == 1
    assert results[0].lexical_rank == 2
    assert results[0].fusion_score == pytest.approx(1 / 61 + 1 / 62)


@pytest.mark.asyncio
async def test_rag_pipeline_stores_fused_results_in_state() -> None:
    async def dense(_: str, __: int) -> list[RetrievedEvidence]:
        return [_evidence("shared"), _evidence("dense-only")]

    async def lexical(_: str, __: int) -> list[RetrievedEvidence]:
        return [_evidence("shared"), _evidence("lexical-only")]

    pipeline = RAGPipeline(
        dense_retriever=dense,
        lexical_retriever=lexical,
        candidate_limit=20,
        result_limit=2,
    )
    state = await pipeline.retrieve("Why did we choose HNSW?", {"route": "rag"})

    assert state["route"] == "rag"
    assert state["contextualized_query"] == "Why did we choose HNSW?"
    assert len(state["retrieved_evidence"]) == 2
    assert state["retrieval_metadata"].dense_candidates == 2
    assert state["retrieval_metadata"].lexical_candidates == 2


@pytest.mark.asyncio
async def test_rag_pipeline_hands_retrieval_state_to_grader() -> None:
    async def search(_: str, __: int) -> list[RetrievedEvidence]:
        return [_evidence("shared")]

    class FakeGrader:
        async def resolve(self, state: dict) -> dict:
            return {**state, "grading": {"action": "answer", "sufficient": True}}

    pipeline = RAGPipeline(
        dense_retriever=search,
        lexical_retriever=search,
        grading_agent=FakeGrader(),
    )
    state = await pipeline.run("Why did we choose HNSW?")

    assert state["retrieved_evidence"]
    assert state["grading"] == {"action": "answer", "sufficient": True}
