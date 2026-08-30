import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from interview_prep_qna.api.routes.conversations import router as conversations_router
from interview_prep_qna.conversations.client import close_mongo_client
from interview_prep_qna.core.scheduler import create_scheduler
from interview_prep_qna.health import router as health_router
from interview_prep_qna.observability import (
    bind_request_id,
    configure_logging,
    reset_request_id,
    shutdown_langfuse,
)
from interview_prep_qna.webhooks.github_handler import router as github_router
from interview_prep_qna.webhooks.manual_trigger import router as manual_trigger_router
from interview_prep_qna.webhooks.notion_handler import router as notion_router
from interview_prep_qna.webhooks.sheets_handler import router as sheets_router

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    try:
        scheduler = create_scheduler()
        application.state.scheduler = scheduler
        scheduler.start()
    except Exception:
        logger.critical("application_startup_failed", exc_info=True)
        raise
    logger.info("application_started")
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await close_mongo_client()
        shutdown_langfuse()
        logger.info("application_stopped")


app = FastAPI(title="Interview Prep Q&A", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def structured_request_logging(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid4().hex
    token = bind_request_id(request_id)
    started = perf_counter()
    logger.info(
        "http_request_started",
        extra={"method": request.method, "path": request.url.path},
    )
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "http_request_failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "latency_ms": round((perf_counter() - started) * 1000, 2),
            },
        )
        raise
    else:
        response.headers["X-Request-ID"] = request_id
        level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            level,
            "http_request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": round((perf_counter() - started) * 1000, 2),
            },
        )
        return response
    finally:
        reset_request_id(token)
app.include_router(github_router)
app.include_router(notion_router)
app.include_router(sheets_router)
app.include_router(manual_trigger_router)
app.include_router(health_router)
app.include_router(conversations_router)


def run_api() -> None:
    """Run the FastAPI application defined in this module."""
    uvicorn.run("interview_prep_qna:app", host="0.0.0.0", port=8000)


def main() -> None:
    run_api()
