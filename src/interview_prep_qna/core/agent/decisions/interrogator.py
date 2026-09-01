from pydantic import BaseModel, Field, model_validator


class InterrogationDecision(BaseModel):
    satisfied: bool
    reason: str = Field(min_length=1, max_length=500)
    next_question: str | None = None

    @model_validator(mode="after")
    def normalize_question(self) -> "InterrogationDecision":
        if self.satisfied:
            self.next_question = None
        elif not self.next_question or not self.next_question.strip():
            raise ValueError("An unsatisfied decision requires next_question")
        return self
