from sqlalchemy import text

from interview_prep_qna.core.agent.state import RetrievedEvidence
from interview_prep_qna.db.client.postgres import get_session
from interview_prep_qna.knowledge_base.embedder import embed_query


async def dense_search(query: str, limit: int = 40) -> list[RetrievedEvidence]:
    """Search pgvector with cosine distance; PostgreSQL can use the HNSW index."""
    if not query.strip():
        raise ValueError("query must not be empty")
    if limit < 1:
        raise ValueError("limit must be positive")

    embedding = await embed_query(query)
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT
                    c.id::text AS chunk_id,
                    c.document_id::text AS document_id,
                    c.content,
                    c.chunk_index,
                    c.metadata,
                    d.source_type,
                    d.source_id,
                    d.title,
                    d.url,
                    c.image_url,
                    1 - (c.embedding <=> CAST(:embedding AS vector)) AS dense_score
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.embedding IS NOT NULL
                ORDER BY c.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """),
            {"embedding": str(embedding), "limit": limit},
        )
        rows = result.mappings().all()

    return [
        RetrievedEvidence(
            **dict(row),
            dense_rank=rank,
        )
        for rank, row in enumerate(rows, start=1)
    ]
