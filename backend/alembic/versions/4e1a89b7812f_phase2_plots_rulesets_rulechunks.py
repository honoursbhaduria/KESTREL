"""phase2_plots_rulesets_rulechunks

Revision ID: 4e1a89b7812f
Revises: 3d2a81a2171a
Create Date: 2026-10-18 21:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from geoalchemy2 import Geometry
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4e1a89b7812f"
down_revision: str | None = "3d2a81a2171a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add ruleset_id to projects
    op.add_column(
        "projects",
        sa.Column("ruleset_id", sa.String(length=100), nullable=True),
    )

    # 2. Plots table
    op.create_table(
        "plots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "boundary",
            Geometry(geometry_type="POLYGON", srid=0, spatial_index=True),
            nullable=True,
        ),
        sa.Column("boundary_coords", postgresql.JSONB, nullable=False),
        sa.Column("original_geo_boundary", postgresql.JSONB, nullable=True),
        sa.Column("north_angle_deg", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("road_sides", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("plot_area_mm2", sa.Float(), nullable=False),
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
    op.create_index("ix_plots_project_id", "plots", ["project_id"], unique=True)

    # 3. Rule chunks table for RAG
    op.create_table(
        "rule_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document", sa.String(length=100), nullable=False),
        sa.Column("section", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("chunk_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_rule_chunks_document", "rule_chunks", ["document"])


def downgrade() -> None:
    op.drop_index("ix_rule_chunks_document", table_name="rule_chunks")
    op.drop_table("rule_chunks")
    op.drop_index("ix_plots_project_id", table_name="plots")
    op.drop_table("plots")
    op.drop_column("projects", "ruleset_id")
