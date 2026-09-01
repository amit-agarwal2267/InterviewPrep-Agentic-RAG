from typing import Any
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq

from interview_prep_qna.core.agent.decisions import InterrogationDecision
from interview_prep_qna.core.agent.enums import InterrogationPhase
from interview_prep_qna.core.agent.prompts import INTERROGATOR_SYSTEM_PROMPT
from interview_prep_qna.core.agent.state import AgentState
from interview_prep_qna.core.config import get_settings
from interview_prep_qna.observability import get_langfuse_client


class InterrogatorAgent:
    """Collect at most two clarifications and explicit persistence consent."""

    MAX_QUESTIONS = 2
    CONSENT_PROMPT = "May I store your clarification in the knowledge base? (yes/no)"

    def __init__(
        self,
        model: BaseChatModel | None = None,
        interrogator: Runnable[dict[str, Any], InterrogationDecision] | None = None,
    ) -> None:
        self._model = model
        self._interrogator = interrogator

    @property
    def interrogator(self) -> Runnable[dict[str, Any], InterrogationDecision]:
        if self._interrogator is None:
            self._interrogator = self._build_interrogator(self._model)
        return self._interrogator

    @staticmethod
    def _build_interrogator(
        model: BaseChatModel | None,
    ) -> Runnable[dict[str, Any], InterrogationDecision]:
        if model is None:
            settings = get_settings()
            if not settings.groq_api_key:
                raise ValueError("GROQ_API_KEY is required for InterrogatorAgent")
            primary = ChatGroq(
                model=settings.groq_model,
                api_key=settings.groq_api_key,
                temperature=0,
                max_retries=0,
                timeout=45,
            ).with_structured_output(InterrogationDecision, method="json_schema")
            fallback = ChatGroq(
                model=settings.groq_fallback_model,
                api_key=settings.groq_api_key,
                temperature=0,
                max_retries=0,
                timeout=45,
            ).with_structured_output(InterrogationDecision, method="json_schema")
            structured_model = primary.with_fallbacks(
                [fallback], exceptions_to_handle=(Exception,)
            )
        else:
            structured_model = model.with_structured_output(
                InterrogationDecision, method="json_schema"
            )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", INTERROGATOR_SYSTEM_PROMPT),
                (
                    "human",
                    """<QUERY>{query}</QUERY>
<GAP>{gap}</GAP>
<CANDIDATE_QUESTIONS>{candidates}</CANDIDATE_QUESTIONS>
<PRIOR_CLARIFICATIONS>{clarifications}</PRIOR_CLARIFICATIONS>
<LATEST_REPLY>{reply}</LATEST_REPLY>""",
                ),
            ]
        )
        return prompt | structured_model

    async def start(self, state: AgentState) -> AgentState:
        """Show the summarized answer and append the first clarification question."""
        draft = state.get("draft_response")
        gap = state.get("knowledge_gap", {})
        questions = gap.get("questions", [])
        if not draft:
            raise ValueError("state does not contain the summarizer draft")
        if not questions:
            raise ValueError("state does not contain a follow-up question")

        question = str(questions[0]).strip()
        updated: AgentState = dict(state)
        updated["route"] = "interrogator"
        updated["interrogation"] = {
            "id": uuid4().hex,
            "phase": InterrogationPhase.AWAITING_ANSWER.value,
            "questions_asked": [question],
            "clarifications": [],
            "satisfied": False,
            "saved": False,
        }
        updated["response"] = f"{draft.rstrip()}\n\n---\n\n{question}"
        return updated

    async def handle_reply(self, state: AgentState, reply: str) -> AgentState:
        """Resume an interrogation with either an answer or explicit consent."""
        if not reply.strip():
            raise ValueError("reply must not be empty")
        session = dict(state.get("interrogation", {}))
        phase = session.get("phase")
        if phase == InterrogationPhase.AWAITING_ANSWER.value:
            return await self._handle_clarification(state, session, reply.strip())
        if phase == InterrogationPhase.AWAITING_CONSENT.value:
            return await self._handle_consent(state, session, reply.strip())
        raise ValueError("state does not contain an active interrogation")

    async def _handle_clarification(
        self, state: AgentState, session: dict[str, Any], reply: str
    ) -> AgentState:
        questions = list(session.get("questions_asked", []))
        clarifications = list(session.get("clarifications", []))
        clarifications.append({"question": questions[-1], "answer": reply})
        gap = state.get("knowledge_gap", {})

        with get_langfuse_client().start_as_current_observation(
            name="interrogate-knowledge-gap",
            as_type="evaluator",
            input={"question_number": len(questions), "reply_characters": len(reply)},
        ) as observation:
            result = await self.interrogator.ainvoke(
                {
                    "query": state.get("contextualized_query") or state.get("query", ""),
                    "gap": gap.get("reason", "Unspecified project-knowledge gap"),
                    "candidates": gap.get("questions", []),
                    "clarifications": clarifications[:-1],
                    "reply": reply,
                }
            )
            decision = InterrogationDecision.model_validate(result)
            observation.update(output=decision.model_dump(mode="json"))

        updated: AgentState = dict(state)
        session["clarifications"] = clarifications
        session["satisfied"] = decision.satisfied
        if decision.satisfied or len(questions) >= self.MAX_QUESTIONS:
            session["phase"] = InterrogationPhase.AWAITING_CONSENT.value
            updated["response"] = self.CONSENT_PROMPT
        else:
            next_question = decision.next_question.strip()
            questions.append(next_question)
            session["questions_asked"] = questions
            updated["response"] = next_question
        updated["interrogation"] = session
        return updated

    async def _handle_consent(
        self, state: AgentState, session: dict[str, Any], reply: str
    ) -> AgentState:
        consent = self._parse_consent(reply)
        updated: AgentState = dict(state)
        if consent is None:
            updated["response"] = f"Please answer yes or no. {self.CONSENT_PROMPT}"
            return updated

        if not consent:
            session["phase"] = InterrogationPhase.COMPLETE.value
            session["consent_granted"] = False
            session["saved"] = False
            updated["route"] = "complete"
            updated["interrogation"] = session
            updated["response"] = "No Information saved."
            return updated

        session["phase"] = InterrogationPhase.READY_TO_WRITE.value
        session["consent_granted"] = True
        updated["interrogation"] = session
        updated["route"] = "write_back"
        updated["response"] = "Saving your clarification to the knowledge base."
        return updated

    @staticmethod
    def _parse_consent(reply: str) -> bool | None:
        normalized = reply.strip().lower().rstrip(".! ")
        if normalized in {"yes", "y", "yes, save it", "save it", "allow"}:
            return True
        if normalized in {"no", "n", "no, don't save it", "do not save", "deny"}:
            return False
        return None
