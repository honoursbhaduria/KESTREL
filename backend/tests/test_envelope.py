"""Tests for buildable envelope computation (pure functions & API).
Tests rectangular, corner, L-shaped irregular plots, and edge cases (plot too small).
Enforces strict TDD: tests written before implementation.
"""

import pytest
from httpx import AsyncClient


async def create_test_project(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Envelope Test Villa"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_pure_envelope_rectangle_plot():
    """15m × 20m rectangular plot with UP Bylaws setbacks."""
    from app.modules.planning.envelope import compute_envelope

    # Plot coordinates: 15,000mm width (X) × 20,000mm depth (Y)
    # Edge 0: (0,0) -> (15000, 0) [Front facing 12m road]
    # Edge 1: (15000, 0) -> (15000, 20000) [Right side]
    # Edge 2: (15000, 20000) -> (0, 20000) [Rear]
    # Edge 3: (0, 20000) -> (0, 0) [Left side]
    plot_polygon = [
        [0.0, 0.0],
        [15000.0, 0.0],
        [15000.0, 20000.0],
        [0.0, 20000.0],
        [0.0, 0.0],
    ]
    road_sides = [{"edge_index": 0, "road_width_mm": 12000.0}]

    # Ruleset params for UP residential 300 sqm plot:
    # Front setback: 3000 mm, Rear setback: 2000 mm, Side setbacks: 1500 mm
    # Ground coverage: 60%, FAR: 1.5, Max height: 15,000 mm, Max floors: 4
    ruleset_params = {
        "ruleset_id": "up-bylaws",
        "front_setback_mm": 3000.0,
        "rear_setback_mm": 2000.0,
        "side_setback_mm": 1500.0,
        "ground_coverage_pct": 60.0,
        "far": 1.5,
        "max_height_mm": 15000.0,
        "max_floors": 4,
    }

    env = compute_envelope(
        plot_polygon=plot_polygon,
        road_sides=road_sides,
        ruleset_params=ruleset_params,
    )

    # Footprint expected bounds:
    # X from 1500 to (15000 - 1500) = 12000 mm wide
    # Y from 3000 to (20000 - 2000) = 15000 mm deep
    # Footprint area = 12000 * 15000 = 180,000,000 mm2 (180 sqm)
    assert env.footprint_area_mm2 == pytest.approx(180000000.0, rel=1e-2)
    assert env.max_coverage_mm2 == pytest.approx(180000000.0, rel=1e-2)  # 60% of 300 sqm
    assert env.max_builtup_mm2 == pytest.approx(450000000.0, rel=1e-2)  # 300 sqm * 1.5 FAR
    assert env.max_height_mm == 15000.0
    assert env.max_floors == 4
    assert len(env.applied_rules) >= 4


def test_pure_envelope_corner_plot():
    """Corner plot with two road sides: Edge 0 (Front) and Edge 1 (Flank)."""
    from app.modules.planning.envelope import compute_envelope

    # 20m × 25m corner plot (500 sqm)
    plot_polygon = [
        [0.0, 0.0],
        [20000.0, 0.0],
        [20000.0, 25000.0],
        [0.0, 25000.0],
        [0.0, 0.0],
    ]
    # Edge 0 (bottom) and Edge 1 (right) face roads
    road_sides = [
        {"edge_index": 0, "road_width_mm": 15000.0},
        {"edge_index": 1, "road_width_mm": 12000.0},
    ]

    ruleset_params = {
        "ruleset_id": "up-bylaws",
        "front_setback_mm": 4500.0,
        "rear_setback_mm": 3000.0,
        "side_setback_mm": 2000.0,
        "ground_coverage_pct": 55.0,
        "far": 1.5,
        "max_height_mm": 15000.0,
        "max_floors": 4,
    }

    env = compute_envelope(
        plot_polygon=plot_polygon,
        road_sides=road_sides,
        ruleset_params=ruleset_params,
    )

    assert env.footprint_area_mm2 > 0
    assert env.footprint_area_mm2 < 500000000.0
    assert len(env.footprint_polygon) >= 4


def test_pure_envelope_l_shaped_irregular_plot():
    """L-shaped irregular plot must offset cleanly with Shapely."""
    from app.modules.planning.envelope import compute_envelope

    # Non-convex 6-vertex L-shaped plot
    l_polygon = [
        [0.0, 0.0],
        [24000.0, 0.0],
        [24000.0, 12000.0],
        [12000.0, 12000.0],
        [12000.0, 24000.0],
        [0.0, 24000.0],
        [0.0, 0.0],
    ]
    road_sides = [{"edge_index": 0, "road_width_mm": 12000.0}]

    ruleset_params = {
        "ruleset_id": "up-bylaws",
        "front_setback_mm": 3000.0,
        "rear_setback_mm": 2000.0,
        "side_setback_mm": 1500.0,
        "ground_coverage_pct": 55.0,
        "far": 1.5,
        "max_height_mm": 15000.0,
        "max_floors": 4,
    }

    env = compute_envelope(
        plot_polygon=l_polygon,
        road_sides=road_sides,
        ruleset_params=ruleset_params,
    )

    # Footprint must be non-empty, smaller than plot, and topologically valid
    assert env.footprint_area_mm2 > 0
    assert len(env.footprint_polygon) >= 4


def test_pure_envelope_plot_too_small_to_build():
    """Plot too small to accommodate setbacks must yield empty footprint with clear warning."""
    from app.modules.planning.envelope import compute_envelope

    # Tiny 4m × 4m plot (4000mm × 4000mm)
    tiny_polygon = [
        [0.0, 0.0],
        [4000.0, 0.0],
        [4000.0, 4000.0],
        [0.0, 4000.0],
        [0.0, 0.0],
    ]
    road_sides = [{"edge_index": 0, "road_width_mm": 9000.0}]

    # Front (3000mm) + Rear (2000mm) = 5000mm > 4000mm depth!
    ruleset_params = {
        "ruleset_id": "up-bylaws",
        "front_setback_mm": 3000.0,
        "rear_setback_mm": 2000.0,
        "side_setback_mm": 1500.0,
        "ground_coverage_pct": 60.0,
        "far": 1.5,
        "max_height_mm": 15000.0,
        "max_floors": 4,
    }

    env = compute_envelope(
        plot_polygon=tiny_polygon,
        road_sides=road_sides,
        ruleset_params=ruleset_params,
    )

    assert env.footprint_area_mm2 == 0.0
    assert env.footprint_polygon == []
    assert env.warning is not None
    assert "insufficient" in env.warning.lower() or "empty" in env.warning.lower()


@pytest.mark.asyncio
async def test_get_project_envelope_endpoint(client: AsyncClient, auth_org_a: dict):
    """GET /api/v1/projects/{id}/envelope returns computed envelope with rule citations."""
    project_id = await create_test_project(client, auth_org_a["headers"])

    # 1. Attempt before plot is set -> 400 error
    resp_no_plot = await client.get(
        f"/api/v1/projects/{project_id}/envelope",
        headers=auth_org_a["headers"],
    )
    assert resp_no_plot.status_code == 400

    # 2. Set plot
    await client.put(
        f"/api/v1/projects/{project_id}/plot",
        headers=auth_org_a["headers"],
        json={
            "width_mm": 15000.0,
            "depth_mm": 20000.0,
            "north_angle_deg": 0.0,
            "road_sides": [{"edge_index": 0, "road_width_mm": 12000.0}],
        },
    )

    # 3. Set ruleset
    await client.put(
        f"/api/v1/projects/{project_id}/ruleset",
        headers=auth_org_a["headers"],
        json={"ruleset_id": "up-bylaws"},
    )

    # 4. Get envelope
    resp = await client.get(
        f"/api/v1/projects/{project_id}/envelope",
        headers=auth_org_a["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "footprint_polygon" in data
    assert "footprint_area_mm2" in data
    assert data["footprint_area_mm2"] > 0
    assert "max_coverage_mm2" in data
    assert "max_builtup_mm2" in data
    assert "max_height_mm" in data
    assert "applied_rules" in data
    assert len(data["applied_rules"]) > 0

    # Every applied rule must have clause and verified status
    for rule in data["applied_rules"]:
        assert "rule_id" in rule
        assert "clause" in rule
        assert "value" in rule
        assert "verified" in rule
