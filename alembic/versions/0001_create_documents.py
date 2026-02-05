"""create documents table

Revision ID: 0001
Revises:
Create Date: 2026-02-04

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "latest", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("raw_object_key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "idx_documents_tenant_source_latest",
        "documents",
        ["tenant_id", "source", "source_id", "latest"],
    )

    op.create_index(
        "idx_documents_hash",
        "documents",
        ["tenant_id", "content_hash"],
    )

    op.create_unique_constraint(
        "uniq_documents_version",
        "documents",
        ["tenant_id", "source", "source_id", "version"],
    )


def downgrade() -> None:
    op.drop_constraint("uniq_documents_version", "documents", type_="unique")
    op.drop_index("idx_documents_hash", table_name="documents")
    op.drop_index("idx_documents_tenant_source_latest", table_name="documents")
    op.drop_table("documents")
