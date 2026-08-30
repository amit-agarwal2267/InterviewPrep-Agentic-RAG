import pytest
from langchain_core.runnables import RunnableLambda

from interview_prep_qna.core.agent.contextualizer import (
    ContextualizerAgent,
    ContextualizerDecision,
    QueryRoute,
)


def _agent(decision: ContextualizerDecision) -> ContextualizerAgent:
    async def classify_async(_: dict) -> ContextualizerDecision:
        return decision

    classifier = RunnableLambda(lambda _: decision, afunc=classify_async)
    return ContextualizerAgent(classifier=classifier)


@pytest.mark.parametrize(
    ("decision", "expected_route", "should_retrieve"),
    [
        (
            ContextualizerDecision(
                route="generic", reason="Greeting", direct_response="Hello!"
            ),
            QueryRoute.GENERIC,
            False,
        ),
        (
            ContextualizerDecision(
                route="irrelevant",
                reason="Cooking request",
                direct_response="Please ask a software-engineering question.",
            ),
            QueryRoute.IRRELEVANT,
            False,
        ),
        (
            ContextualizerDecision(
                route="relevant",
                reason="System-design question",
                standalone_query="How should a rate limiter be designed?",
            ),
            QueryRoute.RELEVANT,
            True,
        ),
    ],
)
def test_contextualizer_routes_typed_decisions(
    decision: ContextualizerDecision,
    expected_route: QueryRoute,
    should_retrieve: bool,
) -> None:
    result = _agent(decision).classify("test query")
    assert result.route is expected_route
    assert result.should_retrieve is should_retrieve


def test_contextualizer_rejects_empty_queries() -> None:
    decision = ContextualizerDecision(
        route="generic", reason="Greeting", direct_response="Hello!"
    )
    with pytest.raises(ValueError, match="must not be empty"):
        _agent(decision).classify("   ")


def test_relevant_decision_requires_standalone_query() -> None:
    with pytest.raises(ValueError, match="standalone_query"):
        ContextualizerDecision(route="relevant", reason="Technical request")


@pytest.mark.asyncio
async def test_contextualizer_maps_decision_to_shared_state() -> None:
    decision = ContextualizerDecision(
        route="relevant",
        reason="Project architecture question",
        standalone_query="Why did this project choose HNSW?",
    )

    state = await _agent(decision).classify_state({"query": "Why HNSW?"})

    assert state["current_agent"] == "contextualizer"
    assert state["contextualized_query"] == "Why did this project choose HNSW?"
    assert state["contextualization"]["route"] is QueryRoute.RELEVANT
