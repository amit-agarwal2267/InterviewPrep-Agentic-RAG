from enum import StrEnum


class InterrogationPhase(StrEnum):
    AWAITING_ANSWER = "awaiting_answer"
    AWAITING_CONSENT = "awaiting_consent"
    READY_TO_WRITE = "ready_to_write"
    COMPLETE = "complete"
