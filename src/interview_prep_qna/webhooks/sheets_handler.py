from fastapi import APIRouter, Header, HTTPException, Request

from interview_prep_qna.core.config import get_settings
from interview_prep_qna.core.pipeline import ingest_document

router = APIRouter()


@router.post("/webhooks/sheets")
async def sheets_webhook(request: Request, x_shared_secret: str = Header(...)):
    settings = get_settings()
    if x_shared_secret != settings.sheets_shared_secret.get_secret_value():
        raise HTTPException(status_code=401, detail="Invalid secret")

    payload = await request.json()
    if "row" not in payload or not isinstance(payload.get("rowData"), dict):
        raise HTTPException(status_code=422, detail="row and rowData are required")
    row_id = f"row-{payload['row']}"
    content = "\n".join(f"{k}: {v}" for k, v in payload["rowData"].items())

    await ingest_document(
        source_type="interview",
        source_id=row_id,
        title=payload["rowData"].get("Company", row_id),
        url=None,
        content=content,
    )
    return {"status": "processed"}
