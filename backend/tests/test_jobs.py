"""Tests for background jobs, idempotency keys, and SSE event streaming."""

import asyncio

import pytest
from httpx import AsyncClient

from app.db.session import async_session_factory
from app.modules.jobs.repository import JobRepository
from app.workers.tasks import process_dummy_job


@pytest.mark.asyncio
async def test_create_and_get_job(client: AsyncClient, auth_org_a: dict):
    """Enqueuing a job with idempotency key creates a job record in 'queued' status."""
    payload = {
        "type": "dummy",
        "idempotency_key": "job-test-idem-key-001",
        "params": {"duration_steps": 2},
    }
    resp = await client.post(
        "/api/v1/jobs",
        json=payload,
        headers=auth_org_a["headers"],
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["type"] == "dummy"
    assert data["status"] == "queued"
    assert data["progress"] == 0
    assert data["idempotency_key"] == payload["idempotency_key"]
    job_id = data["id"]

    # Fetch job status
    get_resp = await client.get(f"/api/v1/jobs/{job_id}", headers=auth_org_a["headers"])
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == job_id


@pytest.mark.asyncio
async def test_job_idempotency_duplicate_returns_same_job(client: AsyncClient, auth_org_a: dict):
    """Submitting the same idempotency key returns the existing job without creating duplicates."""
    payload = {
        "type": "dummy",
        "idempotency_key": "job-idem-duplicate-check-002",
        "params": {"test": 123},
    }
    resp1 = await client.post("/api/v1/jobs", json=payload, headers=auth_org_a["headers"])
    assert resp1.status_code == 202
    job1_id = resp1.json()["id"]

    resp2 = await client.post("/api/v1/jobs", json=payload, headers=auth_org_a["headers"])
    assert resp2.status_code == 200  # Existing job returned
    assert resp2.json()["id"] == job1_id


@pytest.mark.asyncio
async def test_dummy_job_worker_execution(client: AsyncClient, auth_org_a: dict):
    """Executing the dummy task moves job queued -> running -> done with progress updates."""
    # Create job
    create_resp = await client.post(
        "/api/v1/jobs",
        json={"type": "dummy", "params": {"steps": 3}},
        headers=auth_org_a["headers"],
    )
    assert create_resp.status_code == 202
    job_id = create_resp.json()["id"]

    # Execute dummy worker task directly
    async with async_session_factory() as session:
        job_repo = JobRepository(session)
        # Verify initial status
        job = await job_repo.get_by_id(job_id)
        assert job is not None
        assert job.status == "queued"

    # Run the worker task
    worker_ctx = {"redis": None}
    await process_dummy_job(worker_ctx, job_id, steps=2)

    # Check that job has completed
    get_resp = await client.get(f"/api/v1/jobs/{job_id}", headers=auth_org_a["headers"])
    assert get_resp.status_code == 200
    finished_job = get_resp.json()
    assert finished_job["status"] == "done"
    assert finished_job["progress"] == 100
    assert finished_job["result"] is not None
    assert finished_job["result"]["status"] == "success"


@pytest.mark.asyncio
async def test_job_sse_events(client: AsyncClient, auth_org_a: dict):
    """Subscribing to /jobs/{id}/events returns text/event-stream content."""
    create_resp = await client.post(
        "/api/v1/jobs",
        json={"type": "dummy", "params": {"steps": 1}},
        headers=auth_org_a["headers"],
    )
    assert create_resp.status_code == 202
    job_id = create_resp.json()["id"]

    # In background, complete the job shortly
    async def finish_job_delayed():
        await asyncio.sleep(0.1)
        await process_dummy_job({}, job_id, steps=1)

    bg_task = asyncio.create_task(finish_job_delayed())

    # Stream events
    async with client.stream(
        "GET",
        f"/api/v1/jobs/{job_id}/events",
        headers=auth_org_a["headers"],
    ) as stream_resp:
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers["content-type"]
        received_data = []
        async for line in stream_resp.aiter_lines():
            if line.startswith("data:"):
                received_data.append(line)
            if len(received_data) >= 1:
                break
        assert len(received_data) >= 1

    await bg_task
