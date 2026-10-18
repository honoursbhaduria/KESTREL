"""Tests for pure rule engine checkers (Phase 3)."""

import json
from pathlib import Path
import pytest

from app.modules.planning.envelope import Envelope
from app.modules.plans.schemas import PlanData
from app.modules.rules.checkers import (
    check_corridor_clear_width,
    check_door_clear_width,
    check_far,
    check_ground_coverage,
    check_inside_envelope,
    check_min_ceiling_height,
    check_min_room_area,
    check_min_room_width,
    check_stair_riser_tread,
    check_window_to_floor_ratio,
)
from app.modules.rules.schemas import RuleDefinition

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "plans"


@pytest.fixture
def plan_2bhk() -> PlanData:
    raw = json.loads((FIXTURES_DIR / "plan_2bhk_single_floor.json").read_text())
    return PlanData.model_validate(raw)


@pytest.fixture
def plan_violations() -> PlanData:
    raw = json.loads((FIXTURES_DIR / "plan_violations.json").read_text())
    return PlanData.model_validate(raw)


@pytest.fixture
def sample_envelope() -> Envelope:
    return Envelope(
        footprint_polygon=[[0, 0], [12000, 0], [12000, 12000], [0, 12000]],
        footprint_area_mm2=144_000_000,
        max_coverage_mm2=150_000_000,
        max_builtup_mm2=300_000_000,
        max_height_mm=15000,
        max_floors=4,
        applied_rules=[],
    )


def test_min_room_area_checker(plan_2bhk: PlanData, plan_violations: PlanData):
    rule = RuleDefinition(
        id="nbc-min-habitable-room",
        title="Minimum Habitable Room Area",
        clause="NBC 2016 Part 3 Clause 4.3",
        category="room_size",
        applies_to="room",
        check="min_room_area",
        params={"min_area_sqm": 9.5},
        severity="fail",
        verified=True,
    )
    # 2BHK has bedrooms >= 25 sqm -> pass
    issues_pass = check_min_room_area(plan_2bhk, None, rule)
    assert not any(i.status == "fail" for i in issues_pass)

    # Violations fixture has room-bed-small (5 sqm < 9.5) -> fail
    issues_fail = check_min_room_area(plan_violations, None, rule)
    fails = [i for i in issues_fail if i.status == "fail"]
    assert len(fails) >= 1
    assert any("room-bed-small" in i.element_ids for i in fails)


def test_min_room_width_checker(plan_2bhk: PlanData, plan_violations: PlanData):
    rule = RuleDefinition(
        id="nbc-min-kitchen-width",
        title="Minimum Kitchen Width",
        clause="NBC 2016 Part 3 Clause 4.4",
        category="width",
        applies_to="room",
        check="min_room_width",
        params={"room_type": "kitchen", "min_width_mm": 1800},
        severity="fail",
        verified=True,
    )
    issues_pass = check_min_room_width(plan_2bhk, None, rule)
    assert not any(i.status == "fail" for i in issues_pass)

    # Violations fixture kitchen has width 1400 mm < 1800 mm
    issues_fail = check_min_room_width(plan_violations, None, rule)
    fails = [i for i in issues_fail if i.status == "fail"]
    assert len(fails) >= 1
    assert "room-kitchen-narrow" in fails[0].element_ids


def test_min_ceiling_height_checker(plan_2bhk: PlanData, plan_violations: PlanData):
    rule = RuleDefinition(
        id="nbc-min-ceiling-height",
        title="Minimum Ceiling Height",
        clause="NBC 2016 Part 3 Clause 4.2",
        category="height",
        applies_to="level",
        check="min_ceiling_height",
        params={"min_height_mm": 2750},
        severity="fail",
        verified=True,
    )
    # 2BHK floor_to_floor is 3000 mm >= 2750 mm
    issues_pass = check_min_ceiling_height(plan_2bhk, None, rule)
    assert not any(i.status == "fail" for i in issues_pass)

    # Violations fixture has 2400 mm < 2750 mm
    issues_fail = check_min_ceiling_height(plan_violations, None, rule)
    fails = [i for i in issues_fail if i.status == "fail"]
    assert len(fails) >= 1
    assert "lvl-ground" in fails[0].element_ids


def test_door_clear_width_checker(plan_2bhk: PlanData, plan_violations: PlanData):
    rule = RuleDefinition(
        id="nbc-door-width",
        title="Minimum Door Width",
        clause="NBC 2016 Part 3 Clause 4.8",
        category="width",
        applies_to="opening",
        check="door_clear_width",
        params={"min_door_width_mm": 750},
        severity="fail",
        verified=True,
    )
    issues_pass = check_door_clear_width(plan_2bhk, None, rule)
    assert not any(i.status == "fail" for i in issues_pass)

    # Violations fixture has door with 650 mm < 750 mm
    issues_fail = check_door_clear_width(plan_violations, None, rule)
    fails = [i for i in issues_fail if i.status == "fail"]
    assert len(fails) >= 1
    assert "open-door-narrow" in fails[0].element_ids


def test_stair_riser_tread_checker(plan_violations: PlanData):
    raw_3bhk = json.loads((FIXTURES_DIR / "plan_3bhk_two_floors.json").read_text())
    plan_3bhk = PlanData.model_validate(raw_3bhk)

    rule = RuleDefinition(
        id="nbc-stair-proportions",
        title="Stair Riser & Tread Limits",
        clause="NBC 2016 Part 3 Clause 4.10",
        category="stair",
        applies_to="stair",
        check="stair_riser_tread",
        params={"max_riser_mm": 190, "min_tread_mm": 250},
        severity="fail",
        verified=True,
    )
    # 3BHK has riser 160 mm <= 190 and tread 280 mm >= 250
    issues_pass = check_stair_riser_tread(plan_3bhk, None, rule)
    assert not any(i.status == "fail" for i in issues_pass)

    # Violations fixture has riser 220 > 190, tread 210 < 250
    issues_fail = check_stair_riser_tread(plan_violations, None, rule)
    fails = [i for i in issues_fail if i.status == "fail"]
    assert len(fails) >= 1
    assert "stair-steep" in fails[0].element_ids


def test_window_to_floor_ratio_checker(plan_2bhk: PlanData, plan_violations: PlanData):
    rule = RuleDefinition(
        id="nbc-ventilation-ratio",
        title="Habitable Room Ventilation Window Area",
        clause="NBC 2016 Part 3 Clause 4.9",
        category="ventilation",
        applies_to="room",
        check="window_to_floor_ratio",
        params={"min_ratio": 0.125},  # 1/8 of floor area
        severity="fail",
        verified=True,
    )
    issues_pass = check_window_to_floor_ratio(plan_2bhk, None, rule)
    assert not any(i.status == "fail" for i in issues_pass)

    issues_fail = check_window_to_floor_ratio(plan_violations, None, rule)
    fails = [i for i in issues_fail if i.status == "fail"]
    assert len(fails) >= 1


def test_inside_envelope_checker(plan_2bhk: PlanData, plan_violations: PlanData, sample_envelope: Envelope):
    rule = RuleDefinition(
        id="bylaws-inside-envelope",
        title="Building Footprint Inside Envelope",
        clause="Model Bylaws Clause 3.1",
        category="setback",
        applies_to="plan",
        check="inside_envelope",
        params={},
        severity="fail",
        verified=True,
    )
    # 2BHK is 10m x 10m, envelope is 12m x 12m -> inside
    issues_pass = check_inside_envelope(plan_2bhk, sample_envelope, rule)
    assert not any(i.status == "fail" for i in issues_pass)

    # Violations plan extends to X=25000 mm -> outside 12000 mm envelope
    issues_fail = check_inside_envelope(plan_violations, sample_envelope, rule)
    fails = [i for i in issues_fail if i.status == "fail"]
    assert len(fails) >= 1
    assert any("room-outside-boundary" in i.element_ids for i in fails)


def test_unverified_rule_can_only_return_review():
    """Rules with verified: false MUST return status 'review', never 'fail'."""
    raw = json.loads((FIXTURES_DIR / "plan_violations.json").read_text())
    plan = PlanData.model_validate(raw)

    unverified_rule = RuleDefinition(
        id="unverified-experimental-rule",
        title="Unverified Height Rule",
        clause="Local Gazette Draft 2026",
        category="height",
        applies_to="level",
        check="min_ceiling_height",
        params={"min_height_mm": 3500},
        severity="fail",
        verified=False,  # Unverified!
        notes="TODO: source",
    )
    issues = check_min_ceiling_height(plan, None, unverified_rule)
    assert len(issues) >= 1
    for issue in issues:
        assert issue.status != "fail"
        assert issue.status == "review"
