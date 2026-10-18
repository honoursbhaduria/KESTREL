"""Tests for system health, readiness, and metrics endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_health(client: AsyncClient):
    """Liveness probe /health returns 200 OK."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness_ready(client: AsyncClient):
    """Readiness probe /ready verifies PostgreSQL and Redis connections."""
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert data["redis"] == "connected"


@pytest.mark.asyncio
async def test_metrics_prometheus(client: AsyncClient):
    """Metrics endpoint /metrics exposes standard Prometheus text format."""
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text or "process_cpu_seconds_total" in response.text
