"""Initial schema — all tables

Revision ID: 0001
Revises: None
Create Date: 2026-10-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Users ─────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("username", sa.String(100), unique=True, index=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("is_admin", sa.Boolean(), default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Conversations ─────────────────────────────
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), default="New Conversation"),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Messages ──────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Documents ─────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("status", sa.String(20), default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), default=0),
        sa.Column("storage_path", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Document Chunks ───────────────────────────
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), default=0),
        sa.Column("vector_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Citations ─────────────────────────────────
    op.create_table(
        "citations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(36), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("chunk_id", sa.String(36), nullable=True),
        sa.Column("source_title", sa.String(500), nullable=False),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("citation_index", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Integrations ──────────────────────────────
    op.create_table(
        "integrations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tool_type", sa.String(50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), default=True, nullable=False),
        sa.Column("requires_auth", sa.Boolean(), default=False, nullable=False),
        sa.Column("config_schema", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Tool Executions ───────────────────────────
    op.create_table(
        "tool_executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("integration_id", sa.String(36), sa.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("input_data", sa.Text(), nullable=True),
        sa.Column("output_data", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("tool_executions")
    op.drop_table("integrations")
    op.drop_table("citations")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("users")
