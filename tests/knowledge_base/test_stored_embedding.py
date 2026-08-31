from uuid import uuid4

import pytest
from sqlalchemy import text

from interview_prep_qna.core.pipeline import ingest_document
from interview_prep_qna.db.client.postgres import get_session


@pytest.mark.integration
@pytest.mark.asyncio
async def test_embedding_is_stored_in_pgvector() -> None:
    source_id = f"pytest-{uuid4()}"
    content = "A B-tree index keeps ordered keys for efficient database lookups."
    inserted = False
    try:
        changed = await ingest_document(
            source_type="correction",
            source_id=source_id,
            title="Pytest stored embedding",
            url=None,
            content=content,
        )
        assert changed is True
        inserted = True

        async with get_session() as session:
            result = await session.execute(
                text("""
                    SELECT c.content, vector_dims(c.embedding) AS dimensions
                    FROM chunks c
                    JOIN documents d ON d.id = c.document_id
                    WHERE d.source_type = 'correction' AND d.source_id = :source_id
                """),
                {"source_id": source_id},
            )
            rows = result.mappings().all()

        print("\nStored pgvector rows:\n", [dict(row) for row in rows])
        assert rows
        assert rows[0]["content"] == content
        assert rows[0]["dimensions"] == 768
    finally:
        if inserted:
            async with get_session() as session:
                await session.execute(
                    text(
                        "DELETE FROM documents WHERE source_type = 'correction' AND source_id = :source_id"
                    ),
                    {"source_id": source_id},
                )
                await session.commit()
