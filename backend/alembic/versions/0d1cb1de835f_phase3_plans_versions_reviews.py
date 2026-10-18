"""phase3_plans_versions_reviews

Revision ID: 0d1cb1de835f
Revises: 4e1a89b7812f
Create Date: 2026-10-18 22:45:48.270114

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0d1cb1de835f"
down_revision: str | Sequence[str] | None = "4e1a89b7812f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Plans table
    op.create_table(
        "plans",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_plans_org_id"), "plans", ["org_id"], unique=False)
    op.create_index(op.f("ix_plans_project_id"), "plans", ["project_id"], unique=False)

    # 2. Plan versions table
    op.create_table(
        "plan_versions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "plan_id", sa.UUID(), sa.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("parent_version", sa.Integer(), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.String(length=50), nullable=False, server_default="user"),
        sa.Column("message", sa.String(length=500), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_plan_versions_plan_id"), "plan_versions", ["plan_id"], unique=False)

    # 3. Plan reviews table
    op.create_table(
        "plan_reviews",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "plan_id", sa.UUID(), sa.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("issues", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_plan_reviews_plan_id"), "plan_reviews", ["plan_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_plan_reviews_plan_id"), table_name="plan_reviews")
    op.drop_table("plan_reviews")
    op.drop_index(op.f("ix_plan_versions_plan_id"), table_name="plan_versions")
    op.drop_table("plan_versions")
    op.drop_index(op.f("ix_plans_project_id"), table_name="plans")
    op.drop_index(op.f("ix_plans_org_id"), table_name="plans")
    op.drop_table("plans")
