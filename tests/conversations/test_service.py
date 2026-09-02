from datetime import UTC, datetime
from uuid import uuid4

import pytest
from langgraph.types import Command

from interview_prep_qna.conversations.models import Conversation, Message, MessageRole
from interview_prep_qna.conversations.service import ConversationService


class FakeRepository:
    def __init__(self, messages: list[Message] | None = None) -> None:
        now = datetime.now(UTC)
        self.conversation = Conversation(
            _id="conversation-1",
            title="HNSW",
            active_branch_id="main",
            created_at=now,
            updated_at=now,
        )
        self.messages = list(messages or [])

    async def get_conversation(self, conversation_id: str) -> Conversation:
        return self.conversation

    async def list_messages(self, conversation_id: str, branch_id: str):
        return list(self.messages)

    async def append_message(
        self, conversation_id, branch_id, role, content, *, metadata=None, **kwargs
    ) -> Message:
        message = _message(
            role,
            content,
            len(self.messages) + 1,
            metadata=metadata or {},
        )
        self.messages.append(message)
        return message


class FakeGraph:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.inputs = []

    async def ainvoke(self, graph_input, config):
        self.inputs.append((graph_input, config))
        return self.responses.pop(0)


def _message(
    role: MessageRole,
    content: str,
    sequence: int,
    *,
    metadata: dict | None = None,
) -> Message:
    return Message(
        _id=uuid4().hex,
        conversation_id="conversation-1",
        branch_id="main",
        role=role,
        content=content,
        sequence=sequence,
        created_at=datetime.now(UTC),
        metadata=metadata or {},
    )


@pytest.mark.asyncio
async def test_chat_passes_only_last_ten_user_messages_to_new_graph_turn() -> None:
    existing = [
        _message(MessageRole.USER, f"user-{index}", index)
        if index % 2
        else _message(MessageRole.ASSISTANT, f"assistant-{index}", index)
        for index in range(1, 25)
    ]
    repository = FakeRepository(existing)
    graph = FakeGraph([{"response": "Final response"}])

    result = await ConversationService(repository, graph).chat(
        "conversation-1", "What about that existing approach?"
    )

    graph_input = graph.inputs[0][0]
    assert len(graph_input["messages"]) == 10
    assert all(message.type == "human" for message in graph_input["messages"])
    assert graph_input["messages"][-1].content == "What about that existing approach?"
    assert result.assistant_message.content == "Final response"


@pytest.mark.asyncio
async def test_chat_resumes_pending_interrogation_instead_of_starting_new_turn() -> None:
    pending = _message(
        MessageRole.ASSISTANT,
        "Why did you choose it?",
        1,
        metadata={
            "awaiting_resume": True,
            "interrupt_phase": "awaiting_answer",
            "graph_thread_id": "thread-1",
        },
    )
    repository = FakeRepository([pending])
    graph = FakeGraph([{"response": "Information saved."}])

    result = await ConversationService(repository, graph).chat(
        "conversation-1", "Because it returned citations."
    )

    graph_input, config = graph.inputs[0]
    assert isinstance(graph_input, Command)
    assert config["configurable"]["thread_id"] == "thread-1"
    assert result.interrupted is False
    assert result.assistant_message.content == "Information saved."
