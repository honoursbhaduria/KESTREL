"""Business logic service for projects, plots, rulesets, and envelopes."""

import uuid
from typing import Any

from shapely.geometry import Polygon
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMClient, load_prompt_template
from app.core.errors import BadRequestError, NotFoundError
from app.modules.planning.envelope import Envelope, compute_envelope
from app.modules.planning.program import Program, validate_program_feasibility
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

    # -------------------------------------------------------------
    # Brief & Program Methods (Phase 4)
    # -------------------------------------------------------------
    async def set_brief(
        self, project_id: uuid.UUID, org_id: uuid.UUID, brief_text: str
    ) -> dict[str, Any]:
        project = await self.get_project(project_id, org_id)
        envelope = await self.get_envelope(project_id, org_id)
        ruleset = get_ruleset(project.ruleset_id) if project.ruleset_id else None

        template = load_prompt_template("structure_brief.v1.txt")
        prompt = template.replace("{brief_text}", brief_text)

        client = LLMClient()
        program, usage = await client.generate_structured(
            prompt=prompt,
            response_model=Program,
            kind="structure_brief",
            org_id=org_id,
            session=self.session,
        )

        feasibility = validate_program_feasibility(program, envelope, ruleset)

        project.brief_text = brief_text
        project.program_data = program.model_dump()
        await self.session.commit()
        await self.session.refresh(project)

        return {
            "brief_text": brief_text,
            "program": program,
            "feasibility": feasibility,
        }

    async def get_program(
        self, project_id: uuid.UUID, org_id: uuid.UUID
    ) -> dict[str, Any]:
        project = await self.get_project(project_id, org_id)
        envelope = await self.get_envelope(project_id, org_id)
        ruleset = get_ruleset(project.ruleset_id) if project.ruleset_id else None

        if project.program_data:
            program = Program.model_validate(project.program_data)
        else:
            program = Program(levels=1, rooms=[])

        feasibility = validate_program_feasibility(program, envelope, ruleset)
        return {
            "brief_text": project.brief_text,
            "program": program,
            "feasibility": feasibility,
        }

    async def set_program(
        self, project_id: uuid.UUID, org_id: uuid.UUID, program_input: Program | dict[str, Any]
    ) -> dict[str, Any]:
        project = await self.get_project(project_id, org_id)
        envelope = await self.get_envelope(project_id, org_id)
        ruleset = get_ruleset(project.ruleset_id) if project.ruleset_id else None

        program = (
            program_input
            if isinstance(program_input, Program)
            else Program.model_validate(program_input)
        )
        feasibility = validate_program_feasibility(program, envelope, ruleset)

        project.program_data = program.model_dump()
        await self.session.commit()
        await self.session.refresh(project)

        return {
            "brief_text": project.brief_text,
            "program": program,
            "feasibility": feasibility,
        }

    # -------------------------------------------------------------
    # Generative Layout Jobs (Phase 4)
    # -------------------------------------------------------------
    async def enqueue_generation_job(
        self,
        project_id: uuid.UUID,
        org_id: uuid.UUID,
        num_options: int,
        seed: int,
        idempotency_key: str | None = None,
    ) -> tuple[Any, bool]:
        """Enqueue plan generation job. Returns (Job, is_new)."""
        project = await self.get_project(project_id, org_id)

        import asyncio

        from arq import create_pool
        from arq.connections import RedisSettings

        from app.core.config import get_settings
        from app.core.logging import get_logger
        from app.modules.jobs.repository import JobRepository
        from app.workers.tasks import process_plan_generation_job

        settings = get_settings()
        logger = get_logger(__name__)
        job_repo = JobRepository(self.session)

        if idempotency_key:
            existing = await job_repo.get_by_idempotency_key(idempotency_key, org_id)
            if existing:
                return existing, False

        job = await job_repo.create(
            org_id=org_id,
            job_type="plan_generation",
            idempotency_key=idempotency_key,
        )
        await self.session.commit()

        # Enqueue in arq if redis available
        try:
            redis_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
            await redis_pool.enqueue_job(
                "process_plan_generation_job",
                str(job.id),
                str(project.id),
                num_options,
                seed,
            )
            await redis_pool.aclose()  # type: ignore[attr-defined]
        except Exception as e:
            logger.warning("redis_plan_gen_enqueue_failed", error=str(e), job_id=str(job.id))

        # Also trigger an in-process background task for immediate local and test execution
        asyncio.create_task(
            process_plan_generation_job({}, str(job.id), str(project.id), num_options, seed)
        )

        return job, True

    async def list_generated_options(
        self, project_id: uuid.UUID, org_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        project = await self.get_project(project_id, org_id)

        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.modules.plans.models import Plan

        query = (
            select(Plan)
            .options(selectinload(Plan.versions), selectinload(Plan.reviews))
            .where(Plan.project_id == project.id, Plan.created_by == "solver")
            .order_by(Plan.created_at.desc())
        )
        plans = (await self.session.execute(query)).scalars().all()

        results = []
        for p in plans:
            latest_v = p.versions[-1] if p.versions else None
            latest_rev = p.reviews[-1] if p.reviews else None

            rev_summary = {
                "passes": latest_rev.summary.get("pass_count", 0) if latest_rev else 0,
                "reviews": latest_rev.summary.get("review_count", 0) if latest_rev else 0,
                "fails": latest_rev.summary.get("fail_count", 0) if latest_rev else 0,
            }

            results.append({
                "id": str(p.id),
                "project_id": str(p.project_id),
                "name": p.name,
                "created_by": p.created_by,
                "score_breakdown": p.score_breakdown,
                "description": p.description or "",
                "review_summary": rev_summary,
                "data": latest_v.data if latest_v else None,
                "created_at": p.created_at,
            })
        return results
