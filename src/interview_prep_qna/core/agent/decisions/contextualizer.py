from pydantic import BaseModel, Field, model_validator

from interview_prep_qna.core.agent.enums import QueryRoute


class ContextualizerDecision(BaseModel):
    route: QueryRoute
    reason: str = Field(min_length=1, max_length=240)
    standalone_query: str | None = None
    direct_response: str | None = None

    @model_validator(mode="after")
    def validate_route_fields(self) -> "ContextualizerDecision":
        if self.route is QueryRoute.RELEVANT:
            if not self.standalone_query:
                raise ValueError("A relevant query requires standalone_query")
            self.direct_response = None
        else:
            if not self.direct_response:
                raise ValueError(
                    "A generic or irrelevant query requires direct_response"
                )
            self.standalone_query = None
        return self

    @property
    def should_retrieve(self) -> bool:
        return self.route is QueryRoute.RELEVANT
