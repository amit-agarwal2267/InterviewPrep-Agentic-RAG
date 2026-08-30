"""create extensions

Revision ID: 004_knowledge_gaps
Revises: 003_chunks_schema
Create Date: 2026-09-01
"""
from alembic import op

revision = "004_knowledge_gaps"
down_revision = "003_chunks_schema"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE knowledge_gaps (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            thread_id           TEXT NOT NULL,
            query               TEXT NOT NULL,
            gap_description     TEXT,
            resolved_content    TEXT,
            document_id         UUID REFERENCES documents(id) ON DELETE SET NULL,
            follow_up_count     INT NOT NULL DEFAULT 0 CHECK (follow_up_count BETWEEN 0 AND 2),
            status              TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'saved', 'discarded')),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("COMMENT ON TABLE knowledge_gaps IS 'Gaps detected by the Interrogator LLM, tied to a conversation thread'")
    op.execute("COMMENT ON COLUMN knowledge_gaps.status IS 'discarded = budget exhausted or answer not confident enough'")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS knowledge_gaps")