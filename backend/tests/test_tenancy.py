"""Tests for strict multi-tenant isolation.
Crucial invariant: accessing another organization's project returns 404 Not Found (NEVER 403 Forbidden)
to prevent resource enumeration.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tenancy_isolation_read(client: AsyncClient, auth_org_a: dict, auth_org_b: dict):
    """User from Org B cannot read Org A's project (returns 404, not 403)."""
    # 1. Org A creates a project
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Villa Serene", "description": "Org A Luxury Villa"},
        headers=auth_org_a["headers"],
    )
    assert create_resp.status_code == 201
    project_a_id = create_resp.json()["id"]

    # 2. Org A can read its own project
    read_a = await client.get(f"/api/v1/projects/{project_a_id}", headers=auth_org_a["headers"])
    assert read_a.status_code == 200
    assert read_a.json()["id"] == project_a_id

    # 3. Org B attempts to read Org A's project -> MUST BE 404
    read_b = await client.get(f"/api/v1/projects/{project_a_id}", headers=auth_org_b["headers"])
    assert read_b.status_code == 404
    error = read_b.json()
    assert error["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_tenancy_isolation_update(client: AsyncClient, auth_org_a: dict, auth_org_b: dict):
    """User from Org B cannot update Org A's project (returns 404, not 403)."""
    # Org A creates a project
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Mountain Retreat", "description": "Original Org A description"},
        headers=auth_org_a["headers"],
    )
    assert create_resp.status_code == 201
    project_a_id = create_resp.json()["id"]

    # Org B attempts to update Org A's project -> MUST BE 404
    update_b = await client.put(
        f"/api/v1/projects/{project_a_id}",
        json={"name": "Hacked Retreat", "description": "Attacked by Org B"},
        headers=auth_org_b["headers"],
    )
    assert update_b.status_code == 404
    assert update_b.json()["code"] == "NOT_FOUND"

    # Verify project was not modified
    verify_resp = await client.get(
        f"/api/v1/projects/{project_a_id}",
        headers=auth_org_a["headers"],
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["name"] == "Mountain Retreat"


@pytest.mark.asyncio
async def test_tenancy_isolation_delete(client: AsyncClient, auth_org_a: dict, auth_org_b: dict):
    """User from Org B cannot delete Org A's project (returns 404, not 403)."""
    # Org A creates a project
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Lakeside Cabin", "description": "Org A Cabin"},
        headers=auth_org_a["headers"],
    )
    assert create_resp.status_code == 201
    project_a_id = create_resp.json()["id"]

    # Org B attempts to delete Org A's project -> MUST BE 404
    delete_b = await client.delete(
        f"/api/v1/projects/{project_a_id}",
        headers=auth_org_b["headers"],
    )
    assert delete_b.status_code == 404
    assert delete_b.json()["code"] == "NOT_FOUND"

    # Verify project still exists for Org A
    verify_resp = await client.get(
        f"/api/v1/projects/{project_a_id}",
        headers=auth_org_a["headers"],
    )
    assert verify_resp.status_code == 200


@pytest.mark.asyncio
async def test_tenancy_isolation_list(client: AsyncClient, auth_org_a: dict, auth_org_b: dict):
    """Listing projects returns ONLY projects belonging to the requesting user's organization."""
    # Org A creates project
    await client.post(
        "/api/v1/projects",
        json={"name": "Org A Project 1", "description": "Desc A"},
        headers=auth_org_a["headers"],
    )

    # Org B creates project
    await client.post(
        "/api/v1/projects",
        json={"name": "Org B Project 1", "description": "Desc B"},
        headers=auth_org_b["headers"],
    )

    # List Org A projects
    list_a = await client.get("/api/v1/projects", headers=auth_org_a["headers"])
    assert list_a.status_code == 200
    items_a = list_a.json()["items"]
    assert len(items_a) >= 1
    assert all(p["org_id"] == auth_org_a["org"]["id"] for p in items_a)
    assert not any(p["name"] == "Org B Project 1" for p in items_a)

    # List Org B projects
    list_b = await client.get("/api/v1/projects", headers=auth_org_b["headers"])
    assert list_b.status_code == 200
    items_b = list_b.json()["items"]
    assert len(items_b) >= 1
    assert all(p["org_id"] == auth_org_b["org"]["id"] for p in items_b)
    assert not any(p["name"] == "Org A Project 1" for p in items_b)
