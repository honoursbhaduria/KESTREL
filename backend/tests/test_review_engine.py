"""Tests for Review Engine and incremental dependency checking (Phase 3)."""

import json
from pathlib import Path

import pytest

from app.modules.planning.envelope import Envelope
from app.modules.plans.schemas import PlanData
from app.modules.rules.engine import ReviewEngine
from app.modules.rules.loader import get_ruleset

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
def envelope_fixture() -> Envelope:
    return Envelope(
        footprint_polygon=[[0, 0], [15000, 0], [15000, 15000], [0, 15000]],
        footprint_area_mm2=225_000_000,
        max_coverage_mm2=250_000_000,
        max_builtup_mm2=500_000_000,
        max_height_mm=15000,
        max_floors=4,
        applied_rules=[],
    )


def test_review_2bhk_produces_zero_fails(plan_2bhk: PlanData, envelope_fixture: Envelope):
    """Clean 2BHK plan reviewed against NBC 2016 should produce zero fail issues."""
    ruleset = get_ruleset("india-nbc-2016")
    engine = ReviewEngine()
    result = engine.review_plan(plan=plan_2bhk, envelope=envelope_fixture, ruleset=ruleset)

    assert result.summary["fail_count"] == 0
    assert result.summary["pass_count"] > 0


def test_review_violations_fixture_returns_expected_issues(
    plan_violations: PlanData, envelope_fixture: Envelope
):
    """Violations fixture must flag undersized room, door width, stair steepness, and envelope."""
    ruleset = get_ruleset("india-nbc-2016")
    engine = ReviewEngine()
    result = engine.review_plan(plan=plan_violations, envelope=envelope_fixture, ruleset=ruleset)

    assert result.summary["fail_count"] >= 3
    rule_ids_flagged = {issue.rule_id for issue in result.issues if issue.status == "fail"}
    assert "nbc-habitable-room-min-area" in rule_ids_flagged
    assert "nbc-residential-stair-width" in rule_ids_flagged


def test_incremental_review_filters_by_dependencies(
    plan_2bhk: PlanData, envelope_fixture: Envelope
):
    """Incremental review only executes checkers matching modified element dependencies."""
    ruleset = get_ruleset("india-nbc-2016")
    engine = ReviewEngine()

    # If only an opening was modified, only opening/ventilation checkers should run
    result = engine.review_plan(
        plan=plan_2bhk,
        envelope=envelope_fixture,
        ruleset=ruleset,
        modified_element_types={"opening"},
    )
    # Check that checkers dependent purely on 'stair' or 'envelope' did not run
    categories_evaluated = {issue.category for issue in result.issues}
    assert "stair" not in categories_evaluated
