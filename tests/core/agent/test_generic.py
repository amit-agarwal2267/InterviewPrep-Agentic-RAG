import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from interview_prep_qna.core.agent.generic import GenericAgent
from interview_prep_qna.core.agent.state import RetrievedEvidence


class PassthroughSummarizer:
    async def summarize_state(self, state: dict) -> dict:
        return state


@pytest.mark.asyncio
async def test_generic_agent_extracts_text_from_structured_content_blocks() -> None:
    async def greet(_: dict) -> AIMessage:
        return AIMessage(
            content=[
                {
                    "type": "text",
                    "text": "Hi! What interview topic or software project would you like to explore?",
                    "index": 0,
                }
            ]
        )

    state = await GenericAgent(
        responder=RunnableLambda(greet), summarizer=PassthroughSummarizer()
    ).respond_state({"query": "Hi"}, "Greeting")
    assert state["response"] == (
        "Hi! What interview topic or software project would you like to explore?"
    )


@pytest.mark.asyncio
async def test_generic_agent_retains_external_answer_flag() -> None:
    async def summarize(values: dict) -> str:
        assert "fast search API" in values["context"]
        return "Tavily offers a search API designed for LLM retrieval workflows."

    agent = GenericAgent(
        responder=RunnableLambda(summarize), summarizer=PassthroughSummarizer()
    )
    state = await agent.respond_state(
        {
            "query": "Why did I use Tavily?",
            "retrieved_evidence": [
                RetrievedEvidence(
                    chunk_id="web-1",
                    document_id="web-document-1",
                    content="Tavily provides a fast search API with ranked web context.",
                    source_type="web",
                    metadata={
                        "generic_external": True,
                        "grounded_in_user_project": False,
                    },
                )
            ],
        },
        "No project-specific rationale was found.",
    )

    assert state["route"] == "generic"
    assert state["response"].startswith(
        "Generic answer — not verified from your project records:"
    )


@pytest.mark.asyncio
async def test_generic_agent_does_not_add_flag_without_web_evidence() -> None:
    async def greet(_: dict) -> str:
        return "Hi! What interview topic would you like to explore?"

    state = await GenericAgent(
        responder=RunnableLambda(greet), summarizer=PassthroughSummarizer()
    ).respond_state({"query": "Hi"}, "Greeting")
    assert state["response"] == "Hi! What interview topic would you like to explore?"
