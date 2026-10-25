from alembic import op
import sqlalchemy as sa

revision = "04ea6615bda8"
down_revision = "b866805cd9b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("content_hash", sa.Text(), nullable=True),
    )

    op.execute(
        "UPDATE documents "
        "SET content_hash = 'legacy-' || document_id::text "
        "WHERE content_hash IS NULL"
    )

    op.alter_column(
        "documents",
        "content_hash",
        existing_type=sa.Text(),
        nullable=False,
    )

    op.create_unique_constraint(
        "uq_documents_tenant_content_hash",
        "documents",
        ["tenant_id", "content_hash"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_documents_tenant_content_hash",
        "documents",
        type_="unique",
    )
    op.drop_column("documents", "content_hash")