"""Core Plan schemas and spatial validation invariants (Phase 3)."""

from typing import Any, Literal
import math
from pydantic import BaseModel, Field, field_validator, model_validator
from shapely.geometry import Polygon


class Room(BaseModel):
    """Room in a level with spatial boundary polygon."""

    id: str
    type: str = Field(description="Room function: living, bedroom, kitchen, bathroom, etc.")
    name: str = Field(description="Architectural room label")
    polygon: list[list[float]] = Field(description="2D vertices in millimetres [[x, y], ...]")

    @field_validator("polygon")
    @classmethod
    def validate_room_polygon(cls, v: list[list[float]]) -> list[list[float]]:
        if len(v) < 3:
            raise ValueError("Room polygon must have at least 3 vertices.")
        poly = Polygon(v)
        if not poly.is_valid:
            raise ValueError(f"Room polygon is topologically invalid (self-intersecting or degenerate).")
        if poly.area <= 0:
            raise ValueError("Room polygon area must be greater than zero.")
        return v

    @property
    def area_mm2(self) -> float:
        return float(Polygon(self.polygon).area)

    @property
    def area_sqm(self) -> float:
        return self.area_mm2 / 1_000_000.0


class Wall(BaseModel):
    """Linear wall element with start, end, thickness and height in millimetres."""

    id: str
    start: list[float] = Field(description="[x, y] coordinates in mm")
    end: list[float] = Field(description="[x, y] coordinates in mm")
    thickness_mm: float = 200.0
    height_mm: float = 3000.0
    is_external: bool = False

    @field_validator("start", "end")
    @classmethod
    def validate_coord(cls, v: list[float]) -> list[float]:
        if len(v) != 2:
            raise ValueError("Wall coordinates must be [x, y].")
        return [float(v[0]), float(v[1])]

    @property
    def length_mm(self) -> float:
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        return math.hypot(dx, dy)


class Opening(BaseModel):
    """Door or window opening embedded in a host wall."""

    id: str
    wall_id: str
    kind: Literal["door", "window"]
    offset_mm: float = Field(description="Offset along wall from start point in mm")
    width_mm: float = Field(description="Opening width in mm")
    height_mm: float = Field(description="Opening height in mm")
    sill_mm: float = 0.0
    swing: str | None = None


class Stair(BaseModel):
    """Stair flight definition with step geometry."""

    id: str
    polygon: list[list[float]]
    riser_mm: float = 175.0
    tread_mm: float = 250.0
    direction: Literal["up", "down"] = "up"


class Level(BaseModel):
    """Building level containing architectural elements."""

    id: str
    name: str
    elevation_mm: float = 0.0
    floor_to_floor_mm: float = 3000.0
    rooms: list[Room] = Field(default_factory=list)
    walls: list[Wall] = Field(default_factory=list)
    openings: list[Opening] = Field(default_factory=list)
    stairs: list[Stair] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_level_invariants(self) -> "Level":
        walls_by_id = {w.id: w for w in self.walls}

        # 1. Validate openings fit on their host wall
        for op in self.openings:
            wall = walls_by_id.get(op.wall_id)
            if wall is not None:
                if op.offset_mm < 0:
                    raise ValueError(f"Opening {op.id} offset ({op.offset_mm} mm) cannot be negative.")
                # Allow 1.0mm tolerance for floating point calculations
                if op.offset_mm + op.width_mm > wall.length_mm + 1.0:
                    raise ValueError(
                        f"Opening {op.id} ({op.offset_mm + op.width_mm:.1f} mm) exceeds "
                        f"wall {op.wall_id} length ({wall.length_mm:.1f} mm)."
                    )

        # 2. Validate room polygons do not overlap each other in area
        n_rooms = len(self.rooms)
        if n_rooms > 1:
            room_polys = [(r.id, Polygon(r.polygon)) for r in self.rooms]
            for i in range(n_rooms):
                id1, p1 = room_polys[i]
                for j in range(i + 1, n_rooms):
                    id2, p2 = room_polys[j]
                    if p1.intersects(p2):
                        inter = p1.intersection(p2)
                        # An intersection area > 500 mm2 is an overlap (shared border has 0 area)
                        if inter.area > 500.0:
                            raise ValueError(
                                f"Rooms '{id1}' and '{id2}' overlap in area ({inter.area / 1e6:.2f} sqm)."
                            )

        return self


class PlanData(BaseModel):
    """Versioned canonical Plan model."""

    units: Literal["mm"] = "mm"
    levels: list[Level] = Field(default_factory=list)


class PlanSummary(BaseModel):
    """Metadata summary of a plan."""

    id: str
    project_id: str
    name: str
    current_version: int
    created_at: str
    updated_at: str
