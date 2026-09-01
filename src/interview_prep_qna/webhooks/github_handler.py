import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Request

from interview_prep_qna.core.config import get_settings
from interview_prep_qna.core.pipeline import ingest_document
from interview_prep_qna.knowledge_base.loaders.github_loader import fetch_changed_files

router = APIRouter()


def verify_signature(payload: bytes, signature: str) -> bool:
    settings = get_settings()
    expected = (
        "sha256="
        + hmac.new(
            settings.github_webhook_secret.get_secret_value().encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
    )
    return hmac.compare_digest(expected, signature)


@router.post("/webhooks/github")
async def github_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    if request.headers.get("X-GitHub-Event") != "push":
        return {"status": "ignored"}

    changed_files: set[str] = set()
    for commit in payload.get("commits", []):
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))

    relevant = sorted(f for f in changed_files if f.endswith((".md", ".py")))
    contents = await fetch_changed_files(payload["repository"]["full_name"], relevant)

    branch = payload.get("ref", "refs/heads/main").removeprefix("refs/heads/")
    for path, content in contents.items():
        await ingest_document(
            source_type="github",
            source_id=f"{payload['repository']['full_name']}:{path}",
            title=path,
            url=f"{payload['repository']['html_url']}/blob/{branch}/{path}",
            content=content,
        )
    return {"status": "processed", "files": relevant}
