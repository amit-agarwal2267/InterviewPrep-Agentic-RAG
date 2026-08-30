"""create extensions

Revision ID: 003_chunks_schema
Revises: 002_documents_schema
Create Date: 2026-09-01
"""
from alembic import op

revision = "003_chunks_schema"
down_revision = "002_documents_schema"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE chunks (
            id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id           UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            content               TEXT NOT NULL,
            content_tsv           TSVECTOR,
            embedding             VECTOR(768),
            embedding_input_type  TEXT DEFAULT 'text' CHECK (embedding_input_type IN ('text', 'image', 'text+image')),
            chunk_index           INT,
            start_char            INT,
            end_char               INT,
            token_count           INT,
            parent_id             UUID REFERENCES chunks(id) ON DELETE SET NULL,
            chunk_type            TEXT DEFAULT 'text',
            image_url             TEXT,
            metadata              JSONB DEFAULT '{}'::jsonb,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_chunks_doc_index UNIQUE (document_id, chunk_index)
        )
    """)
    op.execute("COMMENT ON TABLE chunks IS 'Chunked content ready for hybrid retrieval (HNSW + lexical full-text)'")
    op.execute("COMMENT ON COLUMN chunks.embedding IS 'Gemini Embedding 2, truncated to 768 dims'")
    op.execute("COMMENT ON COLUMN chunks.embedding_input_type IS 'Was the source content text, an image, or both, when embedded'")
    op.execute("COMMENT ON COLUMN chunks.chunk_type IS 'diagram = architecture image from README/Notion'")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chunks")