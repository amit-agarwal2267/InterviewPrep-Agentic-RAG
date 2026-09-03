import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI

from interview_prep_qna.core.agent.prompts import GENERIC_SYSTEM_PROMPT
from interview_prep_qna.core.agent.state import AgentState
from interview_prep_qna.core.agent.summarizer import SummarizerAgent
from interview_prep_qna.core.config import get_settings
from interview_prep_qna.observability import get_langfuse_callbacks, get_langfuse_client

logger = logging.getLogger(__name__)


def _content_text(result: Any) -> str:
    content = result.content if hasattr(result, "content") else result
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    if isinstance(content, dict) and content.get("type") == "text":
        return str(content.get("text", ""))
    return str(content)


class GenericAgent:
    def __init__(
        self,
        model: BaseChatModel | None = None,
        responder: Runnable[dict[str, Any], Any] | None = None,
        summarizer: SummarizerAgent | None = None,
    ) -> None:
        self._responder = responder or self._build_responder(model)
        self._summarizer = summarizer or SummarizerAgent()

    @staticmethod
    def _build_responder(model: BaseChatModel | None) -> Runnable:
        if model is None:
            settings = get_settings()
            primary = ChatGoogleGenerativeAI(
                model=settings.google_flash_model,
                api_key=settings.google_genai_api_key,
                temperature=0.2,
                retries=2,
            )
            fallback = ChatGoogleGenerativeAI(
                model=settings.google_fallback_flash_model,
                api_key=settings.google_genai_api_key,
                temperature=0.2,
                retries=2,
            )
            model = primary.with_fallbacks(
                [fallback], exceptions_to_handle=(Exception,)
            )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", GENERIC_SYSTEM_PROMPT),
                (
                    "human",
                    (
                        "<USER_QUERY>\n{query}\n</USER_QUERY>\n"
                        "<FALLBACK_REASON>\n{reason}\n</FALLBACK_REASON>\n"
                        "<GENERIC_WEB_CONTEXT>\n{context}\n</GENERIC_WEB_CONTEXT>"
                    ),
                ),
            ]
        )
        return prompt | model

    async def respond(self, query: str, reason: str, context: str = "") -> str:
        with get_langfuse_client().start_as_current_observation(
            name="generate-generic-answer",
            as_type="generation",
            input={
                "query_characters": len(query),
                "context_characters": len(context),
                "fallback_reason": reason,
            },
            model=get_settings().google_flash_model,
        ) as observation:
            try:
                result = await self._responder.ainvoke(
                    {"query": query, "reason": reason, "context": context},
                    config={"callbacks": get_langfuse_callbacks()},
                )
                response = _content_text(result).strip()
            except Exception:
                logger.exception("generic_answer_generation_failed")
                observation.update(level="ERROR", output={"status": "failed"})
                raise
            observation.update(output={"response_characters": len(response)})
            logger.info(
                "generic_answer_generated",
                extra={"response_characters": len(response)},
            )
            return response

    async def respond_state(self, state: AgentState, reason: str) -> AgentState:
        """Generate and summarize a generic answer for non-graph callers."""
        updated = await self.generate_state(state, reason)
        summarized = await self._summarizer.summarize_state(updated)
        if summarized.get("route") == "summarizer":
            summarized["route"] = "generic"
        return summarized

    async def generate_state(self, state: AgentState, reason: str) -> AgentState:
        """Generate the generic draft without advancing to another graph node."""
        query = state.get("contextualized_query") or state.get("query")
        if not query:
            raise ValueError("state does not contain a query")
        generic_web_evidence = [
            item
            for item in state.get("retrieved_evidence", [])
            if item.source_type == "web" and item.metadata.get("generic_external")
        ]
        context = "\n\n".join(
            f"Source: {item.title or item.url}\n{item.content[:3000]}"
            for item in generic_web_evidence
        )
        updated: AgentState = dict(state)
        updated["route"] = "generic"
        response = await self.respond(query, reason, context)
        if generic_web_evidence and not response.lower().startswith("generic answer"):
            response = (
                "Generic answer — not verified from your project records: " + response
            )
        updated["response"] = response
        updated["current_agent"] = "generic"
        updated["route"] = "summarizer"
        return updated
