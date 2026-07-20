"""add chunk embedding

Revision ID: 85c3d2e0f002
Revises: 84b2c1d9e001
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR

revision = "85c3d2e0f002"
down_revision = "84b2c1d9e001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "document_chunk",
        sa.Column(
            "embedding",
            VECTOR(1536),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_document_owner_id",
        "document",
        ["owner_id"],
    )
    op.create_index(
        "ix_document_chunk_document_id",
        "document_chunk",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_chunk_document_id",
        table_name="document_chunk",
    )
    op.drop_index(
        "ix_document_owner_id",
        table_name="document",
    )
    op.drop_column("document_chunk", "embedding")
