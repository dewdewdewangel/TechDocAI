"""use BGE-M3 embedding dimensions

Revision ID: 86d4e3f1a003
Revises: 85c3d2e0f002
"""

from alembic import op
from pgvector.sqlalchemy import VECTOR

revision = "86d4e3f1a003"
down_revision = "85c3d2e0f002"
branch_labels = None
depends_on = None


def _invalidate_existing_embeddings() -> None:
    op.execute(
        """
        UPDATE document
        SET status = 'uploaded', error_message = NULL
        WHERE id IN (
            SELECT DISTINCT document_id
            FROM document_chunk
            WHERE embedding IS NOT NULL
        )
        """
    )
    op.execute("UPDATE document_chunk SET embedding = NULL")


def upgrade() -> None:
    _invalidate_existing_embeddings()
    op.alter_column(
        "document_chunk",
        "embedding",
        existing_type=VECTOR(1536),
        type_=VECTOR(1024),
        postgresql_using="embedding::vector(1024)",
        existing_nullable=True,
    )

def downgrade() -> None:
    _invalidate_existing_embeddings()
    op.alter_column(
        "document_chunk",
        "embedding",
        existing_type=VECTOR(1024),
        type_=VECTOR(1536),
        postgresql_using="embedding::vector(1536)",
        existing_nullable=True,
    )
