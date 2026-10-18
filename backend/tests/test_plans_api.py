"""Integration tests for Plans, Patches, Undo/Redo, Diff and Review API (Phase 3)."""

import json
from pathlib import Path
import pytest
from httpx import AsyncClient

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "plans"


@pytest.fixture
def plan_2bhk_raw() -> dict:
    return json.loads((FIXTURES_DIR / "plan_2bhk_single_floor.json").read_text())


@pytest.mark.asyncio
async def test_plans_api_lifecycle(client: AsyncClient, auth_headers: dict, plan_2bhk_raw: dict):
    # 1. Create a project
    create_proj_res = await client.post(
        "/api/v1/projects",
        json={"name": "Plan Test Residence", "description": "Testing plan versioning"},
        headers=auth_headers,
    )
    assert create_proj_res.status_code == 201
    project_id = create_proj_res.json()["id"]

    # 2. Create initial plan
    create_plan_res = await client.post(
        f"/api/v1/projects/{project_id}/plans",
        json={"name": "Ground Floor Scheme A", "data": plan_2bhk_raw, "message": "Initial scheme import"},
        headers=auth_headers,
    )
    assert create_plan_res.status_code == 201
    plan = create_plan_res.json()
    plan_id = plan["id"]
    assert plan["current_version"] == 1

    # 3. Get plan
    get_res = await client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["current_version"] == 1
    assert len(get_res.json()["data"]["levels"]) == 1

    # 4. Apply Patches -> creates version 2
    patch_payload = {
        "message": "Enlarge master bedroom wall",
        "patches": [
            {
                "type": "set_wall_thickness",
                "wall_id": "wall-ext-north",
                "thickness_mm": 250,
            },
            {
                "type": "rename_room",
                "room_id": "room-bed1",
                "new_name": "Primary Master Suite",
            },
        ],
    }
    patch_res = await client.post(
        f"/api/v1/plans/{plan_id}/patches",
        json=patch_payload,
        headers=auth_headers,
    )
    assert patch_res.status_code == 200
    updated_plan = patch_res.json()
    assert updated_plan["current_version"] == 2

    # 5. Get Diff between version 1 and 2
    diff_res = await client.get(
        f"/api/v1/plans/{plan_id}/diff?from_version=1&to_version=2",
        headers=auth_headers,
    )
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert len(diff_data["modified_walls"]) >= 1

    # 6. Test Undo (returns to version 1)
    undo_res = await client.post(f"/api/v1/plans/{plan_id}/undo", headers=auth_headers)
    assert undo_res.status_code == 200
    assert undo_res.json()["current_version"] == 1

    # 7. Test Redo (returns to version 2)
    redo_res = await client.post(f"/api/v1/plans/{plan_id}/redo", headers=auth_headers)
    assert redo_res.status_code == 200
    assert redo_res.json()["current_version"] == 2

    # 8. List Versions
    versions_res = await client.get(f"/api/v1/plans/{plan_id}/versions", headers=auth_headers)
    assert versions_res.status_code == 200
    versions = versions_res.json()
    assert len(versions) == 2

    # 9. Run Review on current plan
    review_res = await client.post(f"/api/v1/plans/{plan_id}/review", headers=auth_headers)
    assert review_res.status_code == 200
    review_data = review_res.json()
    assert "issues" in review_data
    assert "summary" in review_data
