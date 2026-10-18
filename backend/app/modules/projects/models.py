"""SQLAlchemy models for projects and plots."""

import uuid
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel, TenantBaseModel


class Project(TenantBaseModel):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    ruleset_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    plot: Mapped["Plot | None"] = relationship(
        "Plot",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Plot(BaseModel):
    __tablename__ = "plots"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # PostGIS geometry polygon
    boundary = mapped_column(
        Geometry(geometry_type="POLYGON", srid=0, spatial_index=True),
        nullable=True,
    )
    # Local metric coordinates [[x, y], ...] in mm
    boundary_coords: Mapped[list[list[float]]] = mapped_column(JSONB, nullable=False)
    # Original WGS84 coordinates if drawn on map [[lng, lat], ...]
    original_geo_boundary: Mapped[list[list[float]] | None] = mapped_column(
        JSONB, nullable=True
    )
    north_angle_deg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    road_sides: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    plot_area_mm2: Mapped[float] = mapped_column(Float, nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="plot")
