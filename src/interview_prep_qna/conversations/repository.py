import logging
from datetime import UTC, datetime
from uuid import uuid4

from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase

from interview_prep_qna.conversations.models import (
    Branch,
    Conversation,
    Message,
    MessageRole,
)

logger = logging.getLogger(__name__)


class ConversationNotFoundError(LookupError):
    pass


class MessageNotFoundError(LookupError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


class ConversationRepository:
    def __init__(self, database: AsyncDatabase) -> None:
        self.conversations = database["conversations"]
        self.branches = database["conversation_branches"]
        self.messages = database["conversation_messages"]
        self._indexes_ready = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ready:
            return
        await self.conversations.create_index([("updated_at", DESCENDING)])
        await self.branches.create_index([("conversation_id", ASCENDING)])
        await self.messages.create_index(
            [("conversation_id", ASCENDING), ("branch_id", ASCENDING), ("sequence", ASCENDING)],
            unique=True,
        )
        self._indexes_ready = True

    async def create_conversation(self, title: str) -> Conversation:
        now = _now()
        conversation_id = uuid4().hex
        branch_id = uuid4().hex
        conversation = {
            "_id": conversation_id,
            "title": title.strip(),
            "active_branch_id": branch_id,
            "created_at": now,
            "updated_at": now,
        }
        branch = {
            "_id": branch_id,
            "conversation_id": conversation_id,
            "name": "Main",
            "parent_branch_id": None,
            "forked_from_message_id": None,
            "created_at": now,
            "next_sequence": 1,
        }
        await self.conversations.insert_one(conversation)
        await self.branches.insert_one(branch)
        logger.info(
            "conversation_created",
            extra={"conversation_id": conversation_id, "branch_id": branch_id},
        )
        return Conversation.model_validate(conversation)

    async def list_conversations(self, limit: int, offset: int) -> list[Conversation]:
        cursor = (
            self.conversations.find({})
            .sort("updated_at", DESCENDING)
            .skip(offset)
            .limit(limit)
        )
        return [Conversation.model_validate(item) async for item in cursor]

    async def get_conversation(self, conversation_id: str) -> Conversation:
        item = await self.conversations.find_one({"_id": conversation_id})
        if not item:
            raise ConversationNotFoundError(conversation_id)
        return Conversation.model_validate(item)

    async def rename_conversation(self, conversation_id: str, title: str) -> Conversation:
        item = await self.conversations.find_one_and_update(
            {"_id": conversation_id},
            {"$set": {"title": title.strip(), "updated_at": _now()}},
            return_document=ReturnDocument.AFTER,
        )
        if not item:
            raise ConversationNotFoundError(conversation_id)
        return Conversation.model_validate(item)

    async def delete_conversation(self, conversation_id: str) -> None:
        result = await self.conversations.delete_one({"_id": conversation_id})
        if result.deleted_count == 0:
            raise ConversationNotFoundError(conversation_id)
        await self.branches.delete_many({"conversation_id": conversation_id})
        await self.messages.delete_many({"conversation_id": conversation_id})
        logger.info(
            "conversation_deleted", extra={"conversation_id": conversation_id}
        )

    async def list_branches(self, conversation_id: str) -> list[Branch]:
        cursor = self.branches.find({"conversation_id": conversation_id}).sort(
            "created_at", ASCENDING
        )
        return [Branch.model_validate(item) async for item in cursor]

    async def list_messages(
        self, conversation_id: str, branch_id: str
    ) -> list[Message]:
        cursor = self.messages.find(
            {"conversation_id": conversation_id, "branch_id": branch_id}
        ).sort("sequence", ASCENDING)
        return [Message.model_validate(item) async for item in cursor]

    async def get_message(self, conversation_id: str, message_id: str) -> Message:
        item = await self.messages.find_one(
            {"_id": message_id, "conversation_id": conversation_id}
        )
        if not item:
            raise MessageNotFoundError(message_id)
        return Message.model_validate(item)

    async def append_message(
        self,
        conversation_id: str,
        branch_id: str,
        role: MessageRole,
        content: str,
        *,
        metadata: dict | None = None,
        edited_at: datetime | None = None,
        origin_message_id: str | None = None,
    ) -> Message:
        branch = await self.branches.find_one_and_update(
            {"_id": branch_id, "conversation_id": conversation_id},
            {"$inc": {"next_sequence": 1}},
            return_document=ReturnDocument.BEFORE,
        )
        if not branch:
            raise ConversationNotFoundError(conversation_id)
        sequence = branch["next_sequence"]
        parent = await self.messages.find_one(
            {"conversation_id": conversation_id, "branch_id": branch_id},
            sort=[("sequence", DESCENDING)],
        )
        item = {
            "_id": uuid4().hex,
            "conversation_id": conversation_id,
            "branch_id": branch_id,
            "parent_message_id": parent["_id"] if parent else None,
            "origin_message_id": origin_message_id,
            "role": role.value,
            "content": content.strip(),
            "sequence": sequence,
            "created_at": _now(),
            "edited_at": edited_at,
            "metadata": metadata or {},
        }
        await self.messages.insert_one(item)
        await self.conversations.update_one(
            {"_id": conversation_id},
            {"$set": {"active_branch_id": branch_id, "updated_at": _now()}},
        )
        logger.debug(
            "conversation_message_stored",
            extra={
                "conversation_id": conversation_id,
                "branch_id": branch_id,
                "message_id": item["_id"],
                "role": role.value,
                "sequence": sequence,
                "content_characters": len(content),
            },
        )
        return Message.model_validate(item)

    async def create_branch(
        self,
        conversation_id: str,
        from_message_id: str,
        *,
        name: str | None = None,
        replace_content: str | None = None,
    ) -> tuple[Branch, Message | None]:
        source = await self.get_message(conversation_id, from_message_id)
        source_messages = await self.list_messages(conversation_id, source.branch_id)
        include_sequence = source.sequence - (1 if replace_content is not None else 0)
        prefix = [item for item in source_messages if item.sequence <= include_sequence]
        now = _now()
        branch_id = uuid4().hex
        branch_doc = {
            "_id": branch_id,
            "conversation_id": conversation_id,
            "name": name or f"Branch from message {source.sequence}",
            "parent_branch_id": source.branch_id,
            "forked_from_message_id": source.id,
            "created_at": now,
            "next_sequence": 1,
        }
        await self.branches.insert_one(branch_doc)
        for item in prefix:
            await self.append_message(
                conversation_id,
                branch_id,
                item.role,
                item.content,
                metadata=item.metadata,
                edited_at=item.edited_at,
                origin_message_id=item.origin_message_id or item.id,
            )
        replacement = None
        if replace_content is not None:
            replacement = await self.append_message(
                conversation_id,
                branch_id,
                source.role,
                replace_content,
                edited_at=now,
                origin_message_id=source.id,
                metadata={"edited_from_message_id": source.id},
            )
        await self.conversations.update_one(
            {"_id": conversation_id},
            {"$set": {"active_branch_id": branch_id, "updated_at": now}},
        )
        logger.info(
            "conversation_branch_created",
            extra={
                "conversation_id": conversation_id,
                "branch_id": branch_id,
                "parent_branch_id": source.branch_id,
                "edited": replace_content is not None,
            },
        )
        return Branch.model_validate(branch_doc), replacement
