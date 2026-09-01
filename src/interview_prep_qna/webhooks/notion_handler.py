from fastapi import APIRouter, Request

from interview_prep_qna.core.pipeline import ingest_document
from interview_prep_qna.knowledge_base.loaders.notion_loader import fetch_page_content

router = APIRouter()


@router.post("/webhooks/notion")
async def notion_webhook(request: Request):
    payload = await request.json()

    if "verification_token" in payload:
        return {"challenge": payload["verification_token"]}

    if payload.get("type") != "page.content_updated":
        return {"status": "ignored"}

    page_id = payload["entity"]["id"]
    title, text, image_urls = await fetch_page_content(page_id)

    await ingest_document(
        source_type="notion",
        source_id=page_id,
        title=title,
        url=f"https://notion.so/{page_id.replace('-', '')}",
        content=text,
        image_urls=image_urls,
    )
    return {"status": "processed"}
