"""API router for project, plot, ruleset, and envelope management."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import AuthContext, get_current_auth_context
from app.modules.planning.envelope import Envelope
from app.modules.projects.schemas import (
    BriefProgramResponse,
    GeneratedOptionItem,
    GeneratedOptionsResponse,
    GenerateLayoutRequest,
    PlotResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    SetBriefRequest,
    SetPlotRequest,
    SetProgramRequest,
)
from app.modules.projects.service import ProjectService
from app.modules.rules.schemas import SetProjectRulesetRequest

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    service = ProjectService(session)
    project = await service.create_project(auth.org.id, data)
    return ProjectResponse.model_validate(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectListResponse:
    service = ProjectService(session)
    items, total = await service.list_projects(auth.org.id, skip=skip, limit=limit)
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in items],
        total=total,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    service = ProjectService(session)
    project = await service.get_project(project_id, auth.org.id)
    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    service = ProjectService(session)
    project = await service.update_project(project_id, auth.org.id, data)
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    service = ProjectService(session)
    await service.delete_project(project_id, auth.org.id)


# -------------------------------------------------------------
# Plot Endpoints
# -------------------------------------------------------------
@router.put("/{project_id}/plot", response_model=PlotResponse)
async def set_plot(
    project_id: uuid.UUID,
    data: SetPlotRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> PlotResponse:
    service = ProjectService(session)
    plot = await service.set_plot(project_id, auth.org.id, data)
    return PlotResponse(
        id=plot.id,
        project_id=plot.project_id,
        boundary=plot.boundary_coords,
        original_geo_boundary=plot.original_geo_boundary,
        north_angle_deg=plot.north_angle_deg,
        road_sides=plot.road_sides,
        plot_area_mm2=plot.plot_area_mm2,
        created_at=plot.created_at,
        updated_at=plot.updated_at,
    )


@router.get("/{project_id}/plot", response_model=PlotResponse)
async def get_plot(
    project_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> PlotResponse:
    service = ProjectService(session)
    plot = await service.get_plot(project_id, auth.org.id)
    return PlotResponse(
        id=plot.id,
        project_id=plot.project_id,
        boundary=plot.boundary_coords,
        original_geo_boundary=plot.original_geo_boundary,
        north_angle_deg=plot.north_angle_deg,
        road_sides=plot.road_sides,
        plot_area_mm2=plot.plot_area_mm2,
        created_at=plot.created_at,
        updated_at=plot.updated_at,
    )


# -------------------------------------------------------------
# Ruleset & Envelope Endpoints
# -------------------------------------------------------------
@router.put("/{project_id}/ruleset", response_model=ProjectResponse)
async def set_project_ruleset(
    project_id: uuid.UUID,
    data: SetProjectRulesetRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    service = ProjectService(session)
    project = await service.set_ruleset(project_id, auth.org.id, data.ruleset_id)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}/envelope", response_model=Envelope)
async def get_project_envelope(
    project_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> Envelope:
    service = ProjectService(session)
    return await service.get_envelope(project_id, auth.org.id)


# -------------------------------------------------------------
# Brief & Program Endpoints (Phase 4)
# -------------------------------------------------------------
@router.put("/{project_id}/brief", response_model=BriefProgramResponse)
async def set_project_brief(
    project_id: uuid.UUID,
    data: SetBriefRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> BriefProgramResponse:
    service = ProjectService(session)
    result = await service.set_brief(project_id, auth.org.id, data.brief_text)
    return BriefProgramResponse(**result)


@router.get("/{project_id}/program", response_model=BriefProgramResponse)
async def get_project_program(
    project_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> BriefProgramResponse:
    service = ProjectService(session)
    result = await service.get_program(project_id, auth.org.id)
    return BriefProgramResponse(**result)


@router.put("/{project_id}/program", response_model=BriefProgramResponse)
async def set_project_program(
    project_id: uuid.UUID,
    data: SetProgramRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> BriefProgramResponse:
    service = ProjectService(session)
    result = await service.set_program(project_id, auth.org.id, data.program)
    return BriefProgramResponse(**result)


# -------------------------------------------------------------
# Generative Options Endpoints (Phase 4)
# -------------------------------------------------------------
@router.post("/{project_id}/generate")
async def generate_project_plans(
    project_id: uuid.UUID,
    data: GenerateLayoutRequest,
    response: Response,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ProjectService(session)
    job, is_new = await service.enqueue_generation_job(
        project_id=project_id,
        org_id=auth.org.id,
        num_options=data.num_options,
        seed=data.seed,
        idempotency_key=idempotency_key,
    )
    response.status_code = status.HTTP_202_ACCEPTED if is_new else status.HTTP_200_OK
    return {
        "job_id": str(job.id),
        "status": job.status.value,
    }


@router.get("/{project_id}/generated-options", response_model=GeneratedOptionsResponse)
async def list_project_generated_options(
    project_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> GeneratedOptionsResponse:
    service = ProjectService(session)
    options = await service.list_generated_options(project_id, auth.org.id)
    return GeneratedOptionsResponse(
        options=[GeneratedOptionItem.model_validate(o) for o in options]
    )


