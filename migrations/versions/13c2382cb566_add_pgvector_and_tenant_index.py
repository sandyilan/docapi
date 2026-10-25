from alembic import op

revision = "13c2382cb566"
down_revision = "04ea6615bda8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        "ALTER TABLE chunks "
        "ADD COLUMN IF NOT EXISTS embedding vector(3)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunks_tenant_id "
        "ON chunks (tenant_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chunks_tenant_id")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS embedding")