"""Business logic service for job creation and tracking."""

import uuid

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.modules.jobs.models import Job
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.schemas import JobCreateRequest

logger = get_logger(__name__)


class JobService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = JobRepository(session)
        self.settings = get_settings()

    async def enqueue_job(self, org_id: uuid.UUID, req: JobCreateRequest) -> tuple[Job, bool]:
        """Enqueue job. Returns (Job, is_new). If idempotent key matched, is_new=False."""
        if req.idempotency_key:
            existing = await self.repo.get_by_idempotency_key(req.idempotency_key, org_id)
            if existing:
                return existing, False

        job = await self.repo.create(
            org_id=org_id,
            job_type=req.type,
            idempotency_key=req.idempotency_key,
        )
        await self.session.commit()

        # Enqueue in arq if redis is available
        try:
            redis_pool = await create_pool(RedisSettings.from_dsn(self.settings.REDIS_URL))
            await redis_pool.enqueue_job("process_dummy_job", str(job.id))
            await redis_pool.aclose()  # type: ignore[attr-defined]
        except Exception as e:
            logger.warning(
                "redis_enqueue_deferred_or_unavailable", error=str(e), job_id=str(job.id)
            )

        return job, True

    async def get_job(self, job_id: uuid.UUID, org_id: uuid.UUID) -> Job:
        job = await self.repo.get_by_id(job_id, org_id)
        if not job:
            raise NotFoundError("Job not found")
        return job
