"""Phase 5: Assistant conversations, messages, and fix proposals.

Revision ID: 8b9c0d1e2f3a
Revises: 7a8b9c0d1e2f
Create Date: 2026-10-19 03:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "8b9c0d1e2f3a"
down_revision: str | None = "7a8b9c0d1e2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create conversations table
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversations_plan_id"), "conversations", ["plan_id"], unique=False)
    op.create_index(op.f("ix_conversations_org_id"), "conversations", ["org_id"], unique=False)

    # 2. Create messages table
    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("tool_calls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tool_call_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_messages_conversation_id"), "messages", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_messages_org_id"), "messages", ["org_id"], unique=False)

    # 3. Create fixes table
    op.create_table(
        "fixes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("rule_id", sa.String(length=128), nullable=False),
        sa.Column("clause", sa.String(length=255), nullable=True),
        sa.Column("patch_ops", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("diff_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("introduced_fails", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("applied_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fixes_plan_id"), "fixes", ["plan_id"], unique=False)
    op.create_index(op.f("ix_fixes_org_id"), "fixes", ["org_id"], unique=False)
    op.create_index(op.f("ix_fixes_status"), "fixes", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_fixes_status"), table_name="fixes")
    op.drop_index(op.f("ix_fixes_org_id"), table_name="fixes")
    op.drop_index(op.f("ix_fixes_plan_id"), table_name="fixes")
    op.drop_table("fixes")

    op.drop_index(op.f("ix_messages_org_id"), table_name="messages")
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
    op.drop_table("messages")

    op.drop_index(op.f("ix_conversations_org_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_plan_id"), table_name="conversations")
    op.drop_table("conversations")
