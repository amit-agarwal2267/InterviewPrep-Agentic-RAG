from pydantic import BaseModel, Field

from interview_prep_qna.core.agent.enums import RouteDestination


class RouterDecision(BaseModel):
    destination: RouteDestination
    reason: str = Field(min_length=1, max_length=240)

    @property
    def use_rag(self) -> bool:
        return self.destination is RouteDestination.RAG
