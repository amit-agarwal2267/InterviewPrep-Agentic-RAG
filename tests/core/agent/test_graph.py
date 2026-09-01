from types import SimpleNamespace

import pytest
from langchain_core.runnables import RunnableLambda
from langgraph.types import Command

from interview_prep_qna.core.agent.decisions import (
    InterrogationDecision,
    RouterDecision,
)
from interview_prep_qna.core.agent.enums import GradingAction
from interview_prep_qna.core.agent.graph import build_agent_graph, graph_resume_config
from interview_prep_qna.core.agent.interrogator import InterrogatorAgent
from interview_prep_qna.core.agent.state import RetrievedEvidence

# from langgraph.types import Command


class FakeContextualizer:
    async def classify_state(self, state: dict) -> dict:
        return {
            **state,
            "contextualized_query": state["query"],
            "contextualization": {"route": "relevant", "reason": "Technical"},
        }


class FakeRouter:
    def __init__(self, destination: str) -> None:
        self.destination = destination

    async def route(self, query: str, history=None) -> RouterDecision:
        return RouterDecision(destination=self.destination, reason="Test route")


class FakeRAG:
    async def retrieve(self, query: str, state: dict) -> dict:
        return {
            **state,
            "retrieved_evidence": [_evidence("rag")],
            "retrieval_metadata": {},
        }


class FakeGrader:
    def __init__(self, actions: list[GradingAction], visited: list[str]) -> None:
        self.actions = actions
        self.visited = visited

    async def grade(self, query, evidence, *, stage, available_actions):
        action = self.actions.pop(0)
        assert action in available_actions
        self.visited.append(f"grade:{stage}")
        from interview_prep_qna.core.agent.decisions import GradingDecision

        return GradingDecision(
            action=action,
            sufficient=action is GradingAction.ANSWER,
            reason=f"Route to {action}",
            missing_information=["missing detail"],
        )


class FakeSearch:
    def __init__(self, source: str, visited: list[str]) -> None:
        self.source = source
        self.visited = visited

    async def search(self, query: str, missing: list[str]):
        self.visited.append(self.source)
        return [_evidence(self.source)]


class FakeAnswer:
    def __init__(self, visited: list[str]) -> None:
        self.visited = visited

    async def generate_state(self, state: dict) -> dict:
        self.visited.append("answer")
        return {**state, "response": "Grounded draft", "route": "summarizer"}


class CompleteSummarizer:
    def __init__(self, visited: list[str]) -> None:
        self.visited = visited

    async def summarize_state(self, state: dict) -> dict:
        self.visited.append("summarizer")
        return {**state, "response": "Final answer", "route": "complete"}


class FakeGeneric:
    async def generate_state(self, state: dict, reason: str) -> dict:
        return {**state, "response": "Generic draft", "route": "summarizer"}


def _evidence(source: str) -> RetrievedEvidence:
    return RetrievedEvidence(
        chunk_id=f"{source}-chunk",
        document_id=f"{source}-document",
        content=f"{source} evidence",
        source_type=source,
    )


@pytest.mark.asyncio
async def test_graph_runs_bounded_escalations_then_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "interview_prep_qna.core.agent.graph.get_settings",
        lambda: SimpleNamespace(tavily_api_key="test-key"),
    )
    visited: list[str] = []
    graph = build_agent_graph(
        contextualizer=FakeContextualizer(),
        router=FakeRouter("rag"),
        rag_pipeline=FakeRAG(),
        grader=FakeGrader(
            [GradingAction.GITHUB, GradingAction.WEB, GradingAction.ANSWER], visited
        ),
        github=FakeSearch("github", visited),
        web=FakeSearch("web", visited),
        answer=FakeAnswer(visited),
        summarizer=CompleteSummarizer(visited),
        generic=FakeGeneric(),
    )
    state = await graph.ainvoke(
        {"query": "Explain and show the implementation"},
        graph_resume_config("bounded-escalation"),
    )

    assert state["response"] == "Final answer"
    assert state["route"] == "complete"
    assert visited == [
        "grade:rag",
        "github",
        "grade:github",
        "web",
        "grade:web",
        "answer",
        "summarizer",
    ]


@pytest.mark.asyncio
async def test_graph_interrogates_then_writes_back_after_consent() -> None:
    async def satisfied(_: dict) -> InterrogationDecision:
        return InterrogationDecision(satisfied=True, reason="Specific detail supplied")

    interrogator = InterrogatorAgent(interrogator=RunnableLambda(satisfied))

    class GapSummarizer:
        async def summarize_state(self, state: dict) -> dict:
            return await interrogator.start(
                {
                    **state,
                    "draft_response": state["response"],
                    "knowledge_gap": {
                        "reason": "Project rationale missing",
                        "questions": ["Why did you choose it?"],
                        "alignment": "generic",
                    },
                }
            )

    class FakeWriteBack:
        async def __call__(self, state: dict) -> dict:
            session = {**state["interrogation"], "saved": True}
            return {
                **state,
                "interrogation": session,
                "write_back": {"changed": True},
                "response": "Information saved.",
                "route": "complete",
            }

    graph = build_agent_graph(
        contextualizer=FakeContextualizer(),
        router=FakeRouter("generic"),
        rag_pipeline=FakeRAG(),
        grader=FakeGrader([GradingAction.GENERIC], []),
        github=FakeSearch("github", []),
        web=FakeSearch("web", []),
        generic=FakeGeneric(),
        answer=FakeAnswer([]),
        summarizer=GapSummarizer(),
        interrogator=interrogator,
        write_back=FakeWriteBack(),
    )
    config = graph_resume_config("interrogation-flow")

    first = await graph.ainvoke({"query": "Why did I choose it?"}, config)
    assert first["__interrupt__"][0].value["phase"] == "awaiting_answer"
    assert first["__interrupt__"][0].value["questions_asked"] == 1

    consent = await graph.ainvoke(
        Command(resume="It returned source URLs required by the answer."), config
    )
    assert consent["__interrupt__"][0].value["phase"] == "awaiting_consent"

    final = await graph.ainvoke(Command(resume="yes"), config)
    assert final["route"] == "complete"
    assert final["response"] == "Information saved."
    assert final["interrogation"]["saved"] is True
