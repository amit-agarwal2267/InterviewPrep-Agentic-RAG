import json
import logging
from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse

from interview_prep_qna.conversations.client import get_conversation_database
from interview_prep_qna.conversations.models import (
    Branch,
    BranchCreate,
    ChatRequest,
    Conversation,
    ConversationCreate,
    ConversationDetail,
    ConversationUpdate,
    EditMessageRequest,
    EditMessageResponse,
)
from interview_prep_qna.conversations.repository import (
    ConversationNotFoundError,
    ConversationRepository,
    MessageNotFoundError,
)
from interview_prep_qna.conversations.service import ChatDelta, ConversationService
from interview_prep_qna.core.agent.graph import build_agent_graph

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)


def _is_rate_limit_error(error: Exception) -> bool:
    current: BaseException | None = error
    while current is not None:
        status_code = getattr(current, "status_code", None)
        response = getattr(current, "response", None)
        if status_code == 429 or getattr(response, "status_code", None) == 429:
            return True
        message = str(current).lower()
        if "429" in message or "rate limit" in message or "resource exhausted" in message:
            return True
        current = current.__cause__ or current.__context__
    return False


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@lru_cache(maxsize=1)
def get_conversation_service() -> ConversationService:
    repository = ConversationRepository(get_conversation_database())
    return ConversationService(repository, build_agent_graph())


async def conversation_service_dependency() -> ConversationService:
    service = get_conversation_service()
    await service.repository.ensure_indexes()
    return service


Service = Depends(conversation_service_dependency)




@router.post("", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate, service: ConversationService = Service
) -> Conversation:
    return await service.repository.create_conversation(payload.title)


@router.get("", response_model=list[Conversation])
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ConversationService = Service,
) -> list[Conversation]:
    return await service.repository.list_conversations(limit, offset)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    branch_id: str | None = None,
    service: ConversationService = Service,
) -> ConversationDetail:
    try:
        return await service.conversation_detail(conversation_id, branch_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc


@router.patch("/{conversation_id}", response_model=Conversation)
async def rename_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    service: ConversationService = Service,
) -> Conversation:
    try:
        return await service.repository.rename_conversation(
            conversation_id, payload.title
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str, service: ConversationService = Service
) -> Response:
    try:
        await service.repository.delete_conversation(conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{conversation_id}/chat")
async def chat(
    conversation_id: str,
    payload: ChatRequest,
    service: ConversationService = Service,
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        try:
            async for item in service.chat_stream(
                conversation_id, payload.content, payload.branch_id
            ):
                if isinstance(item, str):
                    # Real-time status emitted as a node starts in the graph.
                    yield _sse({"type": "status", "message": item})
                elif isinstance(item, ChatDelta):
                    yield _sse({"type": "delta", "content": item.content})
                else:
                    # Final ChatResponse; answer tokens were emitted by the service.
                    result = item
                    yield _sse(
                        {
                            "type": "done",
                            "response": result.model_dump(mode="json", by_alias=False),
                        }
                    )
        except ConversationNotFoundError:
            yield _sse(
                {"type": "error", "status": 404, "detail": "Conversation or branch not found"}
            )
        except Exception as exc:
            if _is_rate_limit_error(exc):
                logger.warning("chat_model_rate_limited", exc_info=True)
                yield _sse(
                    {
                        "type": "error",
                        "status": 429,
                        "detail": "The AI service is temporarily rate-limited. Please try again in a moment.",
                    }
                )
                return
            logger.exception("chat_stream_failed")
            yield _sse(
                {"type": "error", "status": 500, "detail": "Chat request failed"}
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{conversation_id}/branches", response_model=Branch)
async def create_branch(
    conversation_id: str,
    payload: BranchCreate,
    service: ConversationService = Service,
) -> Branch:
    try:
        branch, _ = await service.repository.create_branch(
            conversation_id, payload.from_message_id, name=payload.name
        )
        return branch
    except (ConversationNotFoundError, MessageNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="Conversation or message not found") from exc


@router.post(
    "/{conversation_id}/messages/{message_id}/edit",
    response_model=EditMessageResponse,
)
async def edit_message(
    conversation_id: str,
    message_id: str,
    payload: EditMessageRequest,
    service: ConversationService = Service,
) -> EditMessageResponse:
    try:
        branch, message = await service.edit_message(
            conversation_id, message_id, payload.content, payload.branch_name
        )
        return EditMessageResponse(branch=branch, message=message)
    except (ConversationNotFoundError, MessageNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="Conversation or message not found") from exc


@router.get("/{conversation_id}/messages/{message_id}/markdown")
async def copy_message_as_markdown(
    conversation_id: str,
    message_id: str,
    service: ConversationService = Service,
) -> Response:
    try:
        message = await service.repository.get_message(conversation_id, message_id)
    except MessageNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Message not found") from exc
    return Response(
        content=message.content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'inline; filename="message-{message.id}.md"'},
    )
