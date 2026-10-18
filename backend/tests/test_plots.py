"""Tests for plot definition, validation, and spatial properties (Phase 2).
Enforces strict TDD: tests written before implementation.
"""

import pytest
from httpx import AsyncClient


async def create_test_project(client: AsyncClient, headers: dict) -> str:
    """Helper to create a fresh test project and return its ID."""
    resp = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Plot Test Villa", "description": "Phase 2 plot testing project"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_put_plot_width_depth_success(client: AsyncClient, auth_org_a: dict):
    """Setting plot using simple width × depth creates a closed rectangular polygon."""
    project_id = await create_test_project(client, auth_org_a["headers"])

    payload = {
        "width_mm": 15000.0,
        "depth_mm": 20000.0,
        "north_angle_deg": 45.0,
        "road_sides": [{"edge_index": 0, "road_width_mm": 12000.0}],
    }

    resp = await client.put(
        f"/api/v1/projects/{project_id}/plot",
        headers=auth_org_a["headers"],
        json=payload,
    )
    assert resp.status_code == 200, f"Failed: {resp.text}"
    data = resp.json()

    assert data["project_id"] == project_id
    assert data["north_angle_deg"] == 45.0
    assert len(data["road_sides"]) == 1
    assert data["road_sides"][0]["edge_index"] == 0
    assert data["road_sides"][0]["road_width_mm"] == 12000.0

    # 15m × 20m = 300 m2 = 300,000,000 mm2
    assert abs(data["plot_area_mm2"] - 300000000.0) < 1.0

    # Boundary polygon coordinates: 5 points (closed loop)
    coords = data["boundary"]
    assert len(coords) == 5
    assert coords[0] == coords[-1]
    assert coords[0] == [0.0, 0.0]
    assert coords[1] == [15000.0, 0.0]
    assert coords[2] == [15000.0, 20000.0]
    assert coords[3] == [0.0, 20000.0]


@pytest.mark.asyncio
async def test_put_plot_explicit_polygon_success(client: AsyncClient, auth_org_a: dict):
    """Setting plot using explicit 2D polygon vertices in mm."""
    project_id = await create_test_project(client, auth_org_a["headers"])

    # Trapezoidal plot: base 20m, top 12m, depth 25m
    polygon = [
        [0.0, 0.0],
        [20000.0, 0.0],
        [16000.0, 25000.0],
        [4000.0, 25000.0],
        [0.0, 0.0],
    ]

    payload = {
        "boundary": polygon,
        "north_angle_deg": 0.0,
        "road_sides": [{"edge_index": 0, "road_width_mm": 9000.0}],
    }

    resp = await client.put(
        f"/api/v1/projects/{project_id}/plot",
        headers=auth_org_a["headers"],
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Trapezoid area = (20m + 12m) / 2 * 25m = 400 m2 = 400,000,000 mm2
    assert abs(data["plot_area_mm2"] - 400000000.0) < 1.0
    assert data["boundary"] == polygon


@pytest.mark.asyncio
async def test_put_plot_rejects_self_intersecting_polygon(client: AsyncClient, auth_org_a: dict):
    """Self-intersecting polygon (bowtie / figure 8) must be rejected with 422/400."""
    project_id = await create_test_project(client, auth_org_a["headers"])

    # Bowtie polygon crossing at center
    self_intersecting = [
        [0.0, 0.0],
        [10000.0, 10000.0],
        [10000.0, 0.0],
        [0.0, 10000.0],
        [0.0, 0.0],
    ]

    payload = {
        "boundary": self_intersecting,
        "north_angle_deg": 0.0,
    }

    resp = await client.put(
        f"/api/v1/projects/{project_id}/plot",
        headers=auth_org_a["headers"],
        json=payload,
    )
    assert resp.status_code in (400, 422)
    err = resp.json()
    assert "code" in err or "detail" in err


@pytest.mark.asyncio
async def test_put_plot_rejects_unclosed_polygon(client: AsyncClient, auth_org_a: dict):
    """Polygon where last coordinate != first coordinate must be auto-closed or validated."""
    project_id = await create_test_project(client, auth_org_a["headers"])

    unclosed = [
        [0.0, 0.0],
        [15000.0, 0.0],
        [15000.0, 20000.0],
        [0.0, 20000.0],
    ]

    payload = {
        "boundary": unclosed,
        "north_angle_deg": 0.0,
    }

    resp = await client.put(
        f"/api/v1/projects/{project_id}/plot",
        headers=auth_org_a["headers"],
        json=payload,
    )
    # Backend should either auto-close it into 5 vertices or reject with 422
    if resp.status_code == 200:
        data = resp.json()
        assert data["boundary"][0] == data["boundary"][-1]
    else:
        assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_put_plot_rejects_fewer_than_3_vertices(client: AsyncClient, auth_org_a: dict):
    """Plot with fewer than 3 unique vertices cannot form a 2D surface."""
    project_id = await create_test_project(client, auth_org_a["headers"])

    degenerate = [
        [0.0, 0.0],
        [15000.0, 0.0],
        [0.0, 0.0],
    ]

    payload = {"boundary": degenerate}
    resp = await client.put(
        f"/api/v1/projects/{project_id}/plot",
        headers=auth_org_a["headers"],
        json=payload,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_put_plot_rejects_insane_bounds(client: AsyncClient, auth_org_a: dict):
    """Plot smaller than 10 sqm or larger than 1,000,000 sqm must be rejected."""
    project_id = await create_test_project(client, auth_org_a["headers"])

    # Tiny 2m × 2m plot (4 m2)
    tiny_plot = {
        "width_mm": 2000.0,
        "depth_mm": 2000.0,
    }
    resp = await client.put(
        f"/api/v1/projects/{project_id}/plot",
        headers=auth_org_a["headers"],
        json=tiny_plot,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_get_plot_returns_persisted_plot(client: AsyncClient, auth_org_a: dict):
    """GET /api/v1/projects/{id}/plot returns the persisted plot."""
    project_id = await create_test_project(client, auth_org_a["headers"])

    # Set plot
    await client.put(
        f"/api/v1/projects/{project_id}/plot",
        headers=auth_org_a["headers"],
        json={
            "width_mm": 18000.0,
            "depth_mm": 22000.0,
            "north_angle_deg": 90.0,
            "road_sides": [{"edge_index": 0, "road_width_mm": 18000.0}],
        },
    )

    # Get plot
    resp = await client.get(
        f"/api/v1/projects/{project_id}/plot",
        headers=auth_org_a["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == project_id
    assert data["north_angle_deg"] == 90.0
    assert abs(data["plot_area_mm2"] - (18000.0 * 22000.0)) < 1.0


@pytest.mark.asyncio
async def test_plot_tenancy_isolation(client: AsyncClient, auth_org_a: dict, auth_org_b: dict):
    """Org B cannot read or update Org A's plot (must yield 404, not 403)."""
    project_id = await create_test_project(client, auth_org_a["headers"])

    # Org A sets plot
    await client.put(
        f"/api/v1/projects/{project_id}/plot",
        headers=auth_org_a["headers"],
        json={"width_mm": 15000.0, "depth_mm": 20000.0},
    )

    # Org B attempts to read Org A's plot
    resp_get = await client.get(
        f"/api/v1/projects/{project_id}/plot",
        headers=auth_org_b["headers"],
    )
    assert resp_get.status_code == 404

    # Org B attempts to overwrite Org A's plot
    resp_put = await client.put(
        f"/api/v1/projects/{project_id}/plot",
        headers=auth_org_b["headers"],
        json={"width_mm": 10000.0, "depth_mm": 10000.0},
    )
    assert resp_put.status_code == 404
