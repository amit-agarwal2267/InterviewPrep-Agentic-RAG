import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from interview_prep_qna.core.agent.escalation.github_live import (
    GitHubLiveAgent,
    _readme_score,
    _search_terms,
)


def test_github_live_builds_short_search_terms_from_natural_language() -> None:
    terms = _search_terms(
        "What tools have I used in my autonomous market research agent project?",
        ["The tools and integrations documented in the repository"],
    )

    assert terms[:3] == ["tools", "autonomous", "market"]
    assert "what" not in terms
    assert len(terms) <= 8


def test_github_live_prioritizes_matching_project_readme() -> None:
    terms = ["autonomous", "market", "research", "tools"]
    matching = {
        "name": "autonomous-market-research-agent",
        "full_name": "owner/autonomous-market-research-agent",
        "description": "Research workflow",
    }
    unrelated = {
        "name": "portfolio",
        "full_name": "owner/portfolio",
        "description": "Personal site",
    }
    readme = "Tools: Python, LangChain, LangGraph, Tavily, Exa, CrustAPI, Apify"

    assert _readme_score(matching, readme, terms) > _readme_score(
        unrelated, readme, terms
    )


def test_github_live_creates_readme_evidence_with_live_metadata() -> None:
    evidence = GitHubLiveAgent._readme_evidence(
        {
            "full_name": "owner/autonomous-market-research-agent",
            "default_branch": "main",
        },
        "**Python**, **LangChain**, and **Tavily**",
    )

    assert evidence.title == "README.md"
    assert evidence.source_type == "github_live"
    assert evidence.metadata["readme"] is True
    assert evidence.url == (
        "https://github.com/owner/autonomous-market-research-agent/blob/main/README.md"
    )


def test_github_live_search_scores_readmes_with_terms() -> None:
    repository = {
        "name": "autonomous-market-research-agent",
        "full_name": "owner/autonomous-market-research-agent",
        "description": "Research workflow",
        "default_branch": "main",
    }
    readme = "Tools: Python, LangChain, LangGraph, Tavily, Exa"

    class FakeResponse:
        def __init__(self, text: str, status_code: int = 200, payload: dict | None = None) -> None:
            self.text = text
            self.status_code = status_code
            self.is_success = status_code < 400
            self._payload = payload or {"items": []}

        def json(self):
            return self._payload

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None, params=None):
            if "search/code" in url:
                return FakeResponse("", payload={"items": []})
            return FakeResponse(readme)

    settings = SimpleNamespace(
        github_token=SimpleNamespace(get_secret_value=lambda: "dummy-token"),
        github_live_max_results=5,
    )

    with (
        patch(
            "interview_prep_qna.core.agent.escalation.github_live.list_accessible_repositories",
            AsyncMock(return_value=[repository]),
        ),
        patch(
            "interview_prep_qna.core.agent.escalation.github_live.httpx.AsyncClient",
            return_value=FakeClient(),
        ),
        patch(
            "interview_prep_qna.core.agent.escalation.github_live.get_settings",
            return_value=settings,
        ),
    ):
        results = asyncio.run(
            GitHubLiveAgent().search(
                "autonomous market research tools",
                ["tools and integrations documented in the repository"],
            )
        )

    assert results
    assert results[0].source_type == "github_live"
    assert "owner/autonomous-market-research-agent" in results[0].source_id
