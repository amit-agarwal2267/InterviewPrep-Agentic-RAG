import asyncio
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Header, HTTPException

from interview_prep_qna.core.config import get_settings
from interview_prep_qna.core.pipeline import ingest_document
from interview_prep_qna.knowledge_base.loaders.github_loader import (
    fetch_changed_files,
    list_accessible_repositories,
    list_repository_files,
)
from interview_prep_qna.knowledge_base.loaders.notion_poller import (
    poll_notion_changes,
)
from interview_prep_qna.knowledge_base.loaders.sheet_loader import fetch_all_rows

router = APIRouter(prefix="/admin", tags=["admin"])


async def _sync_github() -> dict:
    repositories = await list_accessible_repositories()
    fetched_count = 0
    updated_count = 0
    synced_repositories = 0
    skipped_repositories = 0
    for repository in repositories:
        paths = await list_repository_files(repository)
        if not paths:
            skipped_repositories += 1
            continue
        contents = await fetch_changed_files(repository["full_name"], paths)
        synced_repositories += 1
        fetched_count += len(contents)
        for path, content in contents.items():
            changed = await ingest_document(
                source_type="github",
                source_id=f"{repository['full_name']}:{path}",
                title=path,
                url=(
                    f"{repository['html_url']}/blob/"
                    f"{repository.get('default_branch', 'main')}/{path}"
                ),
                content=content,
            )
            updated_count += int(changed)
    return {
        "status": "completed",
        "repositories_found": len(repositories),
        "repositories_synced": synced_repositories,
        "repositories_skipped": skipped_repositories,
        "files_fetched": fetched_count,
        "files_updated": updated_count,
    }


async def _sync_notion() -> dict:
    updated_count = await poll_notion_changes()
    return {"status": "completed", "updated": updated_count}


async def _sync_sheets() -> dict:
    settings = get_settings()
    if not settings.google_spreadsheet_id:
        return {"status": "skipped", "reason": "GOOGLE_SPREADSHEET_ID is empty"}

    rows = await fetch_all_rows(
        settings.google_spreadsheet_id,
        settings.google_sheet_range,
        settings.google_sheet_gid,
    )
    updated_count = 0
    for index, row in enumerate(rows, start=2):
        content = "\n".join(f"{key}: {value}" for key, value in row.items())
        if not content.strip():
            continue
        row_id = str(row.get("ID") or row.get("id") or f"row-{index}")
        changed = await ingest_document(
            source_type="interview",
            source_id=f"{settings.google_spreadsheet_id}:{row_id}",
            title=str(row.get("Company") or row.get("Title") or row_id),
            url=None,
            content=content,
        )
        updated_count += int(changed)
    return {"status": "completed", "fetched": len(rows), "updated": updated_count}


async def _safe_sync(
    name: str, sync: Callable[[], Awaitable[dict]]
) -> tuple[str, dict]:
    try:
        return name, await sync()
    except Exception as exc: 
        return name, {"status": "failed", "error": str(exc)}


async def sync_all_sources() -> dict[str, dict]:
    results = await asyncio.gather(
        _safe_sync("github", _sync_github),
        _safe_sync("notion", _sync_notion),
        _safe_sync("google_sheets", _sync_sheets),
    )
    return dict(results)


@router.post("/manual-trigger")
async def manual_trigger(x_admin_secret: str = Header(...)) -> dict:
    settings = get_settings()
    expected = settings.admin_trigger_secret or settings.sheets_shared_secret
    if x_admin_secret != expected.get_secret_value():
        raise HTTPException(status_code=401, detail="Invalid admin secret")
    return {"status": "completed", "sources": await sync_all_sources()}
