from uuid import uuid4

import pytest
from sqlalchemy import text

from interview_prep_qna.core.agent.retrieval import RAGPipeline
from interview_prep_qna.core.pipeline import ingest_document
from interview_prep_qna.db.client.postgres import get_session


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_hybrid_retrieval_is_stored_in_state() -> None:
    source_id = f"retrieval-pytest-{uuid4()}"
    inserted = False
    try:
        inserted = await ingest_document(
            source_type="correction",
            source_id=source_id,
            title="HNSW retrieval verification",
            url=None,
            content=(
                "We selected HNSW approximate nearest-neighbor search because it "
                "provided low query latency with a strong recall trade-off for "
                "the interview knowledge base."
            ),
        )
        state = await RAGPipeline().retrieve(
            "Why was HNSW selected for the knowledge base?"
        )

        matching = [
            item for item in state["retrieved_evidence"] if item.source_id == source_id
        ]
        assert matching
        assert matching[0].dense_rank is not None
        assert matching[0].lexical_rank is not None
        assert matching[0].fusion_score > 0
        assert state["retrieval_metadata"].fused_candidates > 0
        print("\nHybrid retrieval state:\n", state["retrieval_metadata"], matching[0])
    finally:
        if inserted:
            async with get_session() as session:
                await session.execute(
                    text(
                        "DELETE FROM documents WHERE source_type = 'correction' AND source_id = :source_id"
                    ),
                    {"source_id": source_id},
                )
                await session.commit()
