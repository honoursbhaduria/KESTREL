"""Tests for projects module CRUD operations and validation."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_project(client: AsyncClient, auth_org_a: dict):
    """Creating a project stores it scoped to the active organization."""
    payload = {
        "name": "Courtyard Residence",
        "description": "Modern sustainable residential layout",
    }
    create_resp = await client.post(
        "/api/v1/projects",
        json=payload,
        headers=auth_org_a["headers"],
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["name"] == payload["name"]
    assert created["description"] == payload["description"]
    assert created["org_id"] == auth_org_a["org"]["id"]
    project_id = created["id"]

    # Read back project
    get_resp = await client.get(
        f"/api/v1/projects/{project_id}",
        headers=auth_org_a["headers"],
    )
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["id"] == project_id
    assert fetched["name"] == payload["name"]


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, auth_org_a: dict):
    """Updating project name and description returns the modified entity."""
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Initial Name", "description": "Initial Desc"},
        headers=auth_org_a["headers"],
    )
    project_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/projects/{project_id}",
        json={"name": "Updated Name", "description": "Updated Desc"},
        headers=auth_org_a["headers"],
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["name"] == "Updated Name"
    assert updated["description"] == "Updated Desc"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, auth_org_a: dict):
    """Deleting a project returns 204 No Content, subsequent GET returns 404."""
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "To Be Deleted", "description": "Temp"},
        headers=auth_org_a["headers"],
    )
    project_id = create_resp.json()["id"]

    delete_resp = await client.delete(
        f"/api/v1/projects/{project_id}",
        headers=auth_org_a["headers"],
    )
    assert delete_resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/projects/{project_id}",
        headers=auth_org_a["headers"],
    )
    assert get_resp.status_code == 404
    assert get_resp.json()["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_project_validation_error_shape(client: AsyncClient, auth_org_a: dict):
    """Invalid requests return HTTP 422 with the standardized error response envelope."""
    # Empty name should fail validation
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "", "description": "No name provided"},
        headers=auth_org_a["headers"],
    )
    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert "message" in data
    assert "details" in data
