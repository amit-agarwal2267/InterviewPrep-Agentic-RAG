from types import SimpleNamespace

import pytest
from langchain_core.runnables import RunnableLambda

from interview_prep_qna.core.agent.grading import (
    GradingAction,
    GradingAgent,
    GradingDecision,
)
from interview_prep_qna.core.agent.state import RetrievedEvidence


def _grader(decision: GradingDecision) -> GradingAgent:
    async def return_decision(_: dict) -> GradingDecision:
        return decision

    return GradingAgent(grader=RunnableLambda(return_decision))


@pytest.mark.asyncio
async def test_grader_stores_decision_in_state() -> None:
    decision = GradingDecision(
        action="answer",
        sufficient=True,
        reason="The evidence covers the complete rationale.",
    )
    evidence = RetrievedEvidence(
        chunk_id="chunk-1",
        document_id="document-1",
        content="HNSW was selected for low-latency approximate nearest-neighbor search.",
        source_type="notion",
    )
    state = await _grader(decision).grade_state(
        {
            "query": "Why was HNSW selected?",
            "retrieved_evidence": [evidence],
        }
    )

    assert state["grading"]["action"] == "answer"
    assert state["grading"]["sufficient"] is True


@pytest.mark.asyncio
async def test_sufficient_evidence_is_handed_to_answer_agent() -> None:
    decision = GradingDecision(
        action="answer", sufficient=True, reason="All query parts are supported."
    )

    async def grade(_: dict) -> GradingDecision:
        return decision

    class FakeAnswerAgent:
        async def answer_state(self, state: dict) -> dict:
            return {**state, "response": "# Grounded answer\n\nSupported claim. [1]"}

    state = await GradingAgent(
        grader=RunnableLambda(grade), answer_agent=FakeAnswerAgent()
    ).resolve({"query": "Why HNSW?", "retrieved_evidence": []})

    assert state["grading"]["action"] == "answer"
    assert state["response"].startswith("# Grounded answer")


def test_code_request_requires_github_handoff() -> None:
    decision = GradingDecision(
        action="github",
        sufficient=False,
        reason="RAG explains the decision but cannot verify current code.",
        missing_information=["Current HNSW implementation code"],
    )

    assert decision.action is GradingAction.GITHUB
    assert decision.needs_github is True
    assert decision.needs_web is False
    assert decision.sufficient is False


@pytest.mark.asyncio
async def test_github_is_regraded_then_web_then_generic_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "interview_prep_qna.core.agent.grading.get_settings",
        lambda: SimpleNamespace(tavily_api_key="test-key"),
    )
    decisions = iter(
        [
            GradingDecision(
                action="github",
                sufficient=False,
                reason="Current code is missing.",
                missing_information=["HNSW implementation code"],
            ),
            GradingDecision(
                action="web",
                sufficient=False,
                reason="External documentation is still missing.",
                missing_information=["Current HNSW documentation"],
            ),
            GradingDecision(
                action="generic",
                sufficient=False,
                reason="The available sources are insufficient.",
            ),
        ]
    )

    async def grade(_: dict) -> GradingDecision:
        return next(decisions)

    class FakeSearchAgent:
        def __init__(self, source: str) -> None:
            self.source = source

        async def search(self, query: str, missing: list[str]):
            return [
                RetrievedEvidence(
                    chunk_id=f"{self.source}-chunk",
                    document_id=f"{self.source}-document",
                    content=f"Evidence for {query}: {missing}",
                    source_type=self.source,
                )
            ]

    class FakeGenericAgent:
        async def respond_state(self, state: dict, reason: str) -> dict:
            return {**state, "route": "generic", "response": reason}

    agent = GradingAgent(
        grader=RunnableLambda(grade),
        github_agent=FakeSearchAgent("github_live"),
        web_agent=FakeSearchAgent("web"),
        generic_agent=FakeGenericAgent(),
    )
    state = await agent.resolve(
        {"query": "Why HNSW, what code implements it, and is it still recommended?"}
    )

    assert [step["source"] for step in state["escalation_steps"]] == [
        "github",
        "web",
    ]
    assert len(state["retrieved_evidence"]) == 2
    assert state["grading"]["action"] == "generic"
    assert state["route"] == "generic"
    assert state["response"] == "The available sources are insufficient."


@pytest.mark.asyncio
async def test_web_is_unavailable_without_tavily_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "interview_prep_qna.core.agent.grading.get_settings",
        lambda: SimpleNamespace(tavily_api_key=None),
    )
    available_actions: list[tuple[GradingAction, ...]] = []

    async def grade(values: dict) -> GradingDecision:
        available_actions.append(values["available_actions"])
        return GradingDecision(
            action="generic", sufficient=False, reason="No web search configured."
        )

    class FakeGenericAgent:
        async def respond_state(self, state: dict, reason: str) -> dict:
            return {**state, "route": "generic", "response": reason}

    await GradingAgent(
        grader=RunnableLambda(grade), generic_agent=FakeGenericAgent()
    ).resolve({"query": "Why did I choose this project design?"})

    assert GradingAction.WEB not in available_actions[0]
