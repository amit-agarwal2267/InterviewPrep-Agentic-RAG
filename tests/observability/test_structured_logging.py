import json
import logging

from interview_prep_qna.observability.logging import (
    JsonFormatter,
    bind_request_id,
    reset_request_id,
)


def test_json_formatter_includes_level_context_and_extra_fields() -> None:
    formatter = JsonFormatter()
    token = bind_request_id("request-123")
    try:
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname=__file__,
            lineno=20,
            msg="recoverable_problem",
            args=(),
            exc_info=None,
        )
        record.conversation_id = "conversation-1"
        payload = json.loads(formatter.format(record))
    finally:
        reset_request_id(token)

    assert payload["level"] == "WARNING"
    assert payload["request_id"] == "request-123"
    assert payload["message"] == "recoverable_problem"
    assert payload["conversation_id"] == "conversation-1"
