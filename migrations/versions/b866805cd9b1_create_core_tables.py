"""Create the four core tables."""

from alembic import op

revision = "b866805cd9b1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE tenants (
            tenant_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE documents (
            document_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            tenant_id BIGINT NOT NULL
                REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            content_type TEXT NOT NULL,
            size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
            storage_path TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (document_id, tenant_id)
        )
    """)

    op.execute("""
        CREATE TABLE chunks (
            chunk_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            tenant_id BIGINT NOT NULL,
            document_id BIGINT NOT NULL,
            chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            FOREIGN KEY (document_id, tenant_id)
                REFERENCES documents(document_id, tenant_id)
                ON DELETE CASCADE,
            UNIQUE (document_id, chunk_index)
        )
    """)

    op.execute("""
        CREATE TABLE conversations (
            conversation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            tenant_id BIGINT NOT NULL
                REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            title TEXT NOT NULL DEFAULT 'New conversation',
            messages JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE conversations")
    op.execute("DROP TABLE chunks")
    op.execute("DROP TABLE documents")
    op.execute("DROP TABLE tenants")