from collections.abc import Awaitable, Callable
from typing import Any

from interview_prep_qna.core.agent.enums import InterrogationPhase
from interview_prep_qna.core.agent.state import AgentState
from interview_prep_qna.core.pipeline import ingest_document
from interview_prep_qna.observability import get_langfuse_client

IngestionPipeline = Callable[..., Awaitable[bool]]


class WriteBackNode:
    """Persist consented interrogator clarifications through the ingestion pipeline."""

    def __init__(self, ingestion_pipeline: IngestionPipeline = ingest_document) -> None:
        self._ingest = ingestion_pipeline

    async def __call__(self, state: AgentState) -> AgentState:
        session = dict(state.get("interrogation", {}))
        self._validate_session(session)
        query = (state.get("contextualized_query") or state.get("query", "")).strip()
        if not query:
            raise ValueError("state does not contain the original query")

        content = self._format_content(query, session["clarifications"])
        source_id = f"interrogation:{session['id']}"
        with get_langfuse_client().start_as_current_observation(
            name="write-back-user-clarification",
            as_type="span",
            input={
                "source_id": source_id,
                "clarification_count": len(session["clarifications"]),
                "content_characters": len(content),
                "content_recorded": False,
            },
        ) as observation:
            changed = await self._ingest(
                source_type="correction",
                source_id=source_id,
                title=f"User clarification: {query[:120]}",
                url=None,
                content=content,
            )
            observation.update(
                output={"status": "ingested" if changed else "unchanged"}
            )

        session["phase"] = InterrogationPhase.COMPLETE.value
        session["saved"] = True
        session["storage_changed"] = changed
        updated: AgentState = dict(state)
        updated["interrogation"] = session
        updated["write_back"] = {
            "source_type": "correction",
            "source_id": source_id,
            "changed": changed,
        }
        updated["route"] = "complete"
        updated["response"] = (
            "Information saved." if changed else "Information was already up to date."
        )
        return updated

    @staticmethod
    def _validate_session(session: dict[str, Any]) -> None:
        if session.get("phase") != InterrogationPhase.READY_TO_WRITE.value:
            raise ValueError("interrogation is not ready for write-back")
        if session.get("consent_granted") is not True:
            raise PermissionError("explicit consent is required for write-back")
        if not session.get("id"):
            raise ValueError("interrogation does not contain an id")
        if not session.get("clarifications"):
            raise ValueError("interrogation does not contain clarifications")

    @staticmethod
    def _format_content(query: str, clarifications: list[dict[str, Any]]) -> str:
        blocks = "\n\n".join(
            f"Question: {item['question']}\nAnswer: {item['answer']}"
            for item in clarifications
        )
        return f"Original query: {query}\n\n{blocks}"


async def write_back_node(state: AgentState) -> AgentState:
    """LangGraph-compatible entry point for approved knowledge write-back."""
    return await WriteBackNode()(state)
