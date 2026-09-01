import pytest

from interview_prep_qna.core.config import get_settings
from interview_prep_qna.observability.langfuse_client import (
    get_langfuse_client,
    is_langfuse_configured,
    shutdown_langfuse,
)


def test_langfuse_client_is_a_singleton() -> None:
    first = get_langfuse_client()
    second = get_langfuse_client()

    assert first is second
    assert get_langfuse_client.cache_info().currsize == 1


@pytest.mark.integration
def test_langfuse_authentication_and_trace_delivery() -> None:
    if not is_langfuse_configured():
        pytest.skip("Set Langfuse credentials in .env to run this integration test")

    settings = get_settings()
    client = get_langfuse_client()
    try:
        assert client.auth_check(), "Langfuse rejected the configured credentials"

        with client.start_as_current_observation(
            name="pytest-langfuse-client",
            as_type="span",
            input={"test": "observability client"},
            metadata={
                "environment": settings.langfuse_environment,
                "generated_by": "pytest",
            },
        ) as observation:
            observation.update(output={"status": "trace created successfully"})

        client.flush()
        print(
            "\nLangfuse response:\n",
            {
                "authenticated": True,
                "trace_flushed": True,
                "base_url": settings.langfuse_base_url,
                "environment": settings.langfuse_environment,
            },
        )
    finally:
        shutdown_langfuse()

    assert get_langfuse_client.cache_info().currsize == 0
