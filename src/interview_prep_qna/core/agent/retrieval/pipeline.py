import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from interview_prep_qna.core.agent.retrieval.dense import dense_search
from interview_prep_qna.core.agent.retrieval.fusion import reciprocal_rank_fusion
from interview_prep_qna.core.agent.retrieval.lexical import lexical_search
from interview_prep_qna.core.agent.state import (
    AgentState,
    RetrievalMetadata,
    RetrievedEvidence,
)
from interview_prep_qna.observability import get_langfuse_client

if TYPE_CHECKING:
    from interview_prep_qna.core.agent.grading import GradingAgent

SearchFunction = Callable[[str, int], Awaitable[list[RetrievedEvidence]]]


class RAGPipeline:
    def __init__(
        self,
        dense_retriever: SearchFunction = dense_search,
        lexical_retriever: SearchFunction = lexical_search,
        *,
        candidate_limit: int = 40,
        result_limit: int = 10,
        rrf_k: int = 60,
        grading_agent: "GradingAgent | None" = None,
    ) -> None:
        self._dense_retriever = dense_retriever
        self._lexical_retriever = lexical_retriever
        self.candidate_limit = candidate_limit
        self.result_limit = result_limit
        self.rrf_k = rrf_k
        self._grading_agent = grading_agent

    async def retrieve(self, query: str, state: AgentState | None = None) -> AgentState:
        if not query.strip():
            raise ValueError("query must not be empty")

        with get_langfuse_client().start_as_current_observation(
            name="hybrid-retrieval",
            as_type="retriever",
            input={"query": query, "candidate_limit": self.candidate_limit},
        ) as observation:
            dense, lexical = await asyncio.gather(
                self._dense_retriever(query, self.candidate_limit),
                self._lexical_retriever(query, self.candidate_limit),
            )
            fused = reciprocal_rank_fusion(
                dense,
                lexical,
                limit=self.result_limit,
                rrf_k=self.rrf_k,
            )
            metadata = RetrievalMetadata(
                dense_candidates=len(dense),
                lexical_candidates=len(lexical),
                fused_candidates=len(fused),
                limit=self.result_limit,
                rrf_k=self.rrf_k,
            )
            observation.update(
                output={
                    "chunk_ids": [item.chunk_id for item in fused],
                    **metadata.model_dump(),
                }
            )

        updated: AgentState = dict(state or {})
        updated["query"] = updated.get("query", query)
        updated["contextualized_query"] = query
        updated["retrieved_evidence"] = fused
        updated["retrieval_metadata"] = metadata
        return updated

    async def run(self, query: str, state: AgentState | None = None) -> AgentState:
        """Retrieve evidence into state and hand it to the GradingAgent."""
        retrieved_state = await self.retrieve(query, state)
        if self._grading_agent is None:
            from interview_prep_qna.core.agent.grading import GradingAgent

            self._grading_agent = GradingAgent()
        return await self._grading_agent.resolve(retrieved_state)
