from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from interview_prep_qna.core.agent.enums import (
    AgentRoute,
    GradingAction,
    GroundingAlignment,
    InterrogationPhase,
    QueryRoute,
    RouteDestination,
)


class RetrievedEvidence(BaseModel):
    """A normalized evidence item shared by retrieval and answer agents."""

    chunk_id: str
    document_id: str
    content: str
    source_type: str
    source_id: str | None = None
    title: str | None = None
    url: str | None = None
    image_url: str | None = None
    chunk_index: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    dense_score: float | None = None
    lexical_score: float | None = None
    dense_rank: int | None = None
    lexical_rank: int | None = None
    fusion_score: float = 0.0


class RetrievalMetadata(BaseModel):
    dense_candidates: int = 0
    lexical_candidates: int = 0
    fused_candidates: int = 0
    limit: int = 0
    rrf_k: int = 60


class AgentError(TypedDict, total=False):
    agent: str
    error_type: str
    message: str
    retryable: bool


class ContextualizerDecisionState(TypedDict, total=False):
    route: QueryRoute
    reason: str
    standalone_query: str | None
    direct_response: str | None


class RouterDecisionState(TypedDict, total=False):
    destination: RouteDestination
    reason: str


class GradingDecisionState(TypedDict, total=False):
    action: GradingAction
    sufficient: bool
    reason: str
    missing_information: list[str]


class EscalationStep(TypedDict, total=False):
    source: str
    results: int
    error: str | None


class SummarizerDecisionState(TypedDict, total=False):
    alignment: GroundingAlignment
    has_knowledge_gap: bool
    gap_reason: str | None
    follow_up_questions: list[str]


class KnowledgeGapState(TypedDict, total=False):
    reason: str
    questions: list[str]
    alignment: GroundingAlignment


class Clarification(TypedDict):
    question: str
    answer: str


class InterrogationState(TypedDict, total=False):
    id: str
    phase: InterrogationPhase
    questions_asked: list[str]
    clarifications: list[Clarification]
    satisfied: bool
    consent_granted: bool
    saved: bool
    storage_changed: bool


class WriteBackState(TypedDict, total=False):
    source_type: str
    source_id: str
    changed: bool


class CommonAgentState(TypedDict, total=False):
    """Conversation and execution fields available to every graph node."""

    request_id: str
    session_id: str
    user_id: str
    query: str
    contextualized_query: str
    messages: Annotated[list[BaseMessage], add_messages]
    route: AgentRoute
    current_agent: str
    response: str
    metadata: dict[str, Any]
    errors: list[AgentError]


class AgentState(CommonAgentState, total=False):
    """Canonical state contract shared across the complete agent graph."""

    contextualization: ContextualizerDecisionState
    routing: RouterDecisionState
    retrieved_evidence: list[RetrievedEvidence]
    retrieval_metadata: RetrievalMetadata
    grading: GradingDecisionState
    escalation_steps: list[EscalationStep]
    draft_response: str
    summarization: SummarizerDecisionState
    knowledge_gap: KnowledgeGapState
    interrogation: InterrogationState
    write_back: WriteBackState
