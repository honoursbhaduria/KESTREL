"""Tests for core Plan Pydantic schema and spatial invariants (Phase 3)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.plans.schemas import Level, Opening, PlanData, Room, Stair, Wall

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "plans"


def test_load_2bhk_fixture_passes_schema():
    """Verify that the 2BHK clean fixture parses and satisfies all spatial invariants."""
    raw = json.loads((FIXTURES_DIR / "plan_2bhk_single_floor.json").read_text())
    plan = PlanData.model_validate(raw)
    assert plan.units == "mm"
    assert len(plan.levels) == 1
    assert len(plan.levels[0].rooms) == 5
    assert len(plan.levels[0].walls) == 10
    assert len(plan.levels[0].openings) == 9


def test_load_3bhk_two_floors_passes_schema():
    """Verify duplex 3BHK fixture with stairs passes schema."""
    raw = json.loads((FIXTURES_DIR / "plan_3bhk_two_floors.json").read_text())
    plan = PlanData.model_validate(raw)
    assert len(plan.levels) == 2
    assert len(plan.levels[0].stairs) == 1
    assert plan.levels[0].stairs[0].riser_mm == 160


def test_schema_rejects_overlapping_rooms():
    """Two rooms overlapping in area within the same level must be rejected."""
    raw = {
        "units": "mm",
        "levels": [
            {
                "id": "lvl-0",
                "name": "Ground",
                "elevation_mm": 0,
                "floor_to_floor_mm": 3000,
                "rooms": [
                    {
                        "id": "r1",
                        "type": "living",
                        "name": "Room 1",
                        "polygon": [[0, 0], [4000, 0], [4000, 4000], [0, 4000]],
                    },
                    {
                        "id": "r2",
                        "type": "bedroom",
                        "name": "Room 2 Overlapping",
                        "polygon": [[2000, 2000], [6000, 2000], [6000, 6000], [2000, 6000]],
                    },
                ],
                "walls": [],
                "openings": [],
                "stairs": [],
            }
        ],
    }
    with pytest.raises(ValidationError) as exc:
        PlanData.model_validate(raw)
    assert "overlap" in str(exc.value).lower()


def test_schema_rejects_opening_exceeding_wall_length():
    """An opening with offset_mm + width_mm > wall_length must be rejected."""
    raw = {
        "units": "mm",
        "levels": [
            {
                "id": "lvl-0",
                "name": "Ground",
                "elevation_mm": 0,
                "floor_to_floor_mm": 3000,
                "rooms": [],
                "walls": [
                    {
                        "id": "w1",
                        "start": [0, 0],
                        "end": [2000, 0],
                        "thickness_mm": 200,
                        "height_mm": 3000,
                        "is_external": True,
                    }
                ],
                "openings": [
                    {
                        "id": "op1",
                        "wall_id": "w1",
                        "kind": "door",
                        "offset_mm": 1500,
                        "width_mm": 1000,  # 1500 + 1000 = 2500 > wall length 2000
                        "height_mm": 2100,
                        "sill_mm": 0,
                    }
                ],
                "stairs": [],
            }
        ],
    }
    with pytest.raises(ValidationError) as exc:
        PlanData.model_validate(raw)
    assert "wall" in str(exc.value).lower()


def test_schema_rejects_self_intersecting_room():
    """A room polygon that self-intersects must fail validation."""
    raw = {
        "units": "mm",
        "levels": [
            {
                "id": "lvl-0",
                "name": "Ground",
                "elevation_mm": 0,
                "floor_to_floor_mm": 3000,
                "rooms": [
                    {
                        "id": "r1",
                        "type": "living",
                        "name": "Hourglass Bowtie",
                        "polygon": [[0, 0], [4000, 4000], [4000, 0], [0, 4000]],
                    }
                ],
                "walls": [],
                "openings": [],
                "stairs": [],
            }
        ],
    }
    with pytest.raises(ValidationError) as exc:
        PlanData.model_validate(raw)
    assert "polygon" in str(exc.value).lower() or "invalid" in str(exc.value).lower()
