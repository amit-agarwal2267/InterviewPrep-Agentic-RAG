"""create extensions

Revision ID: 006_hybrid_search_function
Revises: 005_indexes_triggers
Create Date: 2026-09-01
"""
from alembic import op

revision = "006_hybrid_search_function"
down_revision = "005_indexes_triggers"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION hybrid_search(
            query_embedding VECTOR(768),
            query_text      TEXT,
            match_count     INT DEFAULT 10,
            rrf_k           INT DEFAULT 60
        )
        RETURNS TABLE (
            chunk_id     UUID,
            content      TEXT,
            document_id  UUID,
            source_type  TEXT,
            title        TEXT,
            final_score  FLOAT
        ) AS $$
        BEGIN
            RETURN QUERY
            WITH dense AS (
                SELECT
                    c.id,
                    ROW_NUMBER() OVER (ORDER BY c.embedding <=> query_embedding) AS rank
                FROM chunks c
                WHERE c.embedding IS NOT NULL
                ORDER BY c.embedding <=> query_embedding
                LIMIT match_count * 4
            ),
            sparse AS (
                SELECT
                    c.id,
                    ROW_NUMBER() OVER (
                        ORDER BY ts_rank_cd(c.content_tsv, plainto_tsquery('english', query_text)) DESC
                    ) AS rank
                FROM chunks c
                WHERE c.content_tsv @@ plainto_tsquery('english', query_text)
                LIMIT match_count * 4
            ),
            fused AS (
                SELECT
                    COALESCE(d.id, s.id) AS id,
                    (1.0 / (rrf_k + COALESCE(d.rank, 1000000)))
                    + (1.0 / (rrf_k + COALESCE(s.rank, 1000000))) AS rrf_score
                FROM dense d
                FULL OUTER JOIN sparse s ON d.id = s.id
            )
            SELECT
                c.id,
                c.content,
                c.document_id,
                doc.source_type,
                doc.title,
                f.rrf_score
            FROM fused f
            JOIN chunks c ON c.id = f.id
            JOIN documents doc ON doc.id = c.document_id
            ORDER BY f.rrf_score DESC
            LIMIT match_count;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("COMMENT ON FUNCTION hybrid_search IS 'Fuses dense (pgvector cosine) and lexical (ts_rank_cd) search via reciprocal rank fusion'")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS hybrid_search(VECTOR, TEXT, INT, INT)")