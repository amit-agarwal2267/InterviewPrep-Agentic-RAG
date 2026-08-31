import pytest
from langchain_core.runnables import RunnableLambda

from interview_prep_qna.core.agent.answer import AnswerAgent
from interview_prep_qna.core.agent.state import RetrievedEvidence


def _evidence() -> list[RetrievedEvidence]:
    return [
        RetrievedEvidence(
            chunk_id="chunk-1",
            document_id="document-1",
            content="The project selected HNSW for low-latency vector retrieval.",
            source_type="github",
            source_id="owner/repository:README.md",
            title="Architecture README",
            url="https://github.com/owner/repository/blob/main/README.md",
            image_url="https://example.com/retrieval.png",
        )
    ]


@pytest.mark.asyncio
async def test_answer_agent_appends_canonical_references() -> None:
    async def respond(values: dict) -> str:
        assert "https://example.com/retrieval.png" in values["evidence"]
        return "# HNSW Retrieval\n\nThe project uses HNSW for retrieval. [1]"

    answer = await AnswerAgent(responder=RunnableLambda(respond)).answer(
        "Why did the project use HNSW?", _evidence()
    )
    assert "The project uses HNSW for retrieval. [1]" in answer
    assert "## References" in answer
    assert (
        "[Architecture README](https://github.com/owner/repository/blob/main/README.md)"
        in answer
    )


@pytest.mark.asyncio
async def test_answer_agent_deduplicates_chunks_from_the_same_reference() -> None:
    evidence = _evidence()
    evidence.append(
        evidence[0].model_copy(
            update={"chunk_id": "chunk-2", "content": "LangGraph controls the workflow."}
        )
    )

    async def respond(values: dict) -> str:
        assert values["evidence"].count("[Evidence ") == 1
        assert "LangGraph controls the workflow." in values["evidence"]
        return "The same source supports both claims. [1] It also supports this. [1]"

    answer = await AnswerAgent(responder=RunnableLambda(respond)).answer(
        "Explain the architecture", evidence
    )

    assert answer.count("[Architecture README](https://github.com/owner/repository/blob/main/README.md)") == 1
    assert answer.count("[1]") == 2

@pytest.mark.asyncio
async def test_answer_agent_requires_sufficient_grading() -> None:
    agent = AnswerAgent(responder=RunnableLambda(lambda _: "unused"))
    with pytest.raises(ValueError, match="not been graded as sufficient"):
        await agent.answer_state(
            {
                "query": "Why HNSW?",
                "grading": {"action": "github", "sufficient": False},
                "retrieved_evidence": _evidence(),
            }
        )
