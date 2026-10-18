"""API router for Plans, Patches, Diff, Undo/Redo, and Statutory Reviews (Phase 3)."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import AuthContext, get_current_auth_context
from app.modules.plans.patches import PlanDiff
from app.modules.plans.schemas import (
    ApplyPatchesRequest,
    PlanCreate,
    PlanResponse,
    PlanVersionResponse,
    ReviewPlanRequest,
)
from app.modules.plans.service import PlanService
from app.modules.rules.engine import ReviewResult

router = APIRouter(tags=["plans"])


@router.post(
    "/projects/{project_id}/plans",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_plan(
    project_id: uuid.UUID,
    data: PlanCreate,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> PlanResponse:
    """Create a new architectural plan for a project and commit initial version."""
    service = PlanService(session)
    return await service.create_plan(auth.org.id, project_id, data)


@router.get("/plans/{id}", response_model=PlanResponse)
async def get_plan(
    id: uuid.UUID,
    version: int | None = Query(default=None, description="Optional specific version number"),
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> PlanResponse:
    """Retrieve plan by ID, returning current or requested historical version."""
    service = PlanService(session)
    return await service.get_plan(id, auth.org.id, version=version)


@router.post("/plans/{id}/patches", response_model=PlanResponse)
async def apply_patches(
    id: uuid.UUID,
    data: ApplyPatchesRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> PlanResponse:
    """Apply a batch of typed patches atomically, creating a new immutable version."""
    service = PlanService(session)
    return await service.apply_patches(id, auth.org.id, data)


@router.post("/plans/{id}/undo", response_model=PlanResponse)
async def undo_plan_version(
    id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> PlanResponse:
    """Revert current plan pointer to previous version."""
    service = PlanService(session)
    return await service.undo(id, auth.org.id)


@router.post("/plans/{id}/redo", response_model=PlanResponse)
async def redo_plan_version(
    id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> PlanResponse:
    """Advance current plan pointer to next version."""
    service = PlanService(session)
    return await service.redo(id, auth.org.id)


@router.get("/plans/{id}/versions", response_model=list[PlanVersionResponse])
async def list_plan_versions(
    id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[PlanVersionResponse]:
    """List all version history records for a plan."""
    service = PlanService(session)
    return await service.list_versions(id, auth.org.id)


@router.get("/plans/{id}/diff", response_model=PlanDiff)
async def get_plan_diff(
    id: uuid.UUID,
    from_version: int = Query(..., description="Base version"),
    to_version: int = Query(..., description="Target version"),
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> PlanDiff:
    """Compute structured semantic delta between two plan versions."""
    service = PlanService(session)
    return await service.get_diff(id, auth.org.id, from_version, to_version)


@router.post("/plans/{id}/review", response_model=ReviewResult)
async def review_plan(
    id: uuid.UUID,
    data: ReviewPlanRequest | None = None,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> ReviewResult:
    """Execute statutory code compliance review on plan against project ruleset and envelope."""
    service = PlanService(session)
    ruleset_id = data.ruleset_id if data else None
    return await service.review_plan(id, auth.org.id, ruleset_id=ruleset_id)
