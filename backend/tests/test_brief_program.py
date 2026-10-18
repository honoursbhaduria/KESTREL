"""Tests for Brief-to-Program structuring, envelope feasibility checking, and program editing."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def project_with_plot_and_envelope(client: AsyncClient, auth_org_a: dict) -> dict:
    """Create project, set ruleset to UP bylaws, set 200 sqm rectangle plot."""
    headers = auth_org_a["headers"]
    # 1. Create project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Generative Villa"},
        headers=headers,
    )
    assert resp.status_code == 201
    proj_id = resp.json()["id"]

    # 2. Set ruleset
    await client.put(
        f"/api/v1/projects/{proj_id}/ruleset",
        json={"ruleset_id": "up-bylaws"},
        headers=headers,
    )

    # 3. Set plot: 10m x 20m = 200 sqm (10000mm x 20000mm)
    plot_coords = [
        [0.0, 0.0],
        [10000.0, 0.0],
        [10000.0, 20000.0],
        [0.0, 20000.0],
    ]
    resp = await client.put(
        f"/api/v1/projects/{proj_id}/plot",
        json={
            "boundary_coords": plot_coords,
            "road_sides": [{"edge_index": 0, "road_width_m": 12.0}],
            "north_angle_deg": 0.0,
        },
        headers=headers,
    )
    assert resp.status_code == 200

    return {"project_id": proj_id, "headers": headers}


@pytest.mark.asyncio
async def test_put_brief_structures_program(
    client: AsyncClient, project_with_plot_and_envelope: dict
):
    """Verify PUT /projects/{id}/brief parses free text into structured Program."""
    proj_id = project_with_plot_and_envelope["project_id"]
    headers = project_with_plot_and_envelope["headers"]

    brief_text = (
        "Design a 2-storey 3BHK house. Ground floor: living room, open modular kitchen, "
        "dining, pooja room, guest bedroom with attached bath, powder toilet, stair. "
        "First floor: master bedroom with walk-in closet and bath, kids bedroom with bath, "
        "family lounge. East-facing entrance, Vastu compliant, front parking."
    )

    resp = await client.put(
        f"/api/v1/projects/{proj_id}/brief",
        json={"brief_text": brief_text},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "program" in data
    assert "feasibility" in data
    program = data["program"]
    assert program["levels"] == 2
    assert len(program["rooms"]) >= 7

    # Check key rooms exist
    room_names = [r["name"].lower() for r in program["rooms"]]
    assert any("living" in name for name in room_names)
    assert any("kitchen" in name for name in room_names)
    assert any("master" in name or "bedroom" in name for name in room_names)

    # Check preferences
    assert program["preferences"]["vastu"] is True
    assert program["preferences"]["entrance_side"].lower() == "east"

    # Check feasibility object
    feasibility = data["feasibility"]
    assert "is_feasible" in feasibility
    assert "total_proposed_area_sqm" in feasibility
    assert "max_builtup_area_sqm" in feasibility


@pytest.mark.asyncio
async def test_brief_feasibility_rejects_exorbitant_far(
    client: AsyncClient, project_with_plot_and_envelope: dict
):
    """When brief requests total area far exceeding permissible FAR, return clear explanation and suggestion."""
    proj_id = project_with_plot_and_envelope["project_id"]
    headers = project_with_plot_and_envelope["headers"]

    # Request an impossible 800 sqm mansion on a 200 sqm plot with FAR 1.5 (max 300 sqm)
    brief_text = (
        "Huge mansion with 10 master suites of 50 sqm each, Olympic indoor pool of 100 sqm, "
        "grand ballroom of 150 sqm, 4-car garage, home theater, total 800 sqm."
    )

    resp = await client.put(
        f"/api/v1/projects/{proj_id}/brief",
        json={"brief_text": brief_text},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    feasibility = data["feasibility"]

    assert feasibility["is_feasible"] is False
    assert "FAR" in feasibility["explanation"] or "built-up" in feasibility["explanation"]
    assert feasibility["suggested_program"] is not None
    # Suggested program should scale down target areas so it fits within FAR
    suggested_total = sum(
        r["target_area_mm2"] for r in feasibility["suggested_program"]["rooms"]
    ) / 1e6
    assert suggested_total <= feasibility["max_builtup_area_sqm"] + 1.0


@pytest.mark.asyncio
async def test_get_and_put_program_customization(
    client: AsyncClient, project_with_plot_and_envelope: dict
):
    """Verify GET /program and PUT /program allowing user to edit room areas/adjacencies."""
    proj_id = project_with_plot_and_envelope["project_id"]
    headers = project_with_plot_and_envelope["headers"]

    # First initialize with brief
    await client.put(
        f"/api/v1/projects/{proj_id}/brief",
        json={"brief_text": "Compact 2BHK 1 floor house, living, kitchen, 2 bedrooms, 1 bath."},
        headers=headers,
    )

    # Fetch program
    get_resp = await client.get(f"/api/v1/projects/{proj_id}/program", headers=headers)
    assert get_resp.status_code == 200
    current_prog = get_resp.json()["program"]

    # Modify program: change living room target area and add an adjacency
    for r in current_prog["rooms"]:
        if "living" in r["name"].lower():
            r["target_area_mm2"] = 25_000_000.0  # 25 sqm

    current_prog["adjacencies"].append({
        "a": "Living Room",
        "b": "Kitchen",
        "strength": "must",
    })

    # Update via PUT /program
    put_resp = await client.put(
        f"/api/v1/projects/{proj_id}/program",
        json={"program": current_prog},
        headers=headers,
    )
    assert put_resp.status_code == 200
    updated_data = put_resp.json()
    updated_prog = updated_data["program"]

    # Verify updated living room area
    living = next(r for r in updated_prog["rooms"] if "living" in r["name"].lower())
    assert living["target_area_mm2"] == 25_000_000.0
    assert any(adj["strength"] == "must" for adj in updated_prog["adjacencies"])
