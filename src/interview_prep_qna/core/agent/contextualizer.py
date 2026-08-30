import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI

from interview_prep_qna.core.agent.decisions import ContextualizerDecision
from interview_prep_qna.core.agent.enums import QueryRoute
from interview_prep_qna.core.agent.prompts import CONTEXTUALIZER_SYSTEM_PROMPT
from interview_prep_qna.core.agent.state import AgentState
from interview_prep_qna.core.config import get_settings
from interview_prep_qna.observability import get_langfuse_client

__all__ = ["ContextualizerAgent", "ContextualizerDecision", "QueryRoute"]
logger = logging.getLogger(__name__)


class ContextualizerAgent:
    """Classify and rewrite a query before retrieval or agent routing."""

    def __init__(
        self,
        model: BaseChatModel | None = None,
        classifier: Runnable[dict[str, Any], ContextualizerDecision] | None = None,
    ) -> None:
        self._classifier = classifier or self._build_classifier(model)

    @staticmethod
    def _build_classifier(
        model: BaseChatModel | None,
    ) -> Runnable[dict[str, Any], ContextualizerDecision]:
        if model is None:
            settings = get_settings()
            primary_model = ChatGoogleGenerativeAI(
                model=settings.google_flash_model,
                api_key=settings.google_genai_api_key,
                temperature=0,
                retries=0,
            ).with_structured_output(ContextualizerDecision, method="json_schema")
            fallback_model = ChatGoogleGenerativeAI(
                model=settings.google_fallback_flash_model,
                api_key=settings.google_genai_api_key,
                temperature=0,
                retries=0,
            ).with_structured_output(ContextualizerDecision, method="json_schema")
            structured_model = primary_model.with_fallbacks(
                [fallback_model],
                exceptions_to_handle=(Exception,),
            )
        else:
            structured_model = model.with_structured_output(
                ContextualizerDecision, method="json_schema"
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CONTEXTUALIZER_SYSTEM_PROMPT),
                MessagesPlaceholder("history", optional=True),
                ("human", "<USER_QUERY>\n{query}\n</USER_QUERY>"),
            ]
        )
        return prompt | structured_model

    async def aclassify(
        self, query: str, history: list[BaseMessage] | None = None
    ) -> ContextualizerDecision:
        if not query.strip():
            raise ValueError("query must not be empty")
        with get_langfuse_client().start_as_current_observation(
            name="contextualize-query",
            as_type="generation",
            input={"query_characters": len(query), "history_count": len(history or [])},
            model=get_settings().google_flash_model,
        ) as observation:
            try:
                result = await self._classifier.ainvoke(
                    {"query": query.strip(), "history": history or []}
                )
                decision = ContextualizerDecision.model_validate(result)
            except Exception:
                logger.exception("contextualization_failed")
                observation.update(level="ERROR", output={"status": "failed"})
                raise
            output = {"route": decision.route.value, "rewritten": bool(decision.standalone_query)}
            observation.update(output=output)
            logger.info("query_contextualized", extra=output)
            return decision

    async def classify_state(self, state: AgentState) -> AgentState:
        """Classify the query and preserve the decision in shared graph state."""
        query = state.get("query")
        if not query:
            raise ValueError("state does not contain a query")
        decision = await self.aclassify(query, state.get("messages"))
        updated: AgentState = dict(state)
        updated["contextualization"] = decision.model_dump(mode="python")
        updated["current_agent"] = "contextualizer"
        if decision.standalone_query:
            updated["contextualized_query"] = decision.standalone_query
        if decision.direct_response:
            updated["response"] = decision.direct_response
        return updated

    def classify(
        self, query: str, history: list[BaseMessage] | None = None
    ) -> ContextualizerDecision:
        if not query.strip():
            raise ValueError("query must not be empty")
        result = self._classifier.invoke(
            {"query": query.strip(), "history": history or []}
        )
        return ContextualizerDecision.model_validate(result)
