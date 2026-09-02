import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from interview_prep_qna.conversations.models import (
    Branch,
    ChatResponse,
    ConversationDetail,
    Message,
    MessageRole,
)
from interview_prep_qna.conversations.repository import ConversationRepository
from interview_prep_qna.core.agent.graph import graph_resume_config
from interview_prep_qna.observability import get_langfuse_client

logger = logging.getLogger(__name__)

# Human-readable labels for each graph node that the frontend will display.
_NODE_STATUS: dict[str, str] = {
    "contextualizer": "Understanding your question…",
    "router": "Deciding the best approach…",
    "rag": "Searching knowledge base…",
    "grading": "Evaluating retrieved evidence…",
    "github": "Searching GitHub repositories…",
    "web": "Searching the web…",
    "generic": "Generating a response…",
    "answer": "Composing the answer…",
    "summarizer": "Summarising the response…",
    "interrogator": "Preparing a follow-up question…",
    "write_back": "Saving conversation state…",
}


@dataclass(frozen=True)
class ChatDelta:
    content: str


class ConversationService:
    """Coordinate immutable conversation history with resumable graph execution."""

    HISTORY_USER_MESSAGE_LIMIT = 10

    def __init__(self, repository: ConversationRepository, graph) -> None:
        self.repository = repository
        self.graph = graph

    async def conversation_detail(
        self, conversation_id: str, branch_id: str | None = None
    ) -> ConversationDetail:
        conversation = await self.repository.get_conversation(conversation_id)
        selected_branch = branch_id or conversation.active_branch_id
        return ConversationDetail(
            **conversation.model_dump(),
            branches=await self.repository.list_branches(conversation_id),
            messages=await self.repository.list_messages(
                conversation_id, selected_branch
            ),
        )

    async def chat(
        self, conversation_id: str, content: str, branch_id: str | None = None
    ) -> ChatResponse:
        with get_langfuse_client().start_as_current_observation(
            name="conversation-turn",
            as_type="span",
            input={
                "conversation_id": conversation_id,
                "requested_branch_id": branch_id,
                "message_characters": len(content),
                "content_recorded": False,
            },
        ) as observation:
            try:
                response = await self._run_chat(conversation_id, content, branch_id)
            except Exception:
                logger.exception(
                    "conversation_turn_failed",
                    extra={"conversation_id": conversation_id, "branch_id": branch_id},
                )
                observation.update(level="ERROR", output={"status": "failed"})
                raise
            output = {
                "branch_id": response.branch_id,
                "interrupted": response.interrupted,
                "interrupt_phase": response.interrupt_phase,
            }
            observation.update(output=output)
            logger.info(
                "conversation_turn_completed",
                extra={"conversation_id": conversation_id, **output},
            )
            return response

    async def chat_stream(
        self, conversation_id: str, content: str, branch_id: str | None = None
    ) -> AsyncIterator[str | ChatDelta | ChatResponse]:
        """Yield real-time status strings while the graph runs, then the ChatResponse."""
        conversation = await self.repository.get_conversation(conversation_id)
        selected_branch = branch_id or conversation.active_branch_id
        existing = await self.repository.list_messages(conversation_id, selected_branch)
        pending = self._pending_interrupt(existing)
        user_message = await self.repository.append_message(
            conversation_id,
            selected_branch,
            MessageRole.USER,
            content,
            metadata={"resumes_interrupt": bool(pending)},
        )

        if pending:
            thread_id = str(pending.metadata["graph_thread_id"])
            invoke_input: dict | Command = Command(resume=content)
        else:
            recent_users = [
                message
                for message in [*existing, user_message]
                if message.role is MessageRole.USER
            ][-self.HISTORY_USER_MESSAGE_LIMIT :]
            thread_id = f"{conversation_id}:{selected_branch}:{user_message.id}"
            invoke_input = {
                "request_id": user_message.id,
                "session_id": conversation_id,
                "query": content,
                "messages": [
                    HumanMessage(content=message.content, id=message.id)
                    for message in recent_users
                ],
            }

        config = graph_resume_config(thread_id)

        # Stream graph events; yield a status string whenever a node starts.
        result: dict = {}
        answer_streamed = False
        async for event in self.graph.astream_events(invoke_input, config, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")

            if kind == "on_chain_start" and name in _NODE_STATUS:
                yield _NODE_STATUS[name]

            if (
                kind == "on_chat_model_stream"
                and (
                    "answer_generation" in event.get("tags", [])
                    or event.get("metadata", {}).get("langgraph_node") == "answer"
                )
            ):
                chunk = event.get("data", {}).get("chunk")
                content = getattr(chunk, "content", chunk)
                if isinstance(content, list):
                    content = "".join(
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict)
                    )
                if content:
                    answer_streamed = True
                    yield ChatDelta(str(content))

            # Capture the final graph output when the top-level chain ends.
            if kind == "on_chain_end" and name == "LangGraph":
                output = event.get("data", {}).get("output", {})
                if isinstance(output, dict):
                    result = output

        interrupted, phase, response = self._graph_response(result)
        assistant_message = await self.repository.append_message(
            conversation_id,
            selected_branch,
            MessageRole.ASSISTANT,
            response,
            metadata={
                "awaiting_resume": interrupted,
                "interrupt_phase": phase,
                "graph_thread_id": thread_id,
                "reply_to_message_id": user_message.id,
            },
        )
        if not answer_streamed:
            for index in range(0, len(response), 48):
                yield ChatDelta(response[index : index + 48])
        yield ChatResponse(
            conversation_id=conversation_id,
            branch_id=selected_branch,
            user_message=user_message,
            assistant_message=assistant_message,
            interrupted=interrupted,
            interrupt_phase=phase,
        )

    async def _run_chat(
        self, conversation_id: str, content: str, branch_id: str | None
    ) -> ChatResponse:
        conversation = await self.repository.get_conversation(conversation_id)
        selected_branch = branch_id or conversation.active_branch_id
        existing = await self.repository.list_messages(conversation_id, selected_branch)
        pending = self._pending_interrupt(existing)
        user_message = await self.repository.append_message(
            conversation_id,
            selected_branch,
            MessageRole.USER,
            content,
            metadata={"resumes_interrupt": bool(pending)},
        )
        if pending:
            thread_id = str(pending.metadata["graph_thread_id"])
            result = await self.graph.ainvoke(
                Command(resume=content), graph_resume_config(thread_id)
            )
        else:
            recent_users = [
                message
                for message in [*existing, user_message]
                if message.role is MessageRole.USER
            ][-self.HISTORY_USER_MESSAGE_LIMIT :]
            thread_id = f"{conversation_id}:{selected_branch}:{user_message.id}"
            result = await self.graph.ainvoke(
                {
                    "request_id": user_message.id,
                    "session_id": conversation_id,
                    "query": content,
                    "messages": [
                        HumanMessage(content=message.content, id=message.id)
                        for message in recent_users
                    ],
                },
                graph_resume_config(thread_id),
            )
        interrupted, phase, response = self._graph_response(result)
        assistant_message = await self.repository.append_message(
            conversation_id,
            selected_branch,
            MessageRole.ASSISTANT,
            response,
            metadata={
                "awaiting_resume": interrupted,
                "interrupt_phase": phase,
                "graph_thread_id": thread_id,
                "reply_to_message_id": user_message.id,
            },
        )
        return ChatResponse(
            conversation_id=conversation_id,
            branch_id=selected_branch,
            user_message=user_message,
            assistant_message=assistant_message,
            interrupted=interrupted,
            interrupt_phase=phase,
        )

    async def edit_message(
        self,
        conversation_id: str,
        message_id: str,
        content: str,
        branch_name: str | None = None,
    ) -> tuple[Branch, Message]:
        branch, replacement = await self.repository.create_branch(
            conversation_id,
            message_id,
            name=branch_name,
            replace_content=content,
        )
        if replacement is None:
            raise RuntimeError("edited branch did not create a replacement message")
        return branch, replacement

    @staticmethod
    def _pending_interrupt(messages: list[Message]) -> Message | None:
        if not messages:
            return None
        latest = messages[-1]
        if latest.role is MessageRole.ASSISTANT and latest.metadata.get(
            "awaiting_resume"
        ):
            return latest
        return None

    @staticmethod
    def _graph_response(result: dict) -> tuple[bool, str | None, str]:
        interrupts = result.get("__interrupt__", [])
        if interrupts:
            payload = interrupts[0].value
            return True, payload.get("phase"), payload.get("message", "")
        response = str(result.get("response", "")).strip()
        if not response:
            raise RuntimeError("agent graph returned no response")
        return False, None, response
