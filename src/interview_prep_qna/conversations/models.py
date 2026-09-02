from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=200)


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    branch_id: str | None = None


class EditMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    branch_name: str | None = Field(default=None, max_length=200)


class BranchCreate(BaseModel):
    from_message_id: str
    name: str | None = Field(default=None, max_length=200)


class Message(BaseModel):
    id: str = Field(alias="_id")
    conversation_id: str
    branch_id: str
    parent_message_id: str | None = None
    origin_message_id: str | None = None
    role: MessageRole
    content: str
    sequence: int
    created_at: datetime
    edited_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class Branch(BaseModel):
    id: str = Field(alias="_id")
    conversation_id: str
    name: str
    parent_branch_id: str | None = None
    forked_from_message_id: str | None = None
    created_at: datetime

    model_config = {"populate_by_name": True}


class Conversation(BaseModel):
    id: str = Field(alias="_id")
    title: str
    active_branch_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class ConversationDetail(Conversation):
    branches: list[Branch]
    messages: list[Message]


class ChatResponse(BaseModel):
    conversation_id: str
    branch_id: str
    user_message: Message
    assistant_message: Message
    interrupted: bool = False
    interrupt_phase: str | None = None


class EditMessageResponse(BaseModel):
    branch: Branch
    message: Message
