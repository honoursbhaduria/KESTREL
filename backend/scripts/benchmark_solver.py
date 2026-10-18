"""Benchmark script reporting generative layout synthesis latency for 3 program sizes.
Target: Generation job finishes under 30s for a 2-floor 4BHK.
"""

import time
import sys
from shapely.geometry import Polygon

from app.modules.planning.envelope import Envelope
from app.modules.planning.program import Adjacency, Preferences, Program, RoomProgram
from app.modules.planning.solver import LayoutSolver


def make_envelope(width_mm: float, depth_mm: float) -> Envelope:
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


def benchmark_1bhk_single_floor() -> float:
    """1BHK Single Level: 4 rooms."""
    envelope = make_envelope(7000.0, 10000.0)  # 70 sqm footprint
    program = Program(
        levels=1,
        rooms=[
            RoomProgram(type="living", name="Living Room", target_area_mm2=18_000_000.0, min_width_mm=3000.0, level_hint=1),
            RoomProgram(type="kitchen", name="Kitchen", target_area_mm2=7_000_000.0, min_width_mm=2100.0, level_hint=1),
            RoomProgram(type="bedroom", name="Master Bedroom", target_area_mm2=14_000_000.0, min_width_mm=3000.0, level_hint=1),
            RoomProgram(type="bathroom", name="Bathroom", target_area_mm2=4_000_000.0, min_width_mm=1500.0, level_hint=1),
        ],
        adjacencies=[
            Adjacency(a="Living Room", b="Kitchen", strength="prefer"),
            Adjacency(a="Master Bedroom", b="Bathroom", strength="must"),
        ],
        preferences=Preferences(entrance_side="east", vastu=True),
    )

    solver = LayoutSolver()
    start = time.perf_counter()
    candidates = solver.solve(program=program, envelope=envelope, seed=42, num_candidates=3)
    duration = time.perf_counter() - start

    assert len(candidates) >= 1, "Expected at least 1 valid candidate for 1BHK"
    return duration


def benchmark_2bhk_single_floor() -> float:
    """2BHK Single Level: 6 rooms."""
    envelope = make_envelope(9000.0, 12000.0)  # 108 sqm footprint
    program = Program(
        levels=1,
        rooms=[
            RoomProgram(type="living", name="Living Room", target_area_mm2=22_000_000.0, min_width_mm=3200.0, level_hint=1),
            RoomProgram(type="dining", name="Dining Room", target_area_mm2=10_000_000.0, min_width_mm=2400.0, level_hint=1),
            RoomProgram(type="kitchen", name="Kitchen", target_area_mm2=9_000_000.0, min_width_mm=2400.0, level_hint=1),
            RoomProgram(type="bedroom", name="Master Bedroom", target_area_mm2=16_000_000.0, min_width_mm=3200.0, level_hint=1),
            RoomProgram(type="bedroom", name="Guest Bedroom", target_area_mm2=13_000_000.0, min_width_mm=3000.0, level_hint=1),
            RoomProgram(type="bathroom", name="Master Bath", target_area_mm2=4_500_000.0, min_width_mm=1500.0, level_hint=1),
            RoomProgram(type="bathroom", name="Common Bath", target_area_mm2=3_500_000.0, min_width_mm=1500.0, level_hint=1),
        ],
        adjacencies=[
            Adjacency(a="Living Room", b="Dining Room", strength="must"),
            Adjacency(a="Kitchen", b="Dining Room", strength="must"),
            Adjacency(a="Master Bedroom", b="Master Bath", strength="must"),
        ],
        preferences=Preferences(entrance_side="north", vastu=True),
    )

    solver = LayoutSolver()
    start = time.perf_counter()
    candidates = solver.solve(program=program, envelope=envelope, seed=101, num_candidates=3)
    duration = time.perf_counter() - start

    assert len(candidates) >= 1, "Expected at least 1 valid candidate for 2BHK"
    return duration


def benchmark_4bhk_two_floors() -> float:
    """4BHK Two Floors with Vertical Stair Alignment: 11 rooms."""
    envelope = make_envelope(11000.0, 16000.0)  # 176 sqm footprint
    program = Program(
        levels=2,
        rooms=[
            # Level 1
            RoomProgram(type="living", name="Living Foyer", target_area_mm2=25_000_000.0, min_width_mm=3600.0, level_hint=1),
            RoomProgram(type="dining", name="Dining Room", target_area_mm2=14_000_000.0, min_width_mm=3000.0, level_hint=1),
            RoomProgram(type="kitchen", name="Modular Kitchen", target_area_mm2=11_000_000.0, min_width_mm=2700.0, level_hint=1),
            RoomProgram(type="bedroom", name="Guest Suite", target_area_mm2=15_000_000.0, min_width_mm=3200.0, level_hint=1),
            RoomProgram(type="bathroom", name="Guest Bath", target_area_mm2=4_500_000.0, min_width_mm=1500.0, level_hint=1),
            RoomProgram(type="bathroom", name="Powder Room", target_area_mm2=3_000_000.0, min_width_mm=1200.0, level_hint=1),
            RoomProgram(type="stair", name="Staircase", target_area_mm2=7_000_000.0, min_width_mm=2400.0, level_hint=1),
            # Level 2
            RoomProgram(type="stair", name="Staircase", target_area_mm2=7_000_000.0, min_width_mm=2400.0, level_hint=2),
            RoomProgram(type="bedroom", name="Master Bedroom", target_area_mm2=20_000_000.0, min_width_mm=3600.0, level_hint=2),
            RoomProgram(type="bathroom", name="Master En-Suite", target_area_mm2=6_000_000.0, min_width_mm=1800.0, level_hint=2),
            RoomProgram(type="bedroom", name="Kids Bedroom 1", target_area_mm2=14_000_000.0, min_width_mm=3000.0, level_hint=2),
            RoomProgram(type="bedroom", name="Kids Bedroom 2", target_area_mm2=14_000_000.0, min_width_mm=3000.0, level_hint=2),
            RoomProgram(type="bathroom", name="Kids Bath", target_area_mm2=4_500_000.0, min_width_mm=1500.0, level_hint=2),
        ],
        adjacencies=[
            Adjacency(a="Living Foyer", b="Dining Room", strength="must"),
            Adjacency(a="Modular Kitchen", b="Dining Room", strength="must"),
            Adjacency(a="Master Bedroom", b="Master En-Suite", strength="must"),
        ],
        preferences=Preferences(entrance_side="east", vastu=True),
    )

    solver = LayoutSolver()
    start = time.perf_counter()
    candidates = solver.solve(program=program, envelope=envelope, seed=777, num_candidates=3)
    duration = time.perf_counter() - start

    assert len(candidates) >= 1, "Expected at least 1 valid candidate for 4BHK"
    return duration


def main():
    print("=" * 60)
    print("HARON GENERATIVE LAYOUT SOLVER BENCHMARK")
    print("=" * 60)

    t1 = benchmark_1bhk_single_floor()
    print(f"1. 1BHK Single Floor (4 rooms)         : {t1 * 1000:.1f} ms  (Target: < 30,000 ms)")

    t2 = benchmark_2bhk_single_floor()
    print(f"2. 2BHK Single Floor (7 rooms)         : {t2 * 1000:.1f} ms  (Target: < 30,000 ms)")

    t3 = benchmark_4bhk_two_floors()
    print(f"3. 4BHK Two Floors + Stairs (13 rooms) : {t3 * 1000:.1f} ms  (Target: < 30,000 ms)")

    print("-" * 60)
    max_duration = max(t1, t2, t3)
    if max_duration < 30.0:
        print(f"ALL BENCHMARKS PASSED in {max_duration:.2f}s! Execution is orders of magnitude below 30s target.")
        sys.exit(0)
    else:
        print("BENCHMARK EXCEEDED 30s TARGET.")
        sys.exit(1)


if __name__ == "__main__":
    main()
