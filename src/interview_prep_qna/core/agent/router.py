import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI

from interview_prep_qna.core.agent.decisions import RouterDecision
from interview_prep_qna.core.agent.enums import RouteDestination
from interview_prep_qna.core.agent.prompts import ROUTER_SYSTEM_PROMPT
from interview_prep_qna.core.agent.retrieval import RAGPipeline
from interview_prep_qna.core.agent.state import AgentState
from interview_prep_qna.core.config import get_settings
from interview_prep_qna.observability import get_langfuse_callbacks, get_langfuse_client

__all__ = ["RouteDestination", "RouterAgent", "RouterDecision"]
logger = logging.getLogger(__name__)


class RouterAgent:
    """Route contextualized queries to either RAG or the GenericAgent."""

    def __init__(
        self,
        model: BaseChatModel | None = None,
        router: Runnable[dict[str, Any], RouterDecision] | None = None,
        rag_pipeline: RAGPipeline | None = None,
    ) -> None:
        self._router = router or self._build_router(model)
        self._rag_pipeline = rag_pipeline or RAGPipeline()

    @staticmethod
    def _build_router(
        model: BaseChatModel | None,
    ) -> Runnable[dict[str, Any], RouterDecision]:
        if model is None:
            settings = get_settings()
            primary = ChatGoogleGenerativeAI(
                model=settings.google_flash_model,
                api_key=settings.google_genai_api_key,
                temperature=0,
                retries=2,
            ).with_structured_output(RouterDecision, method="json_schema")
            fallback = ChatGoogleGenerativeAI(
                model=settings.google_fallback_flash_model,
                api_key=settings.google_genai_api_key,
                temperature=0,
                retries=2,
            ).with_structured_output(RouterDecision, method="json_schema")
            structured_model = primary.with_fallbacks(
                [fallback], exceptions_to_handle=(Exception,)
            )
        else:
            structured_model = model.with_structured_output(
                RouterDecision, method="json_schema"
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", ROUTER_SYSTEM_PROMPT),
                MessagesPlaceholder("history", optional=True),
                ("human", "<USER_QUERY>\n{query}\n</USER_QUERY>"),
            ]
        )
        return prompt | structured_model

    async def route(
        self, query: str, history: list[BaseMessage] | None = None
    ) -> RouterDecision:
        if not query.strip():
            raise ValueError("query must not be empty")
        with get_langfuse_client().start_as_current_observation(
            name="route-query",
            as_type="generation",
            input={"query_characters": len(query), "history_count": len(history or [])},
            model=get_settings().google_flash_model,
        ) as observation:
            try:
                result = await self._router.ainvoke(
                    {"query": query.strip(), "history": history or []},
                    config={"callbacks": get_langfuse_callbacks()},
                )
                decision = RouterDecision.model_validate(result)
            except Exception:
                logger.exception("query_routing_failed")
                observation.update(level="ERROR", output={"status": "failed"})
                raise
            observation.update(output={"destination": decision.destination.value})
            logger.info(
                "query_routed", extra={"destination": decision.destination.value}
            )
            return decision

    async def route_and_run(
        self,
        query: str,
        history: list[BaseMessage] | None = None,
        state: AgentState | None = None,
    ) -> AgentState:
        """Route the query and execute RAG immediately when selected."""
        decision = await self.route(query, history)
        updated: AgentState = dict(state or {})
        updated["query"] = updated.get("query", query)
        updated["routing"] = decision.model_dump(mode="python")
        updated["current_agent"] = "router"
        updated["route"] = decision.destination.value
        if decision.use_rag:
            return await self._rag_pipeline.run(query, updated)
        return updated
