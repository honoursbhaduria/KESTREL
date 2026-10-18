"""Property test with hypothesis for move_wall patch operator (Phase 3)."""

import json
from pathlib import Path
from hypothesis import given, settings
import hypothesis.strategies as st
from shapely.geometry import Polygon

from app.modules.plans.patches import MoveWallPatch
from app.modules.plans.schemas import PlanData

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "plans"


@settings(max_examples=30, deadline=None)
@given(
    dx_mm=st.integers(min_value=-400, max_value=400),
)
def test_hypothesis_move_wall_preserves_validity(dx_mm: int):
    """Moving a vertical interior wall horizontally resizes bedrooms while keeping plan valid."""
    raw = json.loads((FIXTURES_DIR / "plan_2bhk_single_floor.json").read_text())
    plan = PlanData.model_validate(raw)

    patch = MoveWallPatch(wall_id="wall-int-v-mid", dx_mm=dx_mm, dy_mm=0)
    updated_plan = patch.apply(plan)

    # Invariants:
    # 1. Wall endpoints moved by dx, dy
    orig_wall = next(w for w in plan.levels[0].walls if w.id == "wall-int-v-mid")
    new_wall = next(w for w in updated_plan.levels[0].walls if w.id == "wall-int-v-mid")
    assert new_wall.start == [orig_wall.start[0] + dx_mm, orig_wall.start[1]]
    assert new_wall.end == [orig_wall.end[0] + dx_mm, orig_wall.end[1]]

    # 2. Every room polygon in the level must remain topologically valid and non-empty
    for room in updated_plan.levels[0].rooms:
        poly = Polygon(room.polygon)
        assert poly.is_valid
        assert poly.area > 0
