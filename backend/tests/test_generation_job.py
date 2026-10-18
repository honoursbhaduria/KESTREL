"""Tests for asynchronous layout generation job and statutory verification of generated options."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import Job, JobStatus
from app.modules.plans.models import Plan
from app.workers.tasks import process_plan_generation_job


@pytest.fixture
async def setup_project_for_generation(client: AsyncClient, auth_org_a: dict) -> dict:
    headers = auth_org_a["headers"]
    # 1. Create project
    p_resp = await client.post("/api/v1/projects", json={"name": "Sunset Residence"}, headers=headers)
    assert p_resp.status_code == 201
    proj_id = p_resp.json()["id"]

    # 2. Assign ruleset
    await client.put(f"/api/v1/projects/{proj_id}/ruleset", json={"ruleset_id": "up-bylaws"}, headers=headers)

    # 3. Assign plot (12m x 18m)
    plot_coords = [[0.0, 0.0], [12000.0, 0.0], [12000.0, 18000.0], [0.0, 18000.0]]
    await client.put(
        f"/api/v1/projects/{proj_id}/plot",
        json={"boundary_coords": plot_coords, "road_sides": [{"edge_index": 0, "road_width_m": 12.0}], "north_angle_deg": 0.0},
        headers=headers,
    )

    # 4. Set brief
    brief_text = "2BHK house with living room, open kitchen, 2 bedrooms, 2 bathrooms. East entrance, vastu preferred."
    await client.put(f"/api/v1/projects/{proj_id}/brief", json={"brief_text": brief_text}, headers=headers)

    return {"project_id": proj_id, "headers": headers}


@pytest.mark.asyncio
async def test_post_generate_job_idempotency(client: AsyncClient, setup_project_for_generation: dict):
    """Verify POST /projects/{id}/generate creates a job and honors Idempotency-Key."""
    proj_id = setup_project_for_generation["project_id"]
    headers = setup_project_for_generation["headers"]
    idemp_key = f"gen-key-{uuid.uuid4()}"

    # 1. First request
    resp1 = await client.post(
        f"/api/v1/projects/{proj_id}/generate",
        json={"num_options": 3, "seed": 42},
        headers={**headers, "Idempotency-Key": idemp_key},
    )
    assert resp1.status_code == 202
    data1 = resp1.json()
    assert "job_id" in data1
    assert data1["status"] in ["queued", "running"]

    # 2. Second request with same idempotency key
    resp2 = await client.post(
        f"/api/v1/projects/{proj_id}/generate",
        json={"num_options": 3, "seed": 42},
        headers={**headers, "Idempotency-Key": idemp_key},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["job_id"] == data1["job_id"]


@pytest.mark.asyncio
async def test_generation_pipeline_end_to_end(
    client: AsyncClient, setup_project_for_generation: dict
):
    """Verify execution of generation task produces valid, scored Plans with no hard fails."""
    proj_id = setup_project_for_generation["project_id"]
    headers = setup_project_for_generation["headers"]

    # Request generation
    resp = await client.post(
        f"/api/v1/projects/{proj_id}/generate",
        json={"num_options": 3, "seed": 100},
        headers=headers,
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    # Execute generation worker task directly
    task_res = await process_plan_generation_job(
        ctx={},
        job_id=job_id,
        project_id=proj_id,
        num_options=3,
        seed=100,
    )
    assert task_res.get("status") == "success"

    # Verify job is DONE via API
    job_resp = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert job_resp.status_code == 200
    job_data = job_resp.json()
    assert job_data["status"] == "done"
    assert job_data["progress"] == 100

    # Query generated options endpoint
    opts_resp = await client.get(f"/api/v1/projects/{proj_id}/generated-options", headers=headers)
    assert opts_resp.status_code == 200
    options = opts_resp.json()["options"]
    assert len(options) >= 2

    # Check each option has score breakdown, description, and review with 0 hard fails
    for opt in options:
        assert opt["created_by"] == "solver"
        assert opt["score_breakdown"] is not None
        assert opt["score_breakdown"]["total_score"] > 0
        assert opt["description"] != ""
        # Check review results: no hard fails
        assert opt["review_summary"]["fails"] == 0
