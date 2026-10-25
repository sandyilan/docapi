"""use 768 dimension embeddings

Revision ID: 23d77df3ee48
Revises: 13c2382cb566
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector


revision: str = "23d77df3ee48"
down_revision: Union[str, None] = "13c2382cb566"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep the old 3-dimensional test vectors under a new name.
    op.alter_column(
        "chunks",
        "embedding",
        new_column_name="embedding_legacy",
        existing_type=Vector(3),
        existing_nullable=True,
    )

    # Add an empty column for new 768-dimensional embeddings.
    op.add_column(
        "chunks",
        sa.Column("embedding", Vector(768), nullable=True),
    )


def downgrade() -> None:
    # Remove the new column, then restore the old column name.
    op.drop_column("chunks", "embedding")
    op.alter_column(
        "chunks",
        "embedding_legacy",
        new_column_name="embedding",
        existing_type=Vector(3),
        existing_nullable=True,
    )