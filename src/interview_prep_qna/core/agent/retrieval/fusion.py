from interview_prep_qna.core.agent.state import RetrievedEvidence


def reciprocal_rank_fusion(
    dense_results: list[RetrievedEvidence],
    lexical_results: list[RetrievedEvidence],
    *,
    limit: int = 10,
    rrf_k: int = 60,
) -> list[RetrievedEvidence]:
    """Fuse independent result rankings using reciprocal rank fusion."""
    if limit < 1:
        raise ValueError("limit must be positive")
    if rrf_k < 1:
        raise ValueError("rrf_k must be positive")

    fused: dict[str, RetrievedEvidence] = {}
    scores: dict[str, float] = {}
    for rank, evidence in enumerate(dense_results, start=1):
        item = evidence.model_copy(deep=True)
        item.dense_rank = rank
        fused[item.chunk_id] = item
        scores[item.chunk_id] = scores.get(item.chunk_id, 0.0) + 1 / (rrf_k + rank)

    for rank, evidence in enumerate(lexical_results, start=1):
        if evidence.chunk_id in fused:
            item = fused[evidence.chunk_id]
            item.lexical_score = evidence.lexical_score
            item.lexical_rank = rank
        else:
            item = evidence.model_copy(deep=True)
            item.lexical_rank = rank
            fused[item.chunk_id] = item
        scores[item.chunk_id] = scores.get(item.chunk_id, 0.0) + 1 / (rrf_k + rank)

    for chunk_id, score in scores.items():
        fused[chunk_id].fusion_score = score
    return sorted(fused.values(), key=lambda item: item.fusion_score, reverse=True)[
        :limit
    ]
