"""Pydantic schemas for projects, plots, and envelope definitions."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from shapely.geometry import Polygon


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    ruleset_id: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str | None
    status: str
    ruleset_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int


class RoadSideItem(BaseModel):
    edge_index: int = Field(..., ge=0, description="0-indexed edge index in boundary polygon")
    road_width_mm: float = Field(default=9000.0, description="Road width in millimetres")
    road_width_m: float | None = Field(default=None, description="Road width in metres")

    @model_validator(mode="before")
    @classmethod
    def normalize_road_width(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "road_width_mm" not in data and "road_width_m" in data:
                data["road_width_mm"] = float(data["road_width_m"]) * 1000.0
            elif "road_width_mm" in data and "road_width_m" not in data:
                data["road_width_m"] = float(data["road_width_mm"]) / 1000.0
        return data


class SetPlotRequest(BaseModel):
    """Payload to define or update a project's spatial plot."""

    # Option A: Simple width × depth (mm)
    width_mm: float | None = Field(default=None, gt=0, description="Plot width in millimetres")
    depth_mm: float | None = Field(default=None, gt=0, description="Plot depth in millimetres")

    # Option B: Explicit 2D polygon vertices in mm
    boundary: list[list[float]] | None = Field(
        default=None,
        description="Plan-local 2D polygon coordinates in mm [[x, y], ...]",
    )
    boundary_coords: list[list[float]] | None = Field(
        default=None,
        description="Alias for boundary",
    )

    # Optional GIS/geographic original boundary (WGS84 lat/long)
    original_geo_boundary: list[list[float]] | None = Field(
        default=None,
        description="WGS84 geographic boundary [[lng, lat], ...]",
    )

    north_angle_deg: float = Field(default=0.0, ge=0.0, le=360.0)
    road_sides: list[RoadSideItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_plot(self) -> "SetPlotRequest":
        if self.boundary is None and self.boundary_coords is not None:
            self.boundary = self.boundary_coords

        # 1. Width × Depth input
        if self.width_mm is not None and self.depth_mm is not None:
            w, d = self.width_mm, self.depth_mm
            coords = [
                [0.0, 0.0],
                [round(w, 2), 0.0],
                [round(w, 2), round(d, 2)],
                [0.0, round(d, 2)],
                [0.0, 0.0],
            ]
            self.boundary = coords

        if not self.boundary:
            raise ValueError(
                "Either (width_mm and depth_mm) or a valid boundary polygon must be provided."
            )

        coords = self.boundary
        # Auto-close if needed
        if coords[0] != coords[-1]:
            coords = list(coords) + [coords[0]]
            self.boundary = coords

        # Must have at least 3 unique vertices (4 points including closure)
        unique_pts = {(pt[0], pt[1]) for pt in coords}
        if len(unique_pts) < 3:
            raise ValueError("Plot polygon must have at least 3 unique vertices.")

        # Check topological validity using Shapely
        try:
            poly = Polygon(coords)
        except Exception as e:
            raise ValueError(f"Malformed polygon coordinates: {e}") from e

        if not poly.is_valid:
            raise ValueError("Self-intersecting or invalid polygon geometry.")

        area_mm2 = poly.area
        # Sane bounds: 10 sqm (10,000,000 mm2) to 1,000,000 sqm (1,000,000,000,000 mm2)
        min_area = 10.0 * 1_000_000.0
        max_area = 1_000_000.0 * 1_000_000.0

        if area_mm2 < min_area:
            raise ValueError(
                f"Plot area ({area_mm2 / 1e6:.1f} sqm) is too small. Minimum supported area is 10 sqm."
            )
        if area_mm2 > max_area:
            raise ValueError(
                f"Plot area ({area_mm2 / 1e6:.1f} sqm) exceeds maximum allowable bounds (1,000,000 sqm)."
            )

        return self


class PlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    boundary: list[list[float]]
    original_geo_boundary: list[list[float]] | None = None
    north_angle_deg: float
    road_sides: list[dict[str, Any]]
    plot_area_mm2: float
    created_at: datetime
    updated_at: datetime


class SetBriefRequest(BaseModel):
    brief_text: str = Field(min_length=1, description="Architectural client brief in free text")


class BriefProgramResponse(BaseModel):
    brief_text: str | None = None
    program: Any
    feasibility: Any


class SetProgramRequest(BaseModel):
    program: Any


class GenerateLayoutRequest(BaseModel):
    num_options: int = Field(default=3, ge=1, le=10, description="Number of scheme options to generate")
    seed: int = Field(default=42, description="RNG seed for deterministic layout generation")


class GeneratedOptionItem(BaseModel):
    id: str
    project_id: str
    name: str
    created_by: str
    score_breakdown: dict[str, Any] | None = None
    description: str = ""
    review_summary: dict[str, Any] = Field(default_factory=dict)
    data: dict[str, Any] | None = None
    created_at: datetime


class GeneratedOptionsResponse(BaseModel):
    options: list[GeneratedOptionItem]


