from sqlalchemy import text

from interview_prep_qna.core.agent.state import RetrievedEvidence
from interview_prep_qna.db.client.postgres import get_session


async def lexical_search(query: str, limit: int = 40) -> list[RetrievedEvidence]:
    """Search the generated tsvector using PostgreSQL ts_rank_cd ranking."""
    if not query.strip():
        raise ValueError("query must not be empty")
    if limit < 1:
        raise ValueError("limit must be positive")

    async with get_session() as session:
        result = await session.execute(
            text("""
                WITH parsed_query AS (
                    SELECT websearch_to_tsquery('english', :query) AS value
                )
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
                    ts_rank_cd(c.content_tsv, parsed_query.value) AS lexical_score
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                CROSS JOIN parsed_query
                WHERE c.content_tsv @@ parsed_query.value
                ORDER BY lexical_score DESC
                LIMIT :limit
            """),
            {"query": query, "limit": limit},
        )
        rows = result.mappings().all()

    return [
        RetrievedEvidence(
            **dict(row),
            lexical_rank=rank,
        )
        for rank, row in enumerate(rows, start=1)
    ]
