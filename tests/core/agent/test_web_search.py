import pytest
from pydantic import SecretStr

from interview_prep_qna.core.agent.escalation import web_search


@pytest.mark.asyncio
async def test_web_search_uses_tavily_client(monkeypatch) -> None:
    calls: dict = {}

    class FakeTavilyClient:
        def __init__(self, api_key: str) -> None:
            calls["api_key"] = api_key

        def search(self, **kwargs):
            calls["search"] = kwargs
            return {
                "results": [
                    {
                        "url": "https://example.com/hnsw",
                        "title": "HNSW",
                        "content": "Current external context",
                        "score": 0.9,
                    }
                ]
            }

    monkeypatch.setattr(web_search, "TavilyClient", FakeTavilyClient)

    async def run_inline(function, **kwargs):
        return function(**kwargs)

    monkeypatch.setattr(web_search.asyncio, "to_thread", run_inline)
    monkeypatch.setattr(
        web_search,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {"tavily_api_key": SecretStr("test-key"), "tavily_max_results": 5},
        )(),
    )
    results = await web_search.WebSearchAgent().search(
        "Why HNSW?", ["Current HNSW tradeoffs"]
    )

    assert calls["search"]["query"] == "Current HNSW tradeoffs"
    assert results[0].url == "https://example.com/hnsw"
    assert results[0].metadata["generic_external"] is True
