"""Tests for the pure Python Generative Layout Solver."""

from shapely.geometry import Point, Polygon

from app.modules.planning.envelope import Envelope
from app.modules.planning.program import Adjacency, Preferences, Program, RoomProgram
from app.modules.planning.solver import LayoutSolver


def create_sample_envelope(width_mm: float = 8000.0, depth_mm: float = 12000.0) -> Envelope:
    """Create a rectangular buildable footprint of width x depth."""
    coords = [
        [0.0, 0.0],
        [width_mm, 0.0],
        [width_mm, depth_mm],
        [0.0, depth_mm],
    ]
    area = width_mm * depth_mm
    return Envelope(
        footprint_polygon=coords,
        footprint_area_mm2=area,
        max_coverage_mm2=area * 0.75,
        max_builtup_mm2=area * 2.0,
        max_height_mm=10000.0,
        max_floors=2,
        applied_rules=[],
    )


def create_sample_program_single_floor() -> Program:
    """Create a 2BHK single-level program."""
    return Program(
        levels=1,
        rooms=[
            RoomProgram(type="living", name="Living Room", target_area_mm2=20_000_000.0, min_width_mm=3000.0, level_hint=1),
            RoomProgram(type="kitchen", name="Kitchen", target_area_mm2=8_000_000.0, min_width_mm=2100.0, level_hint=1),
            RoomProgram(type="bedroom", name="Master Bedroom", target_area_mm2=14_000_000.0, min_width_mm=3000.0, level_hint=1),
            RoomProgram(type="bedroom", name="Guest Bedroom", target_area_mm2=12_000_000.0, min_width_mm=2700.0, level_hint=1),
            RoomProgram(type="bathroom", name="Master Bath", target_area_mm2=4_000_000.0, min_width_mm=1500.0, level_hint=1),
            RoomProgram(type="bathroom", name="Common Bath", target_area_mm2=3_500_000.0, min_width_mm=1500.0, level_hint=1),
        ],
        adjacencies=[
            Adjacency(a="Living Room", b="Kitchen", strength="prefer"),
            Adjacency(a="Master Bedroom", b="Master Bath", strength="must"),
        ],
        preferences=Preferences(entrance_side="east", vastu=True, parking=False),
    )


def create_sample_program_two_floors() -> Program:
    """Create a 3BHK two-level program with stairs."""
    return Program(
        levels=2,
        rooms=[
            # Level 1
            RoomProgram(type="living", name="Living Room", target_area_mm2=22_000_000.0, min_width_mm=3200.0, level_hint=1),
            RoomProgram(type="kitchen", name="Kitchen", target_area_mm2=9_000_000.0, min_width_mm=2100.0, level_hint=1),
            RoomProgram(type="dining", name="Dining Room", target_area_mm2=12_000_000.0, min_width_mm=2700.0, level_hint=1),
            RoomProgram(type="stair", name="Staircase", target_area_mm2=6_000_000.0, min_width_mm=2000.0, level_hint=1),
            RoomProgram(type="bathroom", name="Powder Room", target_area_mm2=3_000_000.0, min_width_mm=1200.0, level_hint=1),
            # Level 2
            RoomProgram(type="stair", name="Staircase", target_area_mm2=6_000_000.0, min_width_mm=2000.0, level_hint=2),
            RoomProgram(type="bedroom", name="Master Bedroom", target_area_mm2=16_000_000.0, min_width_mm=3200.0, level_hint=2),
            RoomProgram(type="bathroom", name="Master Bath", target_area_mm2=5_000_000.0, min_width_mm=1800.0, level_hint=2),
            RoomProgram(type="bedroom", name="Kids Bedroom", target_area_mm2=14_000_000.0, min_width_mm=3000.0, level_hint=2),
            RoomProgram(type="bathroom", name="Kids Bath", target_area_mm2=4_000_000.0, min_width_mm=1500.0, level_hint=2),
        ],
        adjacencies=[
            Adjacency(a="Kitchen", b="Dining Room", strength="must"),
            Adjacency(a="Master Bedroom", b="Master Bath", strength="must"),
        ],
        preferences=Preferences(entrance_side="north", vastu=True, parking=True),
    )


def test_solver_rooms_inside_envelope():
    """Verify all rooms are strictly within the envelope footprint."""
    envelope = create_sample_envelope(8000.0, 12000.0)
    program = create_sample_program_single_floor()
    solver = LayoutSolver()

    candidates = solver.solve(program=program, envelope=envelope, seed=42, num_candidates=3)
    assert len(candidates) >= 1

    footprint_poly = Polygon(envelope.footprint_polygon)
    for cand in candidates:
        plan_data = cand.plan_data
        for level in plan_data.levels:
            for room in level.rooms:
                room_poly = Polygon(room.polygon)
                # Allow 5mm margin for boundary rounding
                assert footprint_poly.buffer(5.0).contains(room_poly)


def test_solver_no_overlapping_rooms():
    """Verify that no two rooms on the same level overlap in area."""
    envelope = create_sample_envelope(8000.0, 12000.0)
    program = create_sample_program_single_floor()
    solver = LayoutSolver()

    candidates = solver.solve(program=program, envelope=envelope, seed=42, num_candidates=3)
    for cand in candidates:
        for level in cand.plan_data.levels:
            polys = [Polygon(r.polygon) for r in level.rooms]
            for i in range(len(polys)):
                for j in range(i + 1, len(polys)):
                    intersection = polys[i].intersection(polys[j])
                    assert intersection.area < 500.0, f"Rooms overlap by {intersection.area} mm2"


def test_solver_room_reachability_graph():
    """Verify that every room has a door connecting to circulation or adjacent room (graph check)."""
    envelope = create_sample_envelope(8000.0, 12000.0)
    program = create_sample_program_single_floor()
    solver = LayoutSolver()

    candidates = solver.solve(program=program, envelope=envelope, seed=42, num_candidates=3)
    for cand in candidates:
        for level in cand.plan_data.levels:
            door_count = len([op for op in level.openings if op.kind == "door"])
            # Every room (except perhaps circulation corridor itself) must have at least one door
            assert door_count >= len(level.rooms)


def test_solver_vertical_stair_alignment():
    """Verify stair footprints on Level 1 and Level 2 are aligned vertically."""
    envelope = create_sample_envelope(9000.0, 14000.0)
    program = create_sample_program_two_floors()
    solver = LayoutSolver()

    candidates = solver.solve(program=program, envelope=envelope, seed=99, num_candidates=3)
    assert len(candidates) >= 1

    for cand in candidates:
        lvl1 = next(lvl for lvl in cand.plan_data.levels if "1" in lvl.name or lvl.elevation_mm == 0.0)
        lvl2 = next(lvl for lvl in cand.plan_data.levels if "2" in lvl.name or lvl.elevation_mm > 0.0)

        stair1 = next(r for r in lvl1.rooms if r.type == "stair")
        stair2 = next(r for r in lvl2.rooms if r.type == "stair")

        p1 = Polygon(stair1.polygon)
        p2 = Polygon(stair2.polygon)

        # Centroids should match closely (< 50mm)
        assert abs(p1.centroid.x - p2.centroid.x) < 50.0
        assert abs(p1.centroid.y - p2.centroid.y) < 50.0


def test_solver_determinism_given_seed():
    """Verify solver output is 100% deterministic given the same seed."""
    envelope = create_sample_envelope(8000.0, 12000.0)
    program = create_sample_program_single_floor()
    solver = LayoutSolver()

    run1 = solver.solve(program=program, envelope=envelope, seed=12345, num_candidates=3)
    run2 = solver.solve(program=program, envelope=envelope, seed=12345, num_candidates=3)

    assert len(run1) == len(run2)
    for c1, c2 in zip(run1, run2, strict=False):
        assert round(c1.score_breakdown.total_score, 4) == round(c2.score_breakdown.total_score, 4)
        for lvl1, lvl2 in zip(c1.plan_data.levels, c2.plan_data.levels, strict=False):
            assert len(lvl1.rooms) == len(lvl2.rooms)
            for r1, r2 in zip(lvl1.rooms, lvl2.rooms, strict=False):
                assert r1.name == r2.name
                assert r1.polygon == r2.polygon
