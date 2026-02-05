"""create extraction and rag tables for phase 6

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-05

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create extraction_jobs table
    op.create_table(
        "extraction_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("schema_name", sa.Text(), nullable=True),
        sa.Column(
            "schema_definition",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("top_k", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column(
            "min_confidence", sa.Float(), nullable=False, server_default=sa.text("0.7")
        ),
    )

    # Create indexes for extraction_jobs
    op.create_index(
        "idx_extraction_jobs_tenant_status",
        "extraction_jobs",
        ["tenant_id", "status"],
    )
    op.create_index(
        "idx_extraction_jobs_tenant",
        "extraction_jobs",
        ["tenant_id"],
    )
    op.create_index(
        "idx_extraction_jobs_created",
        "extraction_jobs",
        ["created_at"],
    )

    # Create extraction_results table
    op.create_table(
        "extraction_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extraction_jobs.id"),
            nullable=False,
        ),
        sa.Column("source_doc_id", sa.Text(), nullable=True),
        sa.Column("source_chunk_index", sa.Integer(), nullable=True),
        sa.Column("source_tenant_id", sa.Text(), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column(
            "confidence", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column(
            "is_valid", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "validation_errors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Create indexes for extraction_results
    op.create_index(
        "idx_extraction_results_job",
        "extraction_results",
        ["job_id"],
    )
    op.create_index(
        "idx_extraction_results_confidence",
        "extraction_results",
        ["confidence"],
    )
    op.create_index(
        "idx_extraction_results_valid",
        "extraction_results",
        ["is_valid"],
    )

    # Create extracted_entities table
    op.create_table(
        "extracted_entities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extraction_results.id"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column(
            "attributes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("source_doc_id", sa.Text(), nullable=True),
        sa.Column("source_version", sa.Integer(), nullable=True),
        sa.Column(
            "confidence", sa.Float(), nullable=False, server_default=sa.text("0.0")
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

    # Create indexes for extracted_entities
    op.create_index(
        "idx_extracted_entities_type",
        "extracted_entities",
        ["entity_type"],
    )
    op.create_index(
        "idx_extracted_entities_name",
        "extracted_entities",
        ["name"],
    )
    op.create_index(
        "idx_extracted_entities_confidence",
        "extracted_entities",
        ["confidence"],
    )
    op.create_index(
        "idx_extracted_entities_result",
        "extracted_entities",
        ["result_id"],
    )

    # Create rag_conversations table
    op.create_table(
        "rag_conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column(
            "context_chunks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column(
            "citations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "confidence", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("backend", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Create indexes for rag_conversations
    op.create_index(
        "idx_rag_conversations_tenant",
        "rag_conversations",
        ["tenant_id"],
    )
    op.create_index(
        "idx_rag_conversations_session",
        "rag_conversations",
        ["session_id"],
    )
    op.create_index(
        "idx_rag_conversations_created",
        "rag_conversations",
        ["created_at"],
    )


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index("idx_rag_conversations_created", table_name="rag_conversations")
    op.drop_index("idx_rag_conversations_session", table_name="rag_conversations")
    op.drop_index("idx_rag_conversations_tenant", table_name="rag_conversations")
    op.drop_table("rag_conversations")

    op.drop_index("idx_extracted_entities_result", table_name="extracted_entities")
    op.drop_index("idx_extracted_entities_confidence", table_name="extracted_entities")
    op.drop_index("idx_extracted_entities_name", table_name="extracted_entities")
    op.drop_index("idx_extracted_entities_type", table_name="extracted_entities")
    op.drop_table("extracted_entities")

    op.drop_index("idx_extraction_results_valid", table_name="extraction_results")
    op.drop_index("idx_extraction_results_confidence", table_name="extraction_results")
    op.drop_index("idx_extraction_results_job", table_name="extraction_results")
    op.drop_table("extraction_results")

    op.drop_index("idx_extraction_jobs_created", table_name="extraction_jobs")
    op.drop_index("idx_extraction_jobs_tenant", table_name="extraction_jobs")
    op.drop_index("idx_extraction_jobs_tenant_status", table_name="extraction_jobs")
    op.drop_table("extraction_jobs")
