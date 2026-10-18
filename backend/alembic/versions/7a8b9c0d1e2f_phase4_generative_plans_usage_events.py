"""Phase 4: Usage events, project brief/program, and plan generative metadata.

Revision ID: 7a8b9c0d1e2f
Revises: 0d1cb1de835f
Create Date: 2026-10-18 23:25:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "7a8b9c0d1e2f"
down_revision: Union[str, None] = "0d1cb1de835f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create usage_events table
    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("kind", sa.String(100), nullable=False, index=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 2. Add columns to projects table
    op.add_column("projects", sa.Column("brief_text", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("program_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # 3. Add columns to plans table
    op.add_column("plans", sa.Column("created_by", sa.String(50), nullable=False, server_default="user"))
    op.add_column("plans", sa.Column("score_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("plans", sa.Column("description", sa.String(1000), nullable=True))


def downgrade() -> None:
    op.drop_column("plans", "description")
    op.drop_column("plans", "score_breakdown")
    op.drop_column("plans", "created_by")

    op.drop_column("projects", "program_data")
    op.drop_column("projects", "brief_text")

    op.drop_table("usage_events")
