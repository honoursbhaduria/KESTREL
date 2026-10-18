"""API router for project, plot, ruleset, and envelope management."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import AuthContext, get_current_auth_context
from app.modules.planning.envelope import Envelope
from app.modules.projects.schemas import (
    PlotResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    SetPlotRequest,
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
