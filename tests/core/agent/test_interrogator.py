import pytest
from langchain_core.runnables import RunnableLambda

from interview_prep_qna.core.agent.interrogator import (
    InterrogationDecision,
    InterrogatorAgent,
)


def _agent(decisions: list[InterrogationDecision]) -> InterrogatorAgent:
    async def decide(_: dict) -> InterrogationDecision:
        return decisions.pop(0)

    return InterrogatorAgent(interrogator=RunnableLambda(decide))


def _state() -> dict:
    return {
        "query": "Why did I choose Tavily?",
        "draft_response": "# Tavily\n\nGeneric answer from public sources.",
        "knowledge_gap": {
            "reason": "The project-specific rationale is missing.",
            "questions": ["What requirement led you to choose Tavily?"],
        },
    }


@pytest.mark.asyncio
async def test_satisfied_first_reply_requests_consent_and_saves_on_yes() -> None:
    agent = _agent(
        [InterrogationDecision(satisfied=True, reason="Specific rationale supplied")],
    )
    state = await agent.start(_state())
    assert state["response"].startswith("# Tavily")
    assert state["response"].endswith("What requirement led you to choose Tavily?")

    state = await agent.handle_reply(
        state, "It returned citations and integrated with LangChain."
    )
    assert state["response"] == agent.CONSENT_PROMPT

    state = await agent.handle_reply(state, "yes")
    assert state["response"] == "Saving your clarification to the knowledge base."
    assert state["route"] == "write_back"
    assert state["interrogation"]["phase"] == "ready_to_write"
    assert state["interrogation"]["consent_granted"] is True


@pytest.mark.asyncio
async def test_two_question_limit_then_declined_storage() -> None:
    agent = _agent(
        [
            InterrogationDecision(
                satisfied=False,
                reason="Constraint is unclear",
                next_question="Which constraint mattered most?",
            ),
            InterrogationDecision(
                satisfied=False,
                reason="Still incomplete",
                next_question="This third question must never be shown?",
            ),
        ],
    )
    state = await agent.start(_state())
    state = await agent.handle_reply(state, "Integration")
    assert state["response"] == "Which constraint mattered most?"
    state = await agent.handle_reply(state, "Development time")
    assert state["response"] == agent.CONSENT_PROMPT
    assert len(state["interrogation"]["questions_asked"]) == 2

    state = await agent.handle_reply(state, "no")
    assert state["response"] == "No Information saved."
    assert state["route"] == "complete"
    assert state["interrogation"]["consent_granted"] is False


@pytest.mark.asyncio
async def test_ambiguous_consent_does_not_save() -> None:
    agent = _agent(
        [InterrogationDecision(satisfied=True, reason="Enough detail")]
    )
    state = await agent.start(_state())
    state = await agent.handle_reply(state, "Because it supports citations")
    state = await agent.handle_reply(state, "maybe later")

    assert state["response"].startswith("Please answer yes or no")
    assert state["interrogation"]["phase"] == "awaiting_consent"
