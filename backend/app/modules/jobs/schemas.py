"""Pydantic schemas for background jobs."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.modules.jobs.models import JobStatus


class JobCreateRequest(BaseModel):
    type: str = "dummy"
    idempotency_key: str | None = None
    params: dict[str, Any] | None = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    type: str
    status: JobStatus
    progress: int
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    idempotency_key: str | None = None
    created_at: datetime
    updated_at: datetime
