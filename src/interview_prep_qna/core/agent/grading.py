from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
# from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from interview_prep_qna.core.agent.answer import AnswerAgent
from interview_prep_qna.core.agent.decisions import GradingDecision
from interview_prep_qna.core.agent.enums import GradingAction
from interview_prep_qna.core.agent.escalation.github_live import GitHubLiveAgent
from interview_prep_qna.core.agent.escalation.web_search import WebSearchAgent
from interview_prep_qna.core.agent.generic import GenericAgent
from interview_prep_qna.core.agent.prompts import GRADING_SYSTEM_PROMPT
from interview_prep_qna.core.agent.state import AgentState, RetrievedEvidence
from interview_prep_qna.core.config import get_settings
from interview_prep_qna.observability import get_langfuse_callbacks, get_langfuse_client


class GradingAgent:
    """Grade RAG evidence and control bounded GitHub/web escalation."""

    def __init__(
        self,
        model: BaseChatModel | None = None,
        grader: Runnable[dict[str, Any], GradingDecision] | None = None,
        github_agent: GitHubLiveAgent | None = None,
        web_agent: WebSearchAgent | None = None,
        generic_agent: GenericAgent | None = None,
        answer_agent: AnswerAgent | None = None,
    ) -> None:
        self._grader = grader or self._build_grader(model)
        self._github = github_agent or GitHubLiveAgent()
        self._web = web_agent or WebSearchAgent()
        self._generic = generic_agent or GenericAgent()
        self._answer = answer_agent or AnswerAgent()

    @staticmethod
    def _build_grader(
        model: BaseChatModel | None,
    ) -> Runnable[dict[str, Any], GradingDecision]:
        if model is None:
            settings = get_settings()
            # primary = ChatGroq(
            #     model=settings.groq_model,
            #     api_key=settings.groq_api_key,
            #     temperature=0,
            #     max_tokens=500,
            #     max_retries=0,
            #     timeout=45,
            # )
            primary = ChatGoogleGenerativeAI(
                model=settings.google_flash_model,
                api_key=settings.google_genai_api_key,
                temperature=0,
                max_tokens=1000,
                retries=2,
            ).with_structured_output(GradingDecision, method="json_schema")
            fallback = ChatGoogleGenerativeAI(
                model=settings.google_fallback_flash_model,
                api_key=settings.google_genai_api_key,
                temperature=0,
                max_tokens=1000,
                retries=2,
            ).with_structured_output(GradingDecision, method="json_schema")
            structured_model = primary.with_fallbacks(
                [fallback], exceptions_to_handle=(Exception,)
            )
        else:
            structured_model = model.with_structured_output(
                GradingDecision, method="json_schema"
            )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", GRADING_SYSTEM_PROMPT),
                (
                    "human",
                    (
                        "<STAGE>{stage}</STAGE>\n"
                        "<AVAILABLE_ACTIONS>{available_actions}</AVAILABLE_ACTIONS>\n"
                        "<USER_QUERY>\n{query}\n</USER_QUERY>\n"
                        "<EVIDENCE>\n{evidence}\n</EVIDENCE>"
                    ),
                ),
            ]
        )
        return prompt | structured_model

    @staticmethod
    def _format_evidence(evidence: list[RetrievedEvidence]) -> str:
        if not evidence:
            return "No evidence was retrieved."
        return "\n\n".join(
            f"[Evidence {index}]\nsource_type: {item.source_type}\n"
            f"title: {item.title or 'Untitled'}\nurl: {item.url or 'Unavailable'}\n"
            f"content:\n{item.content[:4000]}"
            for index, item in enumerate(evidence, start=1)
        )

    async def grade(
        self,
        query: str,
        evidence: list[RetrievedEvidence],
        *,
        stage: str = "rag",
        available_actions: tuple[GradingAction, ...] = tuple(GradingAction),
    ) -> GradingDecision:
        if not query.strip():
            raise ValueError("query must not be empty")
        with get_langfuse_client().start_as_current_observation(
            name="grade-evidence",
            as_type="evaluator",
            input={"stage": stage, "evidence_count": len(evidence)},
        ) as observation:
            result = await self._grader.ainvoke(
                {
                    "query": query.strip(),
                    "evidence": self._format_evidence(evidence),
                    "stage": stage,
                    "available_actions": ", ".join(available_actions),
                },
                config={"callbacks": get_langfuse_callbacks()},
            )
            decision = GradingDecision.model_validate(result)
            if decision.action not in available_actions:
                decision = GradingDecision(
                    action=GradingAction.GENERIC,
                    sufficient=False,
                    reason=f"Invalid repeated action at {stage}: {decision.action}",
                    missing_information=decision.missing_information,
                )
            observation.update(output=decision.model_dump(mode="json"))
            return decision

    async def grade_state(self, state: AgentState) -> AgentState:
        query = state.get("contextualized_query") or state.get("query")
        if not query:
            raise ValueError("state does not contain a query")
        decision = await self.grade(query, state.get("retrieved_evidence", []))
        updated: AgentState = dict(state)
        updated["grading"] = decision.model_dump(mode="python")
        return updated

    async def resolve(self, state: AgentState) -> AgentState:
        """Run RAG grading and each live escalation at most once."""
        query = state.get("contextualized_query") or state.get("query")
        if not query:
            raise ValueError("state does not contain a query")
        updated: AgentState = dict(state)
        evidence = list(updated.get("retrieved_evidence", []))
        steps = list(updated.get("escalation_steps", []))
        github_done = False
        web_done = False
        stage = "rag"

        while True:
            available = [GradingAction.ANSWER, GradingAction.GENERIC]
            if not github_done:
                available.append(GradingAction.GITHUB)
            if not web_done and github_done and get_settings().tavily_api_key is not None:
                available.append(GradingAction.WEB)
            decision = await self.grade(
                query, evidence, stage=stage, available_actions=tuple(available)
            )
            updated["grading"] = decision.model_dump(mode="python")
            if decision.action is GradingAction.ANSWER:
                updated["retrieved_evidence"] = evidence
                updated["escalation_steps"] = steps
                return await self._answer.answer_state(updated)

            if decision.action is GradingAction.GITHUB and not github_done:
                github_done = True
                stage = "github"
                found, error = await self._search_safely(
                    self._github.search, query, decision.missing_information
                )
                evidence.extend(found)
                steps.append(
                    {"source": "github", "results": len(found), "error": error}
                )
                continue

            if decision.action is GradingAction.WEB and not web_done:
                web_done = True
                stage = "web"
                found, error = await self._search_safely(
                    self._web.search, query, decision.missing_information
                )
                evidence.extend(found)
                steps.append({"source": "web", "results": len(found), "error": error})
                continue

            updated["retrieved_evidence"] = evidence
            updated["escalation_steps"] = steps
            return await self._generic.respond_state(updated, decision.reason)

    @staticmethod
    async def _search_safely(search, query: str, missing: list[str]):
        try:
            return await search(query, missing), None
        except Exception as exc:
            return [], f"{type(exc).__name__}: {exc}"
