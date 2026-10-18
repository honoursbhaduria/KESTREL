"""Database repository for asynchronous jobs."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import Job, JobStatus


class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, job_id: uuid.UUID, org_id: uuid.UUID | None = None) -> Job | None:
        stmt = select(Job).where(Job.id == job_id)
        if org_id is not None:
            stmt = stmt.where(Job.org_id == org_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_idempotency_key(self, idempotency_key: str, org_id: uuid.UUID) -> Job | None:
        stmt = select(Job).where(
            Job.idempotency_key == idempotency_key,
            Job.org_id == org_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create(
        self,
        org_id: uuid.UUID,
        job_type: str,
        idempotency_key: str | None = None,
    ) -> Job:
        job = Job(
            org_id=org_id,
            type=job_type,
            status=JobStatus.QUEUED,
            progress=0,
            idempotency_key=idempotency_key,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def update_status(
        self,
        job: Job,
        status: JobStatus,
        progress: int | None = None,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> Job:
        job.status = status
        if progress is not None:
            job.progress = progress
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error
        await self.session.flush()
        return job
