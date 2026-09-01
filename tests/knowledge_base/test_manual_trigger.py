import pytest
from httpx import ASGITransport, AsyncClient

from interview_prep_qna import app
from interview_prep_qna.core.config import get_settings


@pytest.mark.asyncio
async def test_manual_trigger_runs_all_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    expected_sources = {
        "github": {"status": "completed", "updated": 1},
        "notion": {"status": "completed", "updated": 1},
        "google_sheets": {"status": "completed", "updated": 1},
    }

    async def fake_sync_all_sources() -> dict:
        return expected_sources

    monkeypatch.setattr(
        "interview_prep_qna.webhooks.manual_trigger.sync_all_sources",
        fake_sync_all_sources,
    )
    settings = get_settings()
    secret = settings.admin_trigger_secret or settings.sheets_shared_secret

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/admin/manual-trigger",
            headers={"X-Admin-Secret": secret.get_secret_value()},
        )

    print("\nManual trigger response:\n", response.json())
    assert response.status_code == 200
    assert response.json() == {"status": "completed", "sources": expected_sources}


@pytest.mark.asyncio
async def test_manual_trigger_rejects_invalid_secret() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/admin/manual-trigger", headers={"X-Admin-Secret": "invalid"}
        )
    assert response.status_code == 401
