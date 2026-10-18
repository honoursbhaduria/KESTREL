"""Business logic service for projects, plots, rulesets, and envelopes."""

import uuid
from typing import Any

from shapely.geometry import Polygon
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.modules.planning.envelope import Envelope, compute_envelope
from app.modules.projects.models import Plot, Project
from app.modules.projects.repository import ProjectRepository
from app.modules.projects.schemas import ProjectCreate, ProjectUpdate, SetPlotRequest
from app.modules.rules.loader import get_ruleset


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ProjectRepository(session)

    async def create_project(self, org_id: uuid.UUID, data: ProjectCreate) -> Project:
        project = await self.repo.create(
            org_id=org_id,
            name=data.name,
            description=data.description,
        )
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def get_project(self, project_id: uuid.UUID, org_id: uuid.UUID) -> Project:
        project = await self.repo.get_by_id(project_id, org_id)
        if not project:
            raise NotFoundError("Project not found")
        return project

    async def list_projects(
        self, org_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[Project], int]:
        return await self.repo.list_by_org(org_id, skip=skip, limit=limit)

    async def update_project(
        self, project_id: uuid.UUID, org_id: uuid.UUID, data: ProjectUpdate
    ) -> Project:
        project = await self.get_project(project_id, org_id)
        updated = await self.repo.update(
            project,
            name=data.name,
            description=data.description,
            status=data.status,
            ruleset_id=data.ruleset_id,
        )
        await self.session.commit()
        await self.session.refresh(updated)
        return updated

    async def delete_project(self, project_id: uuid.UUID, org_id: uuid.UUID) -> None:
        project = await self.get_project(project_id, org_id)
        await self.repo.delete(project)
        await self.session.commit()

    # -------------------------------------------------------------
    # Plot Methods
    # -------------------------------------------------------------
    async def set_plot(
        self, project_id: uuid.UUID, org_id: uuid.UUID, data: SetPlotRequest
    ) -> Plot:
        project = await self.get_project(project_id, org_id)
        assert data.boundary is not None

        poly = Polygon(data.boundary)
        plot_area_mm2 = float(poly.area)

        road_sides_dict = [rs.model_dump() for rs in data.road_sides]

        plot = await self.repo.upsert_plot(
            project_id=project.id,
            boundary_coords=data.boundary,
            original_geo_boundary=data.original_geo_boundary,
            north_angle_deg=data.north_angle_deg,
            road_sides=road_sides_dict,
            plot_area_mm2=plot_area_mm2,
        )
        await self.session.commit()
        await self.session.refresh(plot)
        return plot

    async def get_plot(self, project_id: uuid.UUID, org_id: uuid.UUID) -> Plot:
        # Verify tenant ownership
        await self.get_project(project_id, org_id)
        plot = await self.repo.get_plot(project_id)
        if not plot:
            raise NotFoundError("Plot not defined for this project")
        return plot

    # -------------------------------------------------------------
    # Ruleset Linkage & Envelope
    # -------------------------------------------------------------
    async def set_ruleset(
        self, project_id: uuid.UUID, org_id: uuid.UUID, ruleset_id: str
    ) -> Project:
        project = await self.get_project(project_id, org_id)
        ruleset = get_ruleset(ruleset_id)
        if not ruleset:
            raise NotFoundError(f"Ruleset '{ruleset_id}' not found")

        updated = await self.repo.update(project, ruleset_id=ruleset_id)
        await self.session.commit()
        await self.session.refresh(updated)
        return updated

    async def get_envelope(self, project_id: uuid.UUID, org_id: uuid.UUID) -> Envelope:
        project = await self.get_project(project_id, org_id)
        plot = await self.repo.get_plot(project_id)
        if not plot:
            raise BadRequestError("Plot must be defined before computing buildable envelope")

        ruleset_id = project.ruleset_id or "up-bylaws"
        ruleset = get_ruleset(ruleset_id)

        ruleset_params: dict[str, Any] = {"ruleset_id": ruleset_id}
        if ruleset:
            for rule in ruleset.rules:
                if rule.category in ("setback", "coverage", "far", "height"):
                    ruleset_params.update(rule.params)

        envelope = compute_envelope(
            plot_polygon=plot.boundary_coords,
            road_sides=plot.road_sides,
            ruleset_params=ruleset_params,
        )
        return envelope
