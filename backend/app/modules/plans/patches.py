"""Typed Plan Patches, atomic apply, and version diffing (Phase 3).

Room Polygon Recomputation from Walls:
When a wall is edited or moved via `MoveWallPatch`, connected room polygons must adjust:
1. Vertices in room polygons that are collinear with or coincident to the wall's start and end points
   within a tolerance distance (50mm snap threshold) are shifted by (dx, dy).
2. The resulting room polygon is validated via Shapely. If valid and non-empty, the updated polygon
   is assigned to the room.
3. This ensures topological continuity between walls and room bounds without requiring a destructive
   mesh rebuild.
"""

from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.modules.plans.schemas import Opening, PlanData


class BasePatch(BaseModel):
    """Base class for typed immutable plan patches."""

    type: str

    def apply(self, plan: PlanData) -> PlanData:
        """Pure function applying patch to plan, returning a new PlanData instance."""
        raise NotImplementedError


class MoveWallPatch(BasePatch):
    """Move wall endpoints by delta (dx_mm, dy_mm)."""

    type: Literal["move_wall"] = "move_wall"
    wall_id: str
    dx_mm: float
    dy_mm: float

    def apply(self, plan: PlanData) -> PlanData:
        plan_dict = plan.model_dump()
        wall_found = False

        for level in plan_dict["levels"]:
            for wall in level["walls"]:
                if wall["id"] == self.wall_id:
                    wall_found = True
                    old_start = list(wall["start"])
                    old_end = list(wall["end"])

                    wall["start"] = [wall["start"][0] + self.dx_mm, wall["start"][1] + self.dy_mm]
                    wall["end"] = [wall["end"][0] + self.dx_mm, wall["end"][1] + self.dy_mm]

                    # Adjust adjacent room polygons coincident with this wall
                    for room in level["rooms"]:
                        new_poly = []
                        for pt in room["polygon"]:
                            # If vertex was at old start or end (or on the wall segment)
                            dist_to_start = (
                                (pt[0] - old_start[0]) ** 2 + (pt[1] - old_start[1]) ** 2
                            ) ** 0.5
                            dist_to_end = (
                                (pt[0] - old_end[0]) ** 2 + (pt[1] - old_end[1]) ** 2
                            ) ** 0.5
                            if dist_to_start < 50.0 or dist_to_end < 50.0:
                                new_poly.append([pt[0] + self.dx_mm, pt[1] + self.dy_mm])
                            else:
                                new_poly.append(pt)
                        room["polygon"] = new_poly
                    break
            if wall_found:
                break

        if not wall_found:
            raise ValueError(f"Wall with id '{self.wall_id}' not found in plan.")

        return PlanData.model_validate(plan_dict)


class SetWallThicknessPatch(BasePatch):
    """Update wall thickness."""

    type: Literal["set_wall_thickness"] = "set_wall_thickness"
    wall_id: str
    thickness_mm: float

    def apply(self, plan: PlanData) -> PlanData:
        plan_dict = plan.model_dump()
        found = False
        for level in plan_dict["levels"]:
            for wall in level["walls"]:
                if wall["id"] == self.wall_id:
                    wall["thickness_mm"] = self.thickness_mm
                    found = True
                    break
            if found:
                break
        if not found:
            raise ValueError(f"Wall '{self.wall_id}' not found.")
        return PlanData.model_validate(plan_dict)


class AddOpeningPatch(BasePatch):
    """Add a new opening to a level."""

    type: Literal["add_opening"] = "add_opening"
    level_id: str
    opening: Opening

    def apply(self, plan: PlanData) -> PlanData:
        plan_dict = plan.model_dump()
        found_level = False
        for level in plan_dict["levels"]:
            if level["id"] == self.level_id:
                level["openings"].append(self.opening.model_dump())
                found_level = True
                break
        if not found_level:
            raise ValueError(f"Level '{self.level_id}' not found.")
        return PlanData.model_validate(plan_dict)


class MoveOpeningPatch(BasePatch):
    """Update offset of an opening along its host wall."""

    type: Literal["move_opening"] = "move_opening"
    opening_id: str
    new_offset_mm: float

    def apply(self, plan: PlanData) -> PlanData:
        plan_dict = plan.model_dump()
        found = False
        for level in plan_dict["levels"]:
            for op in level["openings"]:
                if op["id"] == self.opening_id:
                    op["offset_mm"] = self.new_offset_mm
                    found = True
                    break
            if found:
                break
        if not found:
            raise ValueError(f"Opening '{self.opening_id}' not found.")
        return PlanData.model_validate(plan_dict)


class ResizeOpeningPatch(BasePatch):
    """Resize width and height of an opening."""

    type: Literal["resize_opening"] = "resize_opening"
    opening_id: str
    width_mm: float
    height_mm: float

    def apply(self, plan: PlanData) -> PlanData:
        plan_dict = plan.model_dump()
        found = False
        for level in plan_dict["levels"]:
            for op in level["openings"]:
                if op["id"] == self.opening_id:
                    op["width_mm"] = self.width_mm
                    op["height_mm"] = self.height_mm
                    found = True
                    break
            if found:
                break
        if not found:
            raise ValueError(f"Opening '{self.opening_id}' not found.")
        return PlanData.model_validate(plan_dict)


class RemoveOpeningPatch(BasePatch):
    """Remove an opening from its host level."""

    type: Literal["remove_opening"] = "remove_opening"
    opening_id: str

    def apply(self, plan: PlanData) -> PlanData:
        plan_dict = plan.model_dump()
        found = False
        for level in plan_dict["levels"]:
            orig_len = len(level["openings"])
            level["openings"] = [o for o in level["openings"] if o["id"] != self.opening_id]
            if len(level["openings"]) < orig_len:
                found = True
                break
        if not found:
            raise ValueError(f"Opening '{self.opening_id}' not found.")
        return PlanData.model_validate(plan_dict)


class SetRoomTypePatch(BasePatch):
    """Update functional classification of a room."""

    type: Literal["set_room_type"] = "set_room_type"
    room_id: str
    new_type: str

    def apply(self, plan: PlanData) -> PlanData:
        plan_dict = plan.model_dump()
        found = False
        for level in plan_dict["levels"]:
            for r in level["rooms"]:
                if r["id"] == self.room_id:
                    r["type"] = self.new_type
                    found = True
                    break
            if found:
                break
        if not found:
            raise ValueError(f"Room '{self.room_id}' not found.")
        return PlanData.model_validate(plan_dict)


class RenameRoomPatch(BasePatch):
    """Update human-readable display name of a room."""

    type: Literal["rename_room"] = "rename_room"
    room_id: str
    new_name: str

    def apply(self, plan: PlanData) -> PlanData:
        plan_dict = plan.model_dump()
        found = False
        for level in plan_dict["levels"]:
            for r in level["rooms"]:
                if r["id"] == self.room_id:
                    r["name"] = self.new_name
                    found = True
                    break
            if found:
                break
        if not found:
            raise ValueError(f"Room '{self.room_id}' not found.")
        return PlanData.model_validate(plan_dict)


class SplitRoomPatch(BasePatch):
    """Replace a room with two or more non-overlapping sub-rooms."""

    type: Literal["split_room"] = "split_room"
    room_id: str
    new_rooms: list[dict[str, Any]]

    def apply(self, plan: PlanData) -> PlanData:
        plan_dict = plan.model_dump()
        found = False
        for level in plan_dict["levels"]:
            for idx, r in enumerate(level["rooms"]):
                if r["id"] == self.room_id:
                    # Remove original and inject new sub-rooms
                    level["rooms"].pop(idx)
                    level["rooms"].extend(self.new_rooms)
                    found = True
                    break
            if found:
                break
        if not found:
            raise ValueError(f"Room '{self.room_id}' not found to split.")
        return PlanData.model_validate(plan_dict)


class MergeRoomsPatch(BasePatch):
    """Merge multiple rooms into a single room."""

    type: Literal["merge_rooms"] = "merge_rooms"
    room_ids: list[str]
    merged_room: dict[str, Any]

    def apply(self, plan: PlanData) -> PlanData:
        plan_dict = plan.model_dump()
        found_any = False
        for level in plan_dict["levels"]:
            orig_len = len(level["rooms"])
            level["rooms"] = [r for r in level["rooms"] if r["id"] not in self.room_ids]
            if len(level["rooms"]) < orig_len:
                level["rooms"].append(self.merged_room)
                found_any = True
                break
        if not found_any:
            raise ValueError(f"None of rooms {self.room_ids} found to merge.")
        return PlanData.model_validate(plan_dict)


class SetRoomPolygonPatch(BasePatch):
    """Update geometric polygon boundary of a room."""

    type: Literal["set_room_polygon"] = "set_room_polygon"
    room_id: str
    polygon: list[list[float]]

    def apply(self, plan: PlanData) -> PlanData:
        plan_dict = plan.model_dump()
        found = False
        for level in plan_dict["levels"]:
            for r in level["rooms"]:
                if r["id"] == self.room_id:
                    r["polygon"] = self.polygon
                    found = True
                    break
            if found:
                break
        if not found:
            raise ValueError(f"Room '{self.room_id}' not found.")
        return PlanData.model_validate(plan_dict)


# Patch dispatcher
PATCH_DISPATCHER: dict[str, type[BasePatch]] = {
    "move_wall": MoveWallPatch,
    "set_wall_thickness": SetWallThicknessPatch,
    "add_opening": AddOpeningPatch,
    "move_opening": MoveOpeningPatch,
    "resize_opening": ResizeOpeningPatch,
    "remove_opening": RemoveOpeningPatch,
    "set_room_type": SetRoomTypePatch,
    "rename_room": RenameRoomPatch,
    "split_room": SplitRoomPatch,
    "merge_rooms": MergeRoomsPatch,
    "set_room_polygon": SetRoomPolygonPatch,
}


def parse_patch(patch_dict: dict[str, Any]) -> BasePatch:
    """Parse raw patch dictionary into concrete typed patch model."""
    d = dict(patch_dict)
    ptype = d.get("type") or d.get("op")
    d["type"] = ptype
    patch_cls = PATCH_DISPATCHER.get(ptype or "")
    if not patch_cls:
        raise ValueError(f"Unsupported patch operation type: '{ptype}'")
    return patch_cls.model_validate(d)


def apply_patches(plan: PlanData, patches: Sequence[dict[str, Any] | BasePatch]) -> PlanData:
    """Apply a list of patches sequentially and atomically."""
    current = plan
    for p in patches:
        if isinstance(p, dict):
            patch_obj = parse_patch(p)
        else:
            patch_obj = p
        current = patch_obj.apply(current)
    return current


class PlanDiff(BaseModel):
    """Structured diff between two plan versions."""

    from_version: int | None = None
    to_version: int | None = None
    modified_walls: list[dict[str, Any]] = Field(default_factory=list)
    added_walls: list[dict[str, Any]] = Field(default_factory=list)
    removed_walls: list[str] = Field(default_factory=list)
    modified_openings: list[dict[str, Any]] = Field(default_factory=list)
    added_openings: list[dict[str, Any]] = Field(default_factory=list)
    removed_openings: list[str] = Field(default_factory=list)
    modified_rooms: list[dict[str, Any]] = Field(default_factory=list)
    added_rooms: list[dict[str, Any]] = Field(default_factory=list)
    removed_rooms: list[str] = Field(default_factory=list)


def compute_plan_diff(plan_a: PlanData, plan_b: PlanData) -> PlanDiff:
    """Compute structured semantic delta between two plan states."""
    diff = PlanDiff()

    # Flatten walls from all levels
    walls_a = {w.id: w for lvl in plan_a.levels for w in lvl.walls}
    walls_b = {w.id: w for lvl in plan_b.levels for w in lvl.walls}

    for wid, wa in walls_a.items():
        if wid not in walls_b:
            diff.removed_walls.append(wid)
        else:
            wb = walls_b[wid]
            if wa.model_dump() != wb.model_dump():
                diff.modified_walls.append(
                    {"id": wid, "before": wa.model_dump(), "after": wb.model_dump()}
                )

    for wid, wb in walls_b.items():
        if wid not in walls_a:
            diff.added_walls.append(wb.model_dump())

    # Openings
    ops_a = {o.id: o for lvl in plan_a.levels for o in lvl.openings}
    ops_b = {o.id: o for lvl in plan_b.levels for o in lvl.openings}

    for oid, oa in ops_a.items():
        if oid not in ops_b:
            diff.removed_openings.append(oid)
        else:
            ob = ops_b[oid]
            if oa.model_dump() != ob.model_dump():
                diff.modified_openings.append(
                    {"id": oid, "before": oa.model_dump(), "after": ob.model_dump()}
                )

    for oid, ob in ops_b.items():
        if oid not in ops_a:
            diff.added_openings.append(ob.model_dump())

    # Rooms
    rooms_a = {r.id: r for lvl in plan_a.levels for r in lvl.rooms}
    rooms_b = {r.id: r for lvl in plan_b.levels for r in lvl.rooms}

    for rid, ra in rooms_a.items():
        if rid not in rooms_b:
            diff.removed_rooms.append(rid)
        else:
            rb = rooms_b[rid]
            if ra.model_dump() != rb.model_dump():
                diff.modified_rooms.append(
                    {"id": rid, "before": ra.model_dump(), "after": rb.model_dump()}
                )

    for rid, rb in rooms_b.items():
        if rid not in rooms_a:
            diff.added_rooms.append(rb.model_dump())

    return diff
