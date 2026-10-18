"""Tests for Assistant Tools.
TDD specification for the 6 core assistant tools:
1. get_plan_summary
2. get_issues
3. run_check
4. measure
5. search_rules
6. propose_fix
"""

import uuid

import pytest
from sqlalchemy import select

from app.modules.assistant.tools import (
    get_issues,
    get_plan_summary,
    measure,
    propose_fix,
    run_check,
    search_rules,
)
from app.modules.auth.models import Organization
from app.modules.plans.models import Plan, PlanVersion
from app.modules.plans.schemas import Level, Opening, PlanData, Room, Stair, Wall
from app.modules.projects.models import Project
from tests.conftest import TestingSessionLocal


@pytest.fixture
async def sample_plan_id() -> str:
    """Seed a project and a plan with known rooms, walls, and an undersized room for rule checking."""
    async with TestingSessionLocal() as session:
        org_id = uuid.uuid4()
        org = Organization(id=org_id, name="Tool Test Studio", slug=f"tool-test-{org_id.hex[:6]}")
        session.add(org)
        await session.flush()

        project = Project(
            org_id=org_id,
            name="Assistant Test Villa",
            ruleset_id="india-nbc-2016",
        )
        session.add(project)
        await session.flush()

        plan_data = PlanData(
            units="mm",
            levels=[
                Level(
                    id="lvl_1",
                    name="Ground Floor",
                    elevation_mm=0.0,
                    floor_to_floor_mm=3000.0,
                    rooms=[
                        # Undersized bedroom (7.5 sqm < 9.5 sqm minimum required by NBC 2016)
                        Room(
                            id="room_bed_1",
                            name="Guest Bedroom",
                            type="bedroom",
                            polygon=[[0.0, 0.0], [3000.0, 0.0], [3000.0, 2500.0], [0.0, 2500.0]],
                        ),
                        Room(
                            id="room_living_1",
                            name="Living Room",
                            type="living",
                            polygon=[[3000.0, 0.0], [8000.0, 0.0], [8000.0, 4000.0], [3000.0, 4000.0]],
                        ),
                    ],
                    walls=[
                        Wall(
                            id="wall_w1",
                            start=[0.0, 0.0],
                            end=[3000.0, 0.0],
                            thickness_mm=200.0,
                            is_external=True,
                        ),
                        Wall(
                            id="wall_shared",
                            start=[3000.0, 0.0],
                            end=[3000.0, 2500.0],
                            thickness_mm=100.0,
                            is_external=False,
                        ),
                    ],
                    openings=[
                        Opening(
                            id="op_door_1",
                            wall_id="wall_shared",
                            kind="door",
                            offset_mm=500.0,
                            width_mm=900.0,
                            height_mm=2100.0,
                            sill_mm=0.0,
                        )
                    ],
                    stairs=[
                        Stair(
                            id="stair_1",
                            polygon=[[0.0, 3000.0], [2000.0, 3000.0], [2000.0, 6000.0], [0.0, 6000.0]],
                            riser_mm=150.0,
                            tread_mm=250.0,
                            direction="up",
                        )
                    ],
                )
            ],
        )

        plan = Plan(
            org_id=org_id,
            project_id=project.id,
            name="Primary Ground Plan",
            current_version=1,
        )
        session.add(plan)
        await session.flush()

        version = PlanVersion(
            plan_id=plan.id,
            version=1,
            parent_version=None,
            data=plan_data.model_dump(),
            created_by="user",
            message="Initial plan version",
        )
        session.add(version)
        await session.commit()
        return str(plan.id)


@pytest.mark.asyncio
async def test_tool_get_plan_summary(sample_plan_id: str):
    """get_plan_summary should return room count, level count, total area, and structural elements."""
    async with TestingSessionLocal() as session:
        summary = await get_plan_summary(session, sample_plan_id)
        assert summary["plan_id"] == sample_plan_id
        assert summary["current_version"] == 1
        assert summary["level_count"] == 1
        assert summary["room_count"] == 2
        assert summary["wall_count"] == 2
        assert summary["opening_count"] == 1
        assert summary["stair_count"] == 1
        assert "total_area_sqm" in summary
        assert summary["total_area_sqm"] > 0


@pytest.mark.asyncio
async def test_tool_get_issues(sample_plan_id: str):
    """get_issues should review the plan and return issues, respecting status filter."""
    async with TestingSessionLocal() as session:
        all_issues = await get_issues(session, sample_plan_id)
        assert isinstance(all_issues, list)
        assert len(all_issues) > 0

        # The undersized bedroom (7.5 sqm) MUST fail the 9.5 sqm rule
        fails = await get_issues(session, sample_plan_id, status="fail")
        assert any("room_bed_1" in issue.get("element_ids", []) for issue in fails)

        passes = await get_issues(session, sample_plan_id, status="pass")
        assert all(i["status"] == "pass" for i in passes)


@pytest.mark.asyncio
async def test_tool_run_check(sample_plan_id: str):
    """run_check executes a specific rule check and returns finding details with clause reference."""
    async with TestingSessionLocal() as session:
        res = await run_check(
            session,
            plan_id=sample_plan_id,
            rule_id="nbc-habitable-room-min-area",
        )
        assert res["rule_id"] == "nbc-habitable-room-min-area"
        assert "clause" in res
        assert res["status"] in ("fail", "review", "pass")
        assert len(res["issues"]) > 0


@pytest.mark.asyncio
async def test_tool_measure(sample_plan_id: str):
    """measure computes dimensions, areas, and clearances for specified element IDs."""
    async with TestingSessionLocal() as session:
        # Measure a room
        room_meas = await measure(session, sample_plan_id, element_ids=["room_bed_1"])
        assert "room_bed_1" in room_meas
        assert room_meas["room_bed_1"]["area_sqm"] == pytest.approx(7.5, rel=1e-2)
        assert room_meas["room_bed_1"]["width_mm"] == pytest.approx(2500.0, rel=1e-2)
        assert room_meas["room_bed_1"]["length_mm"] == pytest.approx(3000.0, rel=1e-2)

        # Measure a wall
        wall_meas = await measure(session, sample_plan_id, element_ids=["wall_w1"])
        assert "wall_w1" in wall_meas
        assert wall_meas["wall_w1"]["length_mm"] == pytest.approx(3000.0, rel=1e-2)
        assert wall_meas["wall_w1"]["thickness_mm"] == 200.0


@pytest.mark.asyncio
async def test_tool_search_rules():
    """search_rules performs semantic/keyword search over statutory clauses."""
    results = await search_rules(query="habitable room minimum size area", limit=3)
    assert isinstance(results, list)
    assert len(results) > 0
    assert "clause" in results[0]
    assert "content" in results[0] or "description" in results[0]


@pytest.mark.asyncio
async def test_tool_propose_fix_creates_fix_row_without_updating_plan_version(
    sample_plan_id: str,
):
    """propose_fix creates a Fix row with status 'proposed', calculates diff, and leaves plan untouched."""
    async with TestingSessionLocal() as session:
        # Expand room_bed_1 from 7.5 sqm to 12.0 sqm without overlapping room_living_1
        patch_ops = [
            {
                "op": "set_room_polygon",
                "room_id": "room_bed_1",
                "polygon": [[0.0, -1500.0], [3000.0, -1500.0], [3000.0, 2500.0], [0.0, 2500.0]],
            }
        ]

        fix = await propose_fix(
            session,
            plan_id=sample_plan_id,
            ops=patch_ops,
            rationale="Enlarge guest bedroom to 12.0 sqm to satisfy NBC 2016 minimum 9.5 sqm requirement",
            rule_id="nbc-habitable-room-min-area",
        )

        assert fix["id"] is not None
        assert fix["status"] == "proposed"
        assert "diff_summary" in fix
        assert "resolved" in fix["diff_summary"]
        assert "introduced" in fix["diff_summary"]
        assert fix["introduced_fails"] == 0

        # Ensure plan version in database was NOT modified
        plan = (
            await session.execute(select(Plan).where(Plan.id == uuid.UUID(sample_plan_id)))
        ).scalars().first()
        assert plan is not None
        assert plan.current_version == 1
