import json
from typing import Any

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text

from interview_prep_qna.conversations.client import get_conversation_database
from interview_prep_qna.core.config import get_settings
from interview_prep_qna.db.client.postgres import get_session
from interview_prep_qna.observability import is_langfuse_configured

router = APIRouter(prefix="/health", tags=["health"])


def _has_secret(value: Any) -> bool:
    if value is None:
        return False
    raw = value.get_secret_value() if hasattr(value, "get_secret_value") else str(value)
    return bool(raw and raw != "replace-me")


async def _database_check() -> dict[str, Any]:
    try:
        async with get_session() as session:
            result = await session.execute(
                text("""
                    SELECT
                        EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector') AS pgvector,
                        to_regclass('public.documents') IS NOT NULL AS documents,
                        to_regclass('public.chunks') IS NOT NULL AS chunks
                """)
            )
            row = result.mappings().one()
        ready = all(row.values())
        return {"status": "up" if ready else "degraded", **dict(row)}
    except Exception as exc:  
        return {
            "status": "down",
            "error": f"{type(exc).__name__}: {exc}",
        }


async def _mongodb_check() -> dict[str, Any]:
    try:
        result = await get_conversation_database().command("ping")
        return {"status": "up" if result.get("ok") == 1 else "down"}
    except Exception as exc:  
        return {"status": "down", "error": f"{type(exc).__name__}: {exc}"}


def _configuration_checks() -> dict[str, dict[str, Any]]:
    settings = get_settings()
    google_credentials_valid = False
    if settings.google_service_account_path.is_file():
        try:
            credential = json.loads(settings.google_service_account_path.read_text())
            google_credentials_valid = credential.get("type") == "service_account"
        except (OSError, ValueError):
            pass

    return {
        "github": {
            "status": "configured" if _has_secret(settings.github_token) else "missing"
        },
        "notion": {
            "status": "configured" if _has_secret(settings.notion_token) else "missing"
        },
        "google_sheets": {
            "status": (
                "configured"
                if google_credentials_valid and settings.google_spreadsheet_id
                else "missing"
            )
        },
        "gemini": {
            "status": (
                "configured"
                if _has_secret(settings.google_genai_api_key)
                else "missing"
            )
        },
        "langfuse": {
            "status": (
                "configured"
                if is_langfuse_configured()
                else "disabled"
                if not settings.langfuse_enabled
                else "missing"
            ),
            "required": False,
        },
    }


@router.get("/live")
async def liveness() -> dict[str, str]:
    """Confirm that the API process and event loop are alive."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness(request: Request, response: Response) -> dict[str, Any]:
    """Confirm critical services and source configuration are ready."""
    scheduler = getattr(request.app.state, "scheduler", None)
    checks: dict[str, Any] = {
        "database": await _database_check(),
        "mongodb": await _mongodb_check(),
        "scheduler": {"status": "up" if scheduler and scheduler.running else "down"},
        **_configuration_checks(),
    }
    required_ready = (
        checks["database"]["status"] == "up"
        and checks["mongodb"]["status"] == "up"
        and checks["scheduler"]["status"] == "up"
        and all(
            checks[name]["status"] == "configured"
            for name in ("github", "notion", "google_sheets", "gemini")
        )
    )
    if not required_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if required_ready else "not_ready", "checks": checks}


@router.get("")
async def health(request: Request, response: Response) -> dict[str, Any]:
    """Backward-compatible alias for the readiness endpoint."""
    return await readiness(request, response)
