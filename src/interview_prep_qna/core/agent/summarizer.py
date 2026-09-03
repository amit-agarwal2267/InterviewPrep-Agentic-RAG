import re
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
# from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from interview_prep_qna.core.agent.decisions import SummarizerDecision
from interview_prep_qna.core.agent.enums import GroundingAlignment
from interview_prep_qna.core.agent.prompts import SUMMARIZER_SYSTEM_PROMPT
from interview_prep_qna.core.agent.state import AgentState
from interview_prep_qna.core.config import get_settings
from interview_prep_qna.observability import get_langfuse_callbacks, get_langfuse_client

_LATEX_MACROS = {
    r"\\rightarrow": "→",
    r"\\Rightarrow": "⇒",
    r"\\leftarrow": "←",
    r"\\Leftarrow": "⇐",
    r"\\leftrightarrow": "↔",
    r"\\to\b": "→",
    r"\\times": "×",
    r"\\cdot": "·",
    r"\\le\b": "≤",
    r"\\ge\b": "≥",
    r"\\neq": "≠",
    r"\\approx": "≈",
    r"\\infty": "∞",
    r"\\pm": "±",
}
_MATH_GLYPHS = "→⇒←⇐↔×·≤≥≠≈∞±"


def _strip_unsupported_latex(text: str) -> str:
    """Replace LaTeX math the chat UI cannot render with plain Unicode.

    The frontend only loads remark-gfm (no remark-math/rehype-katex), so raw
    LaTeX such as ``$\\rightarrow$`` would render as literal text instead of
    an arrow. Convert known macros to their Unicode equivalent, then drop
    now-redundant `$...$` / `\\(...\\)` delimiters that only wrap them.
    """
    for pattern, glyph in _LATEX_MACROS.items():
        text = re.sub(pattern, glyph, text)

    def _unwrap(match: "re.Match[str]") -> str:
        inner = match.group(1)
        return inner if any(glyph in inner for glyph in _MATH_GLYPHS) else match.group(0)

    text = re.sub(r"\$([^$\n]{1,80})\$", _unwrap, text)
    text = re.sub(r"\\\((.*?)\\\)", _unwrap, text)
    return text


class SummarizerAgent:
    """Polish final Markdown and gate insufficiently grounded answers."""

    def __init__(
        self,
        model: BaseChatModel | None = None,
        summarizer: Runnable[dict[str, Any], SummarizerDecision] | None = None,
        interrogator_agent: Any | None = None,
    ) -> None:
        self._summarizer = summarizer or self._build_summarizer(model)

    @staticmethod
    def _build_summarizer(
        model: BaseChatModel | None,
    ) -> Runnable[dict[str, Any], SummarizerDecision]:
        settings = get_settings()
        if model is None:
            # primary = ChatGroq(
            #     model=settings.groq_model,
            #     api_key=settings.groq_api_key,
            #     temperature=0.1,
            #     max_tokens=500,
            # )
            primary = ChatGoogleGenerativeAI(
                model=settings.google_flash_model,
                api_key=settings.google_genai_api_key,
                temperature=0.1,
                max_tokens=1000,
                retries=2,
            ).with_structured_output(SummarizerDecision, method="json_schema")
            fallback = ChatGoogleGenerativeAI(
                model=settings.google_fallback_flash_model,
                api_key=settings.google_genai_api_key,
                temperature=0.1,
                max_tokens=1000,
                retries=2,
            ).with_structured_output(SummarizerDecision, method="json_schema")
            structured_model = primary.with_fallbacks(
                [fallback], exceptions_to_handle=(Exception,)
            )
        else:
            structured_model = model.with_structured_output(
                SummarizerDecision, method="json_schema"
            )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SUMMARIZER_SYSTEM_PROMPT),
                (
                    "human",
                    (
                        "<USER_QUERY>\n{query}\n</USER_QUERY>\n"
                        "<GROUNDING_METADATA>\n{grounding}\n</GROUNDING_METADATA>\n"
                        "<DRAFT_MARKDOWN>\n{draft}\n</DRAFT_MARKDOWN>"
                    ),
                ),
            ]
        )
        return prompt | structured_model

    @staticmethod
    def _grounding_metadata(state: AgentState) -> dict[str, Any]:
        evidence = state.get("retrieved_evidence", [])
        generic_sources = [
            item.url or item.source_id
            for item in evidence
            if item.metadata.get("generic_external")
        ]
        project_sources = [
            item.url or item.source_id
            for item in evidence
            if item.source_type in {"github", "github_live", "notion", "interview"}
            and not item.metadata.get("generic_external")
        ]
        return {
            "grading": state.get("grading", {}),
            "generic_external_sources": generic_sources,
            "project_grounded_sources": project_sources,
            "generic_fallback": state.get("route") == "generic",
        }

    async def summarize_state(self, state: AgentState) -> AgentState:
        query = state.get("contextualized_query") or state.get("query")
        draft = state.get("response")
        if not query:
            raise ValueError("state does not contain a query")
        if not draft:
            raise ValueError("state does not contain a response to summarize")
        grounding = self._grounding_metadata(state)

        with get_langfuse_client().start_as_current_observation(
            name="summarize-and-check-grounding",
            as_type="evaluator",
            input={
                "draft_word_count": len(draft.split()),
                "generic_external_sources": len(grounding["generic_external_sources"]),
            },
        ) as observation:
            result = await self._summarizer.ainvoke(
                {"query": query, "draft": draft, "grounding": grounding},
                config={"callbacks": get_langfuse_callbacks()},
            )
            decision = SummarizerDecision.model_validate(result)
            if grounding["generic_external_sources"]:
                decision.has_knowledge_gap = True
                if decision.alignment is GroundingAlignment.USER_GROUNDED:
                    decision.alignment = GroundingAlignment.MIXED
                decision.gap_reason = decision.gap_reason or (
                    "The answer relies on generic web evidence that does not verify "
                    "the user's project-specific rationale."
                )
                decision.follow_up_questions = decision.follow_up_questions or [
                    "What project requirement or limitation led to this decision?"
                ]

            updated: AgentState = dict(state)
            cleaned_draft = _strip_unsupported_latex(draft)
            updated["draft_response"] = cleaned_draft
            updated["summarization"] = decision.model_dump(mode="python")
            observation.update(output=updated["summarization"])
            if decision.has_knowledge_gap:
                updated.pop("response", None)
                updated["route"] = "interrogator"
                updated["knowledge_gap"] = {
                    "reason": decision.gap_reason,
                    "questions": decision.follow_up_questions,
                    "alignment": decision.alignment,
                }
                updated["response"] = cleaned_draft
                return updated
            else:
                updated["route"] = "complete"
                updated["response"] = cleaned_draft
                updated.pop("knowledge_gap", None)
            return updated