import pytest
from langchain_core.runnables import RunnableLambda

from interview_prep_qna.core.agent.state import RetrievedEvidence
from interview_prep_qna.core.agent.summarizer import (
    SummarizerAgent,
    SummarizerDecision,
)


def _summarizer(decision: SummarizerDecision) -> SummarizerAgent:
    async def summarize(_: dict) -> SummarizerDecision:
        return decision

    return SummarizerAgent(summarizer=RunnableLambda(summarize))


@pytest.mark.asyncio
async def test_grounded_answer_is_returned_to_user() -> None:
    decision = SummarizerDecision(
        alignment="user_grounded",
        has_knowledge_gap=False,
    )
    state = await _summarizer(decision).summarize_state(
        {
            "query": "Why HNSW?",
            "response": "A repetitive draft",
            "retrieved_evidence": [
                RetrievedEvidence(
                    chunk_id="1",
                    document_id="1",
                    content="HNSW rationale",
                    source_type="github",
                )
            ],
        }
    )

    assert state["route"] == "complete"
    assert state["response"] == "A repetitive draft"
    assert "knowledge_gap" not in state


@pytest.mark.asyncio
async def test_generic_web_answer_is_forced_to_interrogator() -> None:
    decision = SummarizerDecision(
        alignment="user_grounded",
        has_knowledge_gap=False,
    )
    state = await _summarizer(decision).summarize_state(
        {
            "query": "Why did I use Tavily?",
            "response": "Generic web draft",
            "retrieved_evidence": [
                RetrievedEvidence(
                    chunk_id="web-1",
                    document_id="web-1",
                    content="General Tavily benefits",
                    source_type="web",
                    url="https://example.com/tavily",
                    metadata={"generic_external": True},
                )
            ],
        }
    )

    assert state["route"] == "interrogator"
    assert state["response"] == "Generic web draft"
    assert state["draft_response"] == "Generic web draft"
    assert state["knowledge_gap"]["alignment"] == "mixed"
    assert state["knowledge_gap"]["questions"]
