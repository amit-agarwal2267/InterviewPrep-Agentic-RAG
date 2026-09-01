from pydantic import BaseModel, Field, model_validator

from interview_prep_qna.core.agent.enums import GradingAction


class GradingDecision(BaseModel):
    action: GradingAction
    sufficient: bool
    reason: str = Field(min_length=1, max_length=500)
    missing_information: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def action_matches_sufficiency(self) -> "GradingDecision":
        self.sufficient = self.action is GradingAction.ANSWER
        if self.sufficient:
            self.missing_information = []
        return self

    @property
    def needs_github(self) -> bool:
        return self.action is GradingAction.GITHUB

    @property
    def needs_web(self) -> bool:
        return self.action is GradingAction.WEB
