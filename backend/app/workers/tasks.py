"""arq worker tasks and settings."""

import asyncio
import uuid
from typing import Any

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.modules.jobs.models import JobStatus
from app.modules.jobs.repository import JobRepository

logger = get_logger(__name__)


async def process_dummy_job(
    ctx: dict[str, Any], job_id: str | uuid.UUID, steps: int = 3
) -> dict[str, Any]:
    """Execute dummy pipeline: transitions job from queued -> running -> done."""
    uid = uuid.UUID(str(job_id))
    logger.info("process_dummy_job_started", job_id=str(uid))

    async with async_session_factory() as session:
        repo = JobRepository(session)
        job = await repo.get_by_id(uid)
        if not job:
            logger.error("job_not_found", job_id=str(uid))
            return {"error": "Job not found"}

        # Move to running
        await repo.update_status(job, JobStatus.RUNNING, progress=10)
        await session.commit()

    # Emulate work steps
    for step in range(1, steps + 1):
        await asyncio.sleep(0.05)
        progress = int((step / (steps + 1)) * 90)
        async with async_session_factory() as session:
            repo = JobRepository(session)
            job = await repo.get_by_id(uid)
            if job:
                await repo.update_status(job, JobStatus.RUNNING, progress=progress)
                await session.commit()

    # Move to done
    result_data = {
        "status": "success",
        "message": "Dummy job pipeline verified end to end",
        "steps_completed": steps,
    }
    async with async_session_factory() as session:
        repo = JobRepository(session)
        job = await repo.get_by_id(uid)
        if job:
            await repo.update_status(job, JobStatus.DONE, progress=100, result=result_data)
            await session.commit()

    logger.info("process_dummy_job_completed", job_id=str(uid))
    return result_data


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("arq_worker_startup")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("arq_worker_shutdown")


settings = get_settings()


class WorkerSettings:
    functions = [process_dummy_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300
