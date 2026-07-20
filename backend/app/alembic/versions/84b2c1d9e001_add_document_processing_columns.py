from alembic import op
import sqlalchemy as sa

revision = "84b2c1d9e001"
down_revision = "83d57a753d95"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document",
        sa.Column(
            "chunk_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "document",
        sa.Column(
            "error_message",
            sa.String(length=2000),
            nullable=True,
        ),
    )
    op.alter_column("document", "chunk_count", server_default=None)


def downgrade() -> None:
    op.drop_column("document", "error_message")
    op.drop_column("document", "chunk_count")
