import pytest
from langchain_core.runnables import RunnableLambda

from interview_prep_qna.core.agent.router import (
    RouteDestination,
    RouterAgent,
    RouterDecision,
)


def _router(decision: RouterDecision, rag_pipeline=None) -> RouterAgent:
    async def return_decision(_: dict) -> RouterDecision:
        return decision

    return RouterAgent(
        router=RunnableLambda(return_decision), rag_pipeline=rag_pipeline
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("decision", "expected", "use_rag"),
    [
        (
            RouterDecision(destination="rag", reason="Technical interview query"),
            RouteDestination.RAG,
            True,
        ),
        (
            RouterDecision(destination="generic", reason="Greeting"),
            RouteDestination.GENERIC,
            False,
        ),
    ],
)
async def test_router_returns_typed_destination(
    decision: RouterDecision,
    expected: RouteDestination,
    use_rag: bool,
) -> None:
    result = await _router(decision).route("test query")
    assert result.destination is expected
    assert result.use_rag is use_rag


@pytest.mark.asyncio
async def test_router_rejects_empty_query() -> None:
    decision = RouterDecision(destination="generic", reason="Greeting")
    with pytest.raises(ValueError, match="must not be empty"):
        await _router(decision).route("  ")


@pytest.mark.asyncio
async def test_router_invokes_rag_pipeline_and_returns_graded_state() -> None:
    class FakeRAGPipeline:
        async def run(self, query: str, state: dict) -> dict:
            return {
                **state,
                "contextualized_query": query,
                "retrieved_evidence": [],
                "grading": {"action": "github", "sufficient": False},
            }

    decision = RouterDecision(destination="rag", reason="Technical query")
    state = await _router(decision, FakeRAGPipeline()).route_and_run(
        "Show me the current HNSW code"
    )

    assert state["route"] == "rag"
    assert state["current_agent"] == "router"
    assert state["routing"]["destination"] is RouteDestination.RAG
    assert state["grading"]["action"] == "github"
