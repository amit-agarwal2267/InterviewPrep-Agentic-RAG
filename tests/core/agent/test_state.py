from typing import get_type_hints

from langchain_core.messages import HumanMessage
from langgraph.graph.message import add_messages

from interview_prep_qna.core.agent.enums import AgentRoute
from interview_prep_qna.core.agent.state import AgentState


def test_agent_state_maps_shared_and_agent_specific_sections() -> None:
    hints = get_type_hints(AgentState, include_extras=True)

    assert {
        "query",
        "messages",
        "route",
        "contextualization",
        "routing",
        "retrieved_evidence",
        "grading",
        "summarization",
        "interrogation",
        "write_back",
    } <= hints.keys()


def test_message_reducer_preserves_conversation_history() -> None:
    first = HumanMessage(content="Why HNSW?", id="message-1")
    replacement = HumanMessage(content="Why did I choose HNSW?", id="message-1")
    second = HumanMessage(content="Show the implementation", id="message-2")

    messages = add_messages([first], [replacement, second])

    assert [message.content for message in messages] == [
        "Why did I choose HNSW?",
        "Show the implementation",
    ]


def test_route_enum_covers_terminal_and_write_back_routes() -> None:
    assert AgentRoute.GRADING == "grading"
    assert AgentRoute.GITHUB == "github"
    assert AgentRoute.WEB == "web"
    assert AgentRoute.WRITE_BACK == "write_back"
    assert AgentRoute.COMPLETE == "complete"
