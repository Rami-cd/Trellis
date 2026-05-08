"""initial schema

Revision ID: 7fa1177d302d
Revises: 
Create Date: 2026-05-08 08:10:20.688791

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from fastapi_users_db_sqlalchemy.generics import GUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7fa1177d302d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "repositories",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("user_id", GUID(), nullable=True),
        sa.Column("source_type", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "repository_languages",
        sa.Column("repo_id", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["repo_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("repo_id", "language"),
    )

    op.create_table(
        "code_nodes",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("repo_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("path", sa.Text(), nullable=True),
        sa.Column("qualified_name", sa.Text(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=True),
        sa.Column("end_line", sa.Integer(), nullable=True),
        sa.Column("start_byte", sa.Integer(), nullable=True),
        sa.Column("end_byte", sa.Integer(), nullable=True),
        sa.Column("raw_source", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "attributes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["repo_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nodes_repo_path", "code_nodes", ["repo_id", "path"], unique=False)
    op.create_index(
        "ix_nodes_name_trgm",
        "code_nodes",
        ["name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )

    op.create_table(
        "code_edges",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=True),
        sa.Column("target_ref", sa.Text(), nullable=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column(
            "attributes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_id"], ["code_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["code_nodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_edges_source_id", "code_edges", ["source_id"], unique=False)
    op.create_index("ix_edges_target_id", "code_edges", ["target_id"], unique=False)
    op.create_index("ix_edges_source_type", "code_edges", ["source_id", "type"], unique=False)
    op.create_index(
        "ix_edges_target_ref_trgm",
        "code_edges",
        ["target_ref"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"target_ref": "gin_trgm_ops"},
    )

    op.create_table(
        "code_embeddings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.ForeignKeyConstraint(["node_id"], ["code_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_id", "chunk_index", name="uq_embeddings_node_chunk"),
    )
    op.create_index("ix_embeddings_node_id", "code_embeddings", ["node_id"], unique=False)
    op.create_index(
        "ix_embeddings_vector",
        "code_embeddings",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
        postgresql_with={"m": 16, "ef_construction": 64},
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("focus_node_id", sa.Text(), nullable=True),
        sa.Column(
            "active_node_ids",
            sa.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("last_query_type", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["focus_node_id"], ["code_nodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"], unique=False)

    op.create_table(
        "indexing_jobs",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("repo_id", sa.Text(), nullable=True),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["repo_id"], ["repositories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_repo_id", "indexing_jobs", ["repo_id"], unique=False)
    op.create_index("ix_jobs_status", "indexing_jobs", ["status"], unique=False)
    op.create_index("ix_jobs_user_id", "indexing_jobs", ["user_id"], unique=False)

    op.create_table(
        "conversations",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("repo_id", sa.Text(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["repo_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_repo_id", "conversations", ["repo_id"], unique=False)
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("conversation_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("nodes_used", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_index("ix_conversations_repo_id", table_name="conversations")
    op.drop_table("conversations")

    op.drop_index("ix_jobs_user_id", table_name="indexing_jobs")
    op.drop_index("ix_jobs_status", table_name="indexing_jobs")
    op.drop_index("ix_jobs_repo_id", table_name="indexing_jobs")
    op.drop_table("indexing_jobs")

    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_table("sessions")

    op.drop_index("ix_embeddings_vector", table_name="code_embeddings", postgresql_using="hnsw")
    op.drop_index("ix_embeddings_node_id", table_name="code_embeddings")
    op.drop_table("code_embeddings")

    op.drop_index("ix_edges_target_ref_trgm", table_name="code_edges", postgresql_using="gin")
    op.drop_index("ix_edges_source_type", table_name="code_edges")
    op.drop_index("ix_edges_target_id", table_name="code_edges")
    op.drop_index("ix_edges_source_id", table_name="code_edges")
    op.drop_table("code_edges")

    op.drop_index("ix_nodes_name_trgm", table_name="code_nodes", postgresql_using="gin")
    op.drop_index("ix_nodes_repo_path", table_name="code_nodes")
    op.drop_table("code_nodes")

    op.drop_table("repository_languages")
    op.drop_table("repositories")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
