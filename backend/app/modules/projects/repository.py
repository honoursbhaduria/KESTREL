"""Repository for projects and plots with strict organization isolation."""

import uuid
from typing import Any

from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.projects.models import Plot, Project


class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, project_id: uuid.UUID, org_id: uuid.UUID) -> Project | None:
        """Fetch project scoped strictly by org_id."""
        stmt = (
            select(Project)
            .options(selectinload(Project.plot))
            .where(
                Project.id == project_id,
                Project.org_id == org_id,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_org(
        self, org_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[Project], int]:
        """List all projects belonging to the given organization."""
        count_stmt = select(func.count()).select_from(Project).where(Project.org_id == org_id)
        total = await self.session.scalar(count_stmt) or 0

        stmt = (
            select(Project)
            .where(Project.org_id == org_id)
            .order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        items = list(res.scalars().all())
        return items, total

    async def create(self, org_id: uuid.UUID, name: str, description: str | None) -> Project:
        project = Project(
            org_id=org_id,
            name=name.strip(),
            description=description.strip() if description else None,
            status="active",
        )
        self.session.add(project)
        await self.session.flush()
        return project

    async def update(
        self,
        project: Project,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        ruleset_id: str | None = None,
    ) -> Project:
        if name is not None:
            project.name = name.strip()
        if description is not None:
            project.description = description.strip() if description else None
        if status is not None:
            project.status = status.strip()
        if ruleset_id is not None:
            project.ruleset_id = ruleset_id.strip()
        await self.session.flush()
        return project

    async def delete(self, project: Project) -> None:
        await self.session.delete(project)
        await self.session.flush()

    # -------------------------------------------------------------
    # Plot Methods
    # -------------------------------------------------------------
    async def get_plot(self, project_id: uuid.UUID) -> Plot | None:
        stmt = select(Plot).where(Plot.project_id == project_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def upsert_plot(
        self,
        project_id: uuid.UUID,
        boundary_coords: list[list[float]],
        original_geo_boundary: list[list[float]] | None,
        north_angle_deg: float,
        road_sides: list[dict[str, Any]],
        plot_area_mm2: float,
    ) -> Plot:
        plot = await self.get_plot(project_id)
        # Convert shapely polygon to WKB element for PostGIS geometry column
        poly_geom = Polygon(boundary_coords)
        wkb_geom = from_shape(poly_geom, srid=0)

        if plot:
            plot.boundary = wkb_geom
            plot.boundary_coords = boundary_coords
            plot.original_geo_boundary = original_geo_boundary
            plot.north_angle_deg = north_angle_deg
            plot.road_sides = road_sides
            plot.plot_area_mm2 = plot_area_mm2
        else:
            plot = Plot(
                project_id=project_id,
                boundary=wkb_geom,
                boundary_coords=boundary_coords,
                original_geo_boundary=original_geo_boundary,
                north_angle_deg=north_angle_deg,
                road_sides=road_sides,
                plot_area_mm2=plot_area_mm2,
            )
            self.session.add(plot)

        await self.session.flush()
        return plot
