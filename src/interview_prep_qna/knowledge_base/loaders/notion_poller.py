import hashlib

from notion_client import AsyncClient
from sqlalchemy import text

from interview_prep_qna.core.config import get_settings
from interview_prep_qna.core.pipeline import ingest_document
from interview_prep_qna.db.client.postgres import get_session
from interview_prep_qna.knowledge_base.loaders.notion_loader import fetch_page_content


async def poll_notion_changes() -> int:
    """Fallback for block-level edits webhooks can't see. Run on a schedule."""
    notion = AsyncClient(auth=get_settings().notion_token.get_secret_value())
    cursor = None
    ingested = 0
    while True:
        results = await notion.search(
            filter={"property": "object", "value": "page"},
            sort={"direction": "descending", "timestamp": "last_edited_time"},
            start_cursor=cursor,
        )

        for page in results["results"]:
            page_id = page["id"]
            title, content, image_urls = await fetch_page_content(page_id)
            new_hash = hashlib.sha256(content.encode()).hexdigest()

            async with get_session() as session:
                existing = await session.execute(
                    text(
                        "SELECT content_hash FROM documents WHERE source_type = 'notion' AND source_id = :sid"
                    ),
                    {"sid": page_id},
                )
                row = existing.fetchone()

            if row and row.content_hash == new_hash:
                continue

            changed = await ingest_document(
                source_type="notion",
                source_id=page_id,
                title=title,
                url=f"https://notion.so/{page_id.replace('-', '')}",
                content=content,
                image_urls=image_urls,
            )
            ingested += int(changed)
        if not results.get("has_more"):
            break
        cursor = results.get("next_cursor")
    return ingested
