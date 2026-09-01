import asyncio
import hashlib
import logging

from tavily import TavilyClient

from interview_prep_qna.core.agent.state import RetrievedEvidence
from interview_prep_qna.core.config import get_settings
from interview_prep_qna.observability import get_langfuse_client

logger = logging.getLogger(__name__)


class WebSearchAgent:
    """Fetch current external evidence with Tavily."""

    async def search(
        self, query: str, missing_information: list[str] | None = None
    ) -> list[RetrievedEvidence]:
        settings = get_settings()
        if not settings.tavily_api_key:
            raise ValueError("TAVILY_API_KEY is required for web escalation")
        search_query = " ".join(missing_information or []) or query
        with get_langfuse_client().start_as_current_observation(
            name="tavily-web-search",
            as_type="tool",
            input={"query_characters": len(search_query)},
        ) as observation:
            try:
                client = TavilyClient(
                    api_key=settings.tavily_api_key.get_secret_value()
                )
                response = await asyncio.to_thread(
                    client.search,
                    query=search_query,
                    search_depth="advanced",
                    max_results=settings.tavily_max_results,
                    include_answer=False,
                    include_raw_content=False,
                )
                results = response.get("results", [])
                evidence = [
                    RetrievedEvidence(
                        chunk_id=hashlib.sha256(
                            f"web:{item['url']}".encode()
                        ).hexdigest(),
                        document_id=f"web:{item['url']}",
                        content=item.get("content", ""),
                        source_type="web",
                        source_id=item["url"],
                        title=item.get("title"),
                        url=item["url"],
                        metadata={
                            "tavily_score": item.get("score"),
                            "live": True,
                            "generic_external": True,
                            "grounded_in_user_project": False,
                        },
                    )
                    for item in results
                    if item.get("content")
                ]
            except Exception:
                logger.exception("tavily_search_failed")
                observation.update(level="ERROR", output={"status": "failed"})
                raise
            observation.update(output={"result_count": len(evidence)})
        logger.info("tavily_search_completed", extra={"result_count": len(evidence)})
        return evidence
