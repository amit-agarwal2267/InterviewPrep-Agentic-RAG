from pydantic import BaseModel, Field, model_validator

from interview_prep_qna.core.agent.enums import GroundingAlignment


class SummarizerDecision(BaseModel):
    alignment: GroundingAlignment
    has_knowledge_gap: bool
    gap_reason: str | None = None
    follow_up_questions: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def normalize_gap_fields(self) -> "SummarizerDecision":
        if self.alignment is GroundingAlignment.GENERIC:
            self.has_knowledge_gap = True
        if self.has_knowledge_gap:
            if not self.gap_reason:
                raise ValueError("A knowledge gap requires gap_reason")
            if not self.follow_up_questions:
                raise ValueError("A knowledge gap requires follow_up_questions")
        else:
            self.gap_reason = None
            self.follow_up_questions = []
        return self
