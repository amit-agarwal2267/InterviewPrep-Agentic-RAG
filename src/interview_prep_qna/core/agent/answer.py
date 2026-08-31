from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI

from interview_prep_qna.core.agent.prompts import ANSWER_SYSTEM_PROMPT
from interview_prep_qna.core.agent.state import AgentState, RetrievedEvidence
from interview_prep_qna.core.agent.summarizer import SummarizerAgent
from interview_prep_qna.core.config import get_settings
from interview_prep_qna.observability import get_langfuse_client


class AnswerAgent:
    """Generate the final long-form, cited Markdown answer from graded evidence."""

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
        settings = get_settings()
        if model is None:
            primary = ChatGoogleGenerativeAI(
                model=settings.gemini_reasoning_model,
                api_key=settings.google_genai_api_key,
                temperature=0.2,
                max_tokens=settings.answer_max_tokens,
                retries=0,
            )
            fallback = ChatGoogleGenerativeAI(
                model=settings.gemini_fallback_reasoning_model,
                api_key=settings.google_genai_api_key,
                temperature=0.2,
                max_tokens=settings.answer_max_tokens,
                retries=0,
            )
            model = primary.with_fallbacks(
                [fallback], exceptions_to_handle=(Exception,)
            )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", ANSWER_SYSTEM_PROMPT),
                (
                    "human",
                    (
                        "<USER_QUERY>\n{query}\n</USER_QUERY>\n\n"
                        "<GRADED_EVIDENCE>\n{evidence}\n</GRADED_EVIDENCE>"
                    ),
                ),
            ]
        ).partial(
            min_words=settings.answer_min_words,
            max_words=settings.answer_max_words,
        )
        return prompt | model

    @staticmethod
    def _deduplicate_evidence(
        evidence: list[RetrievedEvidence],
    ) -> list[RetrievedEvidence]:
        """Collapse multiple chunks from one source into one citable record."""
        grouped: dict[str, RetrievedEvidence] = {}
        contents: dict[str, list[str]] = {}
        for item in evidence:
            key = (
                item.url
                or (
                    f"{item.source_type}:{item.source_id}"
                    if item.source_id
                    else item.document_id
                )
            ).rstrip("/")
            if key not in grouped:
                grouped[key] = item
                contents[key] = [item.content]
            elif item.content not in contents[key]:
                contents[key].append(item.content)
        return [
            item.model_copy(update={"content": "\n\n".join(contents[key])[:24_000]})
            for key, item in grouped.items()
        ]

    @staticmethod
    def _format_evidence(evidence: list[RetrievedEvidence]) -> str:
        if not evidence:
            return "No evidence was supplied."
        records = []
        for index, item in enumerate(evidence, start=1):
            image_urls = [item.image_url] if item.image_url else []
            image_urls.extend(item.metadata.get("image_urls", []))
            records.append(
                f"[Evidence {index}]\n"
                f"source_type: {item.source_type}\n"
                f"source_id: {item.source_id or 'Unavailable'}\n"
                f"title: {item.title or 'Untitled'}\n"
                f"url: {item.url or 'Unavailable'}\n"
                f"image_urls: {image_urls or 'None'}\n"
                f"content:\n{item.content[:12_000]}"
            )
        return "\n\n".join(records)

    @staticmethod
    def _references(evidence: list[RetrievedEvidence]) -> str:
        lines = ["## References", ""]
        for index, item in enumerate(evidence, start=1):
            title = (
                (item.title or item.source_id or f"Evidence {index}")
                .replace("[", "\\[")
                .replace("]", "\\]")
            )
            source = item.source_type.replace("_", " ").title()
            if item.url:
                lines.append(f"{index}. [{title}]({item.url}) — {source}")
            else:
                lines.append(f"{index}. {title} — {source}")
        return "\n".join(lines)

    async def answer(self, query: str, evidence: list[RetrievedEvidence]) -> str:
        if not query.strip():
            raise ValueError("query must not be empty")
        evidence = self._deduplicate_evidence(evidence)
        with get_langfuse_client().start_as_current_observation(
            name="generate-final-answer",
            as_type="generation",
            input={"query": query, "evidence_count": len(evidence)},
            model=get_settings().gemini_reasoning_model,
        ) as observation:
            chunks: list[str] = []
            async for result in self._responder.astream(
                {"query": query.strip(), "evidence": self._format_evidence(evidence)},
                config={"tags": ["answer_generation"]},
            ):
                content = result.content if hasattr(result, "content") else result
                if isinstance(content, list):
                    content = "".join(
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict)
                    )
                chunks.append(str(content))
            markdown = "".join(chunks).strip()
            final_answer = f"{markdown}\n\n{self._references(evidence)}"
            observation.update(
                output={
                    "word_count": len(markdown.split()),
                    "reference_count": len(evidence),
                }
            )
            return final_answer

    async def answer_state(self, state: AgentState) -> AgentState:
        """Generate and summarize an answer for non-graph callers."""
        updated = await self.generate_state(state)
        return await self._summarizer.summarize_state(updated)

    async def generate_state(self, state: AgentState) -> AgentState:
        """Generate the draft answer without advancing to another graph node."""
        query = state.get("contextualized_query") or state.get("query")
        if not query:
            raise ValueError("state does not contain a query")
        grading = state.get("grading", {})
        if grading.get("action") != "answer" or not grading.get("sufficient"):
            raise ValueError("state evidence has not been graded as sufficient")
        updated: AgentState = dict(state)
        updated["response"] = await self.answer(
            query, state.get("retrieved_evidence", [])
        )
        updated["current_agent"] = "answer"
        updated["route"] = "summarizer"
        return updated
