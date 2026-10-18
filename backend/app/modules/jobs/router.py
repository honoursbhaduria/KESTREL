"""API router for job creation, status querying, and SSE event streaming."""

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

import app.db.session as db_session_module
from app.db.session import get_db_session
from app.modules.auth.dependencies import AuthContext, get_current_auth_context
from app.modules.jobs.models import JobStatus
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.schemas import JobCreateRequest, JobResponse
from app.modules.jobs.service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse)
async def create_job(
    req: JobCreateRequest,
    response: Response,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> JobResponse:
    service = JobService(session)
    job, is_new = await service.enqueue_job(auth.org.id, req)
    response.status_code = status.HTTP_202_ACCEPTED if is_new else status.HTTP_200_OK
    return JobResponse.model_validate(job)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> JobResponse:
    service = JobService(session)
    job = await service.get_job(job_id, auth.org.id)
    return JobResponse.model_validate(job)


@router.get("/{job_id}/events")
async def stream_job_events(
    job_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> EventSourceResponse:
    service = JobService(session)
    # Validate access
    await service.get_job(job_id, auth.org.id)

    async def event_generator():
        last_progress = -1
        last_status = None

        while True:
            async with db_session_module.async_session_factory() as poll_session:
                repo = JobRepository(poll_session)
                job = await repo.get_by_id(job_id, auth.org.id)
                if not job:
                    break

                if job.progress != last_progress or job.status != last_status:
                    last_progress = job.progress
                    last_status = job.status

                    data = {
                        "job_id": str(job.id),
                        "status": job.status.value,
                        "progress": job.progress,
                        "result": job.result,
                        "error": job.error,
                    }
                    yield {
                        "event": "job_update",
                        "data": json.dumps(data),
                    }

                if job.status in [JobStatus.DONE, JobStatus.FAILED]:
                    break

            await asyncio.sleep(0.1)

    return EventSourceResponse(event_generator())
