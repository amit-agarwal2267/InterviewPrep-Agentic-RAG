"""create extensions

Revision ID: 005_indexes_triggers
Revises: 004_knowledge_gaps
Create Date: 2026-09-01
"""
from alembic import op

revision = "005_indexes_triggers"
down_revision = "004_knowledge_gaps"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        CREATE INDEX idx_chunks_embedding_hnsw
            ON chunks USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
    """)
    op.execute("COMMENT ON INDEX idx_chunks_embedding_hnsw IS 'HNSW index for dense vector search (cosine)'")

    op.execute("CREATE INDEX idx_chunks_content_tsv ON chunks USING GIN (content_tsv)")
    op.execute("COMMENT ON INDEX idx_chunks_content_tsv IS 'GIN index for lexical/full-text search (ts_rank_cd)'")

    op.execute("CREATE INDEX idx_documents_source_type ON documents (source_type)")
    op.execute("CREATE INDEX idx_chunks_document_id ON chunks (document_id)")
    op.execute("CREATE INDEX idx_chunks_chunk_type ON chunks (chunk_type)")
    op.execute("CREATE INDEX idx_chunks_parent_id ON chunks (parent_id) WHERE parent_id IS NOT NULL")
    op.execute("CREATE INDEX idx_documents_metadata ON documents USING GIN (metadata)")
    op.execute("CREATE INDEX idx_chunks_metadata ON chunks USING GIN (metadata)")
    op.execute("CREATE INDEX idx_knowledge_gaps_status ON knowledge_gaps (status)")
    op.execute("CREATE INDEX idx_knowledge_gaps_thread_id ON knowledge_gaps (thread_id)")

    op.execute("""
        CREATE OR REPLACE FUNCTION update_content_tsv()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.content_tsv := to_tsvector('english', COALESCE(NEW.content, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_chunks_tsv_update
            BEFORE INSERT OR UPDATE OF content ON chunks
            FOR EACH ROW EXECUTE FUNCTION update_content_tsv()
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_documents_updated_at
            BEFORE UPDATE ON documents
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)
    op.execute("""
        CREATE TRIGGER trg_knowledge_gaps_updated_at
            BEFORE UPDATE ON knowledge_gaps
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    op.execute("""
        CREATE OR REPLACE VIEW v_chunks_with_source AS
        SELECT
            c.id, c.content, c.embedding, c.chunk_index, c.token_count,
            c.chunk_type, c.image_url, c.metadata AS chunk_metadata,
            d.id AS document_id, d.source_type, d.source_id, d.title, d.url,
            d.metadata AS document_metadata
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
    """)
    op.execute("COMMENT ON VIEW v_chunks_with_source IS 'Convenient join of chunks + document metadata for retrieval'")


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_chunks_with_source")
    op.execute("DROP TRIGGER IF EXISTS trg_knowledge_gaps_updated_at ON knowledge_gaps")
    op.execute("DROP TRIGGER IF EXISTS trg_documents_updated_at ON documents")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
    op.execute("DROP TRIGGER IF EXISTS trg_chunks_tsv_update ON chunks")
    op.execute("DROP FUNCTION IF EXISTS update_content_tsv()")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_gaps_thread_id")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_gaps_status")
    op.execute("DROP INDEX IF EXISTS idx_chunks_metadata")
    op.execute("DROP INDEX IF EXISTS idx_documents_metadata")
    op.execute("DROP INDEX IF EXISTS idx_chunks_parent_id")
    op.execute("DROP INDEX IF EXISTS idx_chunks_chunk_type")
    op.execute("DROP INDEX IF EXISTS idx_chunks_document_id")
    op.execute("DROP INDEX IF EXISTS idx_documents_source_type")
    op.execute("DROP INDEX IF EXISTS idx_chunks_content_tsv")
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding_hnsw")