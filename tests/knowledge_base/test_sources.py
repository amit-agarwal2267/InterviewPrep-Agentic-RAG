import json

import pytest
from notion_client import AsyncClient

from interview_prep_qna.core.config import get_settings
from interview_prep_qna.knowledge_base.loaders.github_loader import (
    fetch_changed_files,
    list_accessible_repositories,
    list_repository_files,
)
from interview_prep_qna.knowledge_base.loaders.notion_loader import fetch_page_content
from interview_prep_qna.knowledge_base.loaders.sheet_loader import fetch_all_rows


def _show(source: str, payload: dict) -> None:
    print(f"\nActual {source} data:\n{json.dumps(payload, indent=2, default=str)}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_github_source() -> None:
    repositories = await list_accessible_repositories()
    assert repositories
    repository = None
    files = {}
    skipped_repositories = []
    for candidate in repositories:
        paths = await list_repository_files(candidate)
        if not paths:
            skipped_repositories.append(candidate["full_name"])
            continue
        files = await fetch_changed_files(candidate["full_name"], [paths[0]])
        if files:
            repository = candidate["full_name"]
            break

    assert files, (
        "No supported files could be fetched; skipped repositories: "
        f"{skipped_repositories}"
    )
    _show(
        "GitHub",
        {
            "accessible_repositories": len(repositories),
            "repository": repository,
            "skipped_repositories": skipped_repositories,
            "files": {path: content[:300] for path, content in files.items()},
        },
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_notion_source() -> None:
    settings = get_settings()
    notion = AsyncClient(auth=settings.notion_token.get_secret_value())
    search = await notion.search(
        filter={"property": "object", "value": "page"}, page_size=100
    )
    assert search["results"], "The integration cannot access any Notion pages"

    page = search["results"][0]
    title, content, images = await fetch_page_content(page["id"])
    assert content, "The page has no readable properties or blocks"
    _show(
        "Notion",
        {"title": title, "content": content[:500], "image_count": len(images)},
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_google_sheets_source() -> None:
    settings = get_settings()
    assert settings.google_spreadsheet_id, "GOOGLE_SPREADSHEET_ID is required"
    rows = await fetch_all_rows(
        settings.google_spreadsheet_id,
        settings.google_sheet_range,
        settings.google_sheet_gid,
    )
    assert rows, "The configured sheet contains no data rows"
    _show("Google Sheets", {"row_count": len(rows), "first_rows": rows[:5]})
