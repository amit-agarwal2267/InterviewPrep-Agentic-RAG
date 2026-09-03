import logging
from functools import lru_cache

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from interview_prep_qna.core.config import get_settings

logger = logging.getLogger(__name__)


def is_langfuse_configured() -> bool:
    """Return whether tracing is enabled and both Langfuse keys are configured."""
    settings = get_settings()
    return bool(
        settings.langfuse_enabled
        and settings.langfuse_public_key
        and settings.langfuse_secret_key
    )


@lru_cache(maxsize=1)
def get_langfuse_client() -> Langfuse:
    """Return the process-wide Langfuse client.

    The SDK client is safe to import in development and tests without credentials;
    tracing is disabled until both the public and secret keys are configured.
    """
    settings = get_settings()
    configured = is_langfuse_configured()
    secret_key = (
        settings.langfuse_secret_key.get_secret_value()
        if settings.langfuse_secret_key
        else None
    )
    client = Langfuse(
        public_key=settings.langfuse_public_key if configured else "disabled",
        secret_key=secret_key if configured else "disabled",
        base_url=settings.langfuse_base_url,
        environment=settings.langfuse_environment,
        tracing_enabled=configured,
    )
    logger.info(
        "langfuse_client_initialized",
        extra={"configured": configured, "environment": settings.langfuse_environment},
    )
    return client


def get_langfuse_callbacks() -> list[CallbackHandler]:
    """Return callbacks for native LangChain usage and cost capture."""
    if not is_langfuse_configured():
        return []
    settings = get_settings()
    return [CallbackHandler(public_key=settings.langfuse_public_key)]


def shutdown_langfuse() -> None:
    """Flush pending observations, stop worker threads, and clear the singleton."""
    if get_langfuse_client.cache_info().currsize:
        get_langfuse_client().shutdown()
        get_langfuse_client.cache_clear()
        logger.info("langfuse_client_shutdown")
