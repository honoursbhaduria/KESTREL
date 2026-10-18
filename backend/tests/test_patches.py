"""Tests for typed Plan Patches, undo/redo, and version diffing (Phase 3)."""

import json
from pathlib import Path

import pytest

from app.modules.plans.patches import (
    AddOpeningPatch,
    MergeRoomsPatch,
    MoveOpeningPatch,
    MoveWallPatch,
    RemoveOpeningPatch,
    RenameRoomPatch,
    ResizeOpeningPatch,
    SetRoomTypePatch,
    SetWallThicknessPatch,
    SplitRoomPatch,
    apply_patches,
    compute_plan_diff,
)
from app.modules.plans.schemas import Opening, PlanData

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "plans"


@pytest.fixture
def plan_fixture() -> PlanData:
    raw = json.loads((FIXTURES_DIR / "plan_2bhk_single_floor.json").read_text())
    return PlanData.model_validate(raw)


def test_move_wall_patch_updates_coordinates(plan_fixture: PlanData):
    """Moving a wall updates its endpoints and adjusts connected room geometry."""
    original_wall = next(w for w in plan_fixture.levels[0].walls if w.id == "wall-int-v-mid")
    assert original_wall.start == [5000, 5000]

    patch = MoveWallPatch(wall_id="wall-int-v-mid", dx_mm=500, dy_mm=0)
    updated_plan = patch.apply(plan_fixture)

    updated_wall = next(w for w in updated_plan.levels[0].walls if w.id == "wall-int-v-mid")
    assert updated_wall.start == [5500, 5000]
    assert updated_wall.end == [5500, 10000]


def test_set_wall_thickness_patch(plan_fixture: PlanData):
    """Setting wall thickness updates the attribute."""
    patch = SetWallThicknessPatch(wall_id="wall-int-h-mid", thickness_mm=150)
    updated = patch.apply(plan_fixture)
    w = next(w for w in updated.levels[0].walls if w.id == "wall-int-h-mid")
    assert w.thickness_mm == 150


def test_add_and_remove_opening_patches(plan_fixture: PlanData):
    """Adding an opening and removing it updates the level opening list."""
    new_op = Opening(
        id="open-test-window",
        wall_id="wall-ext-west",
        kind="window",
        offset_mm=2000,
        width_mm=1200,
        height_mm=1200,
        sill_mm=900,
    )
    add_patch = AddOpeningPatch(level_id="lvl-ground", opening=new_op)
    plan_with_op = add_patch.apply(plan_fixture)
    assert any(o.id == "open-test-window" for o in plan_with_op.levels[0].openings)

    rm_patch = RemoveOpeningPatch(opening_id="open-test-window")
    plan_after_rm = rm_patch.apply(plan_with_op)
    assert not any(o.id == "open-test-window" for o in plan_after_rm.levels[0].openings)


def test_move_and_resize_opening_patches(plan_fixture: PlanData):
    """Moving and resizing an opening updates offset and dimensions."""
    move_patch = MoveOpeningPatch(opening_id="open-main-door", new_offset_mm=1500)
    plan_moved = move_patch.apply(plan_fixture)
    op = next(o for o in plan_moved.levels[0].openings if o.id == "open-main-door")
    assert op.offset_mm == 1500

    resize_patch = ResizeOpeningPatch(opening_id="open-main-door", width_mm=1200, height_mm=2200)
    plan_resized = resize_patch.apply(plan_moved)
    op2 = next(o for o in plan_resized.levels[0].openings if o.id == "open-main-door")
    assert op2.width_mm == 1200
    assert op2.height_mm == 2200


def test_room_type_and_rename_patches(plan_fixture: PlanData):
    """Updating room type and renaming updates the room record."""
    patch_type = SetRoomTypePatch(room_id="room-bed2", new_type="study")
    patch_name = RenameRoomPatch(room_id="room-bed2", new_name="Executive Study")

    updated = patch_name.apply(patch_type.apply(plan_fixture))
    room = next(r for r in updated.levels[0].rooms if r.id == "room-bed2")
    assert room.type == "study"
    assert room.name == "Executive Study"


def test_split_and_merge_rooms_patches(plan_fixture: PlanData):
    """Splitting a room and merging rooms preserves topology and updates IDs."""
    # Split bedroom 1 into bed1-a and bed1-b
    split_patch = SplitRoomPatch(
        room_id="room-bed1",
        new_rooms=[
            {
                "id": "room-bed1-a",
                "type": "bedroom",
                "name": "Master Bed Sleeping Area",
                "polygon": [[0, 5000], [3000, 5000], [3000, 10000], [0, 10000]],
            },
            {
                "id": "room-bed1-b",
                "type": "utility",
                "name": "Walk-in Wardrobe",
                "polygon": [[3000, 5000], [5000, 5000], [5000, 10000], [3000, 10000]],
            },
        ],
    )
    plan_split = split_patch.apply(plan_fixture)
    assert not any(r.id == "room-bed1" for r in plan_split.levels[0].rooms)
    assert any(r.id == "room-bed1-a" for r in plan_split.levels[0].rooms)
    assert any(r.id == "room-bed1-b" for r in plan_split.levels[0].rooms)

    # Merge them back
    merge_patch = MergeRoomsPatch(
        room_ids=["room-bed1-a", "room-bed1-b"],
        merged_room={
            "id": "room-bed1",
            "type": "bedroom",
            "name": "Recombined Master Bedroom",
            "polygon": [[0, 5000], [5000, 5000], [5000, 10000], [0, 10000]],
        },
    )
    plan_merged = merge_patch.apply(plan_split)
    assert any(r.id == "room-bed1" for r in plan_merged.levels[0].rooms)
    assert not any(r.id == "room-bed1-a" for r in plan_merged.levels[0].rooms)


def test_invalid_patch_rejected(plan_fixture: PlanData):
    """Patch referring to non-existent wall or invalid offset raises ValueError."""
    bad_wall_patch = MoveWallPatch(wall_id="wall-does-not-exist", dx_mm=100, dy_mm=0)
    with pytest.raises(ValueError, match="not found"):
        bad_wall_patch.apply(plan_fixture)

    # Move opening beyond wall length
    bad_op_patch = MoveOpeningPatch(opening_id="open-main-door", new_offset_mm=100000)
    with pytest.raises(ValueError, match="exceeds wall"):
        bad_op_patch.apply(plan_fixture)


def test_compute_plan_diff(plan_fixture: PlanData):
    """Diffing original plan and modified plan returns structured delta."""
    patch = SetWallThicknessPatch(wall_id="wall-ext-north", thickness_mm=300)
    modified = patch.apply(plan_fixture)

    diff = compute_plan_diff(plan_fixture, modified)
    assert len(diff.modified_walls) == 1
    assert diff.modified_walls[0]["id"] == "wall-ext-north"
    assert diff.modified_walls[0]["before"]["thickness_mm"] == 200
    assert diff.modified_walls[0]["after"]["thickness_mm"] == 300
