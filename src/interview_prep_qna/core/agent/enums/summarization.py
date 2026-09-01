from enum import StrEnum


class GroundingAlignment(StrEnum):
    USER_GROUNDED = "user_grounded"
    MIXED = "mixed"
    GENERIC = "generic"
    NO_GROUNDING_NEEDED = "no_grounding_needed"
    