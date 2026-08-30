"""create extensions

Revision ID: 002_documents_schema
Revises: 001_extensions
Create Date: 2026-09-01
"""
from alembic import op

revision = "002_documents_schema"
down_revision = "001_extensions"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE documents (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_type     TEXT NOT NULL CHECK (source_type IN ('github', 'notion', 'interview', 'correction')),
            source_id       TEXT,
            title           TEXT,
            url             TEXT,
            metadata        JSONB DEFAULT '{}'::jsonb,
            content_hash    TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_documents_source UNIQUE (source_type, source_id)
        )
    """)
    op.execute("COMMENT ON TABLE documents IS 'Top-level sources: GitHub files, Notion pages, interviews, self-learned corrections'")
    op.execute("COMMENT ON COLUMN documents.source_type IS 'github | notion | interview | correction (write-back from Interrogator)'")

def downgrade() -> None:
    op.execute("DROP TABLE documents")