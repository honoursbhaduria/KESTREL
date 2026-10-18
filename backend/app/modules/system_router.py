"""Health, readiness, and metrics endpoints."""

import redis.asyncio as aioredis
from fastapi import APIRouter, Response, status
from sqlalchemy import text

import app.db.session as db_session_module
from app.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """Liveness probe: verifies the application process is running."""
    return {"status": "ok"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(response: Response) -> dict[str, str]:
    """Readiness probe: verifies database and cache connectivity."""
    db_status = "disconnected"
    redis_status = "disconnected"
    settings = get_settings()

    # 1. Check PostgreSQL using current session factory
    try:
        async with db_session_module.async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        db_status = "failed"

    # 2. Check Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()  # type: ignore[attr-defined]
        redis_status = "connected"
    except Exception:
        redis_status = "failed"

    is_ready = db_status == "connected" and redis_status == "connected"
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "degraded",
        "database": db_status,
        "redis": redis_status,
    }
