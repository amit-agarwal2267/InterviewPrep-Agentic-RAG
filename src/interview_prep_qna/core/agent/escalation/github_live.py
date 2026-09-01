import asyncio
import hashlib
import logging
import re

import httpx

from interview_prep_qna.core.agent.state import RetrievedEvidence
from interview_prep_qna.core.config import get_settings
from interview_prep_qna.knowledge_base.loaders.github_loader import (
    list_accessible_repositories,
)
from interview_prep_qna.observability import get_langfuse_client

logger = logging.getLogger(__name__)

_STOP_WORDS = {
    "about", "agent", "and", "are", "but", "could", "for", "from", "have",
    "not", "our", "project", "should", "that", "the", "their", "this", "used",
    "uses", "was", "what", "when", "where", "which", "with", "would", "you",
    "your",
}


def _search_terms(query: str, missing_information: list[str] | None) -> list[str]:
    text = " ".join([query, *(missing_information or [])]).lower()
    terms = [
        word for word in re.findall(r"[a-z0-9_+.-]{3,}", text)
        if word not in _STOP_WORDS
    ]
    return list(dict.fromkeys(terms))[:8]


def _readme_score(repository: dict, content: str, terms: list[str]) -> int:
    identity = " ".join(
        str(repository.get(key) or "")
        for key in ("name", "full_name", "description", "topics")
    ).lower()
    lowered = content.lower()
    return sum(4 for term in terms if term in identity) + sum(
        1 for term in terms if term in lowered
    )


class GitHubLiveAgent:
    """Retrieve current README and code content visible to the configured token."""

    async def search(
        self, query: str, missing_information: list[str] | None = None
    ) -> list[RetrievedEvidence]:
        settings = get_settings()
        terms = _search_terms(query, missing_information)
        headers = {
            "Authorization": f"Bearer {settings.github_token.get_secret_value()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        with get_langfuse_client().start_as_current_observation(
            name="github-live-search",
            as_type="tool",
            input={"query_characters": len(query), "search_term_count": len(terms)},
        ) as observation:
            try:
                repositories = await list_accessible_repositories()
                async with httpx.AsyncClient(headers=headers, timeout=30) as client:
                    readmes: list[tuple[dict, str]] = []
                    candidates = repositories[:50]
                    for start in range(0, len(candidates), 10):
                        readmes.extend(
                            await asyncio.gather(
                                *(
                                    self._fetch_readme(client, headers, repository)
                                    for repository in candidates[start : start + 10]
                                )
                            )
                        )
                    ranked_readmes = sorted(
                        (
                            (
                                _readme_score(repository, content, terms),
                                repository,
                                content,
                            )
                            for repository, content in readmes
                            if content
                        ),
                        key=lambda item: item[0],
                        reverse=True,
                    )
                    evidence = [
                        self._readme_evidence(repository, content)
                        for score, repository, content in ranked_readmes
                        if score > 1
                    ][: settings.github_live_max_results]

                    if len(evidence) < settings.github_live_max_results and terms:
                        evidence.extend(
                            await self._search_code(
                                client,
                                headers,
                                repositories,
                                terms,
                                settings.github_live_max_results - len(evidence),
                                {item.url for item in evidence},
                            )
                        )
            except Exception:
                logger.exception("github_live_search_failed")
                observation.update(level="ERROR", output={"status": "failed"})
                raise
            output = {
                "repository_count": len(repositories),
                "result_count": len(evidence),
                "readme_results": sum(item.title == "README.md" for item in evidence),
            }
            observation.update(output=output)
            logger.info("github_live_search_completed", extra=output)
            return evidence

    @staticmethod
    async def _fetch_readme(
        client: httpx.AsyncClient, headers: dict[str, str], repository: dict
    ) -> tuple[dict, str]:
        response = await client.get(
            f"https://api.github.com/repos/{repository['full_name']}/readme",
            headers={**headers, "Accept": "application/vnd.github.raw+json"},
        )
        return repository, response.text[:100_000] if response.is_success else ""

    @staticmethod
    def _readme_evidence(repository: dict, content: str) -> RetrievedEvidence:
        full_name = repository["full_name"]
        branch = repository.get("default_branch", "main")
        url = f"https://github.com/{full_name}/blob/{branch}/README.md"
        return RetrievedEvidence(
            chunk_id=hashlib.sha256(f"github:{url}".encode()).hexdigest(),
            document_id=f"github-live:{full_name}",
            content=content,
            source_type="github_live",
            source_id=f"{full_name}:README.md",
            title="README.md",
            url=url,
            metadata={"repository": full_name, "live": True, "readme": True},
        )

    @staticmethod
    async def _search_code(
        client: httpx.AsyncClient,
        headers: dict[str, str],
        repositories: list[dict],
        terms: list[str],
        limit: int,
        existing_urls: set[str | None],
    ) -> list[RetrievedEvidence]:
        found: list[RetrievedEvidence] = []
        keywords = " ".join(terms[:5])
        for repository in repositories:
            response = await client.get(
                "https://api.github.com/search/code",
                params={
                    "q": f"{keywords} repo:{repository['full_name']}",
                    "per_page": limit - len(found),
                },
            )
            if response.status_code in {403, 404, 422}:
                continue
            response.raise_for_status()
            for item in response.json().get("items", []):
                if item.get("html_url") in existing_urls:
                    continue
                raw = await client.get(
                    item["url"],
                    headers={**headers, "Accept": "application/vnd.github.raw+json"},
                )
                if raw.is_success:
                    repository_name = item["repository"]["full_name"]
                    found.append(
                        RetrievedEvidence(
                            chunk_id=hashlib.sha256(
                                f"github:{item.get('html_url')}".encode()
                            ).hexdigest(),
                            document_id=f"github-live:{repository_name}",
                            content=raw.text[:100_000],
                            source_type="github_live",
                            source_id=f"{repository_name}:{item['path']}",
                            title=item["path"],
                            url=item.get("html_url"),
                            metadata={"repository": repository_name, "live": True},
                        )
                    )
                if len(found) >= limit:
                    return found
        return found