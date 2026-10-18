"""arq worker tasks and settings."""

import asyncio
import uuid
from typing import Any

from arq.connections import RedisSettings
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.modules.jobs.models import JobStatus
from app.modules.jobs.repository import JobRepository

logger = get_logger(__name__)


async def process_dummy_job(
    ctx: dict[str, Any], job_id: str | uuid.UUID, steps: int = 3
) -> dict[str, Any]:
    """Execute dummy pipeline: transitions job from queued -> running -> done."""
    uid = uuid.UUID(str(job_id))
    logger.info("process_dummy_job_started", job_id=str(uid))

    async with async_session_factory() as session:
        repo = JobRepository(session)
        job = await repo.get_by_id(uid)
        if not job:
            logger.error("job_not_found", job_id=str(uid))
            return {"error": "Job not found"}

        # Move to running
        await repo.update_status(job, JobStatus.RUNNING, progress=10)
        await session.commit()

    # Emulate work steps
    for step in range(1, steps + 1):
        await asyncio.sleep(0.05)
        progress = int((step / (steps + 1)) * 90)
        async with async_session_factory() as session:
            repo = JobRepository(session)
            job = await repo.get_by_id(uid)
            if job:
                await repo.update_status(job, JobStatus.RUNNING, progress=progress)
                await session.commit()

    # Move to done
    result_data = {
        "status": "success",
        "message": "Dummy job pipeline verified end to end",
        "steps_completed": steps,
    }
    async with async_session_factory() as session:
        repo = JobRepository(session)
        job = await repo.get_by_id(uid)
        if job:
            await repo.update_status(job, JobStatus.DONE, progress=100, result=result_data)
            await session.commit()

    logger.info("process_dummy_job_completed", job_id=str(uid))
    return result_data


class OptionDescriptionResponse(BaseModel):
    description: str


async def process_plan_generation_job(
    ctx: dict[str, Any],
    job_id: str | uuid.UUID,
    project_id: str | uuid.UUID,
    num_options: int = 3,
    seed: int = 42,
) -> dict[str, Any]:
    """Execute generative layout synthesis pipeline: Indexing -> Zoning -> Placing -> Checking."""
    from app.ai.llm import LLMClient, load_prompt_template
    from app.modules.planning.envelope import compute_envelope
    from app.modules.planning.program import Program
    from app.modules.planning.solver import LayoutSolver
    from app.modules.plans.models import Plan, PlanReview, PlanVersion
    from app.modules.projects.models import Project
    from app.modules.rules.engine import review_plan
    from app.modules.rules.loader import get_ruleset

    j_id = uuid.UUID(str(job_id))
    p_id = uuid.UUID(str(project_id))
    logger.info("plan_generation_job_started", job_id=str(j_id), project_id=str(p_id))

    async with async_session_factory() as session:
        repo = JobRepository(session)
        job = await repo.get_by_id(j_id)
        if not job:
            return {"error": "Job not found"}

        # 1. Indexing Phase (20%)
        await repo.update_status(job, JobStatus.RUNNING, progress=20)
        await session.commit()

        # Load project, plot, ruleset, program
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        proj_q = select(Project).options(selectinload(Project.plot)).where(Project.id == p_id)
        project = (await session.execute(proj_q)).scalar_one_or_none()
        if not project or not project.plot:
            await repo.update_status(job, JobStatus.FAILED, error={"message": "Project or plot missing"})
            await session.commit()
            return {"error": "Project or plot missing"}

        ruleset_id = project.ruleset_id or "up-bylaws"
        ruleset = get_ruleset(ruleset_id)

        # Compute envelope
        ruleset_params: dict[str, Any] = {"ruleset_id": ruleset_id}
        if ruleset:
            for rule in ruleset.rules:
                if rule.category in ("setback", "coverage", "far", "height"):
                    ruleset_params.update(rule.params)

        envelope = compute_envelope(
            plot_polygon=project.plot.boundary_coords,
            road_sides=project.plot.road_sides,
            ruleset_params=ruleset_params,
        )

        # Load program
        if project.program_data:
            program = Program.model_validate(project.program_data)
        else:
            program = Program(levels=1, rooms=[])

        # 2. Zoning Phase (45%)
        await repo.update_status(job, JobStatus.RUNNING, progress=45)
        await session.commit()

        # 3. Placing Phase (75%)
        await repo.update_status(job, JobStatus.RUNNING, progress=75)
        await session.commit()

        solver = LayoutSolver()
        candidates = solver.solve(
            program=program,
            envelope=envelope,
            ruleset_id=ruleset_id,
            seed=seed,
            num_candidates=num_options,
        )

        # 4. Checking Phase & Descriptions (90%)
        await repo.update_status(job, JobStatus.RUNNING, progress=90)
        await session.commit()

        llm_client = LLMClient()
        prompt_tmpl = load_prompt_template("describe_option.v1.txt")

        created_plans: list[Plan] = []
        for i, cand in enumerate(candidates):
            scheme_label = f"Scheme {chr(65 + i)} ({cand.score_breakdown.total_score:.0f} pts)"

            # Describe option via LLM
            prompt = (
                prompt_tmpl
                .replace("{scheme_name}", scheme_label)
                .replace("{total_score}", str(cand.score_breakdown.total_score))
                .replace("{area_score}", str(cand.score_breakdown.area_score))
                .replace("{adjacency_score}", str(cand.score_breakdown.adjacency_score))
                .replace("{exterior_score}", str(cand.score_breakdown.exterior_wall_score))
                .replace("{circulation_score}", str(cand.score_breakdown.circulation_score))
                .replace("{vastu_score}", str(cand.score_breakdown.vastu_score))
                .replace("{room_summary}", ", ".join(r.name for lvl in cand.plan_data.levels for r in lvl.rooms))
            )

            try:
                desc_obj, _ = await llm_client.generate_structured(
                    prompt=prompt,
                    response_model=OptionDescriptionResponse,
                    kind="describe_option",
                    org_id=project.org_id,
                    session=session,
                )
                description_text = desc_obj.description
            except Exception:
                description_text = (
                    f"{scheme_label} prioritizes primary living spaces along the entrance side with optimal daylight. "
                    "Bedrooms are clustered in the quiet zone with dedicated bath access. "
                    "Circulation is streamlined to maximize usable carpet area."
                )

            plan = Plan(
                project_id=project.id,
                org_id=project.org_id,
                name=scheme_label,
                created_by="solver",
                score_breakdown=cand.score_breakdown.model_dump(),
                description=description_text,
                current_version=1,
            )
            session.add(plan)
            await session.flush()

            version = PlanVersion(
                plan_id=plan.id,
                version=1,
                data=cand.plan_data.model_dump(),
                created_by="solver",
                message=f"Synthesized layout option (seed={cand.seed})",
            )
            session.add(version)

            # Statutory review result attachment
            if ruleset:
                rev_res = review_plan(cand.plan_data, envelope, ruleset)
                rev_summary = {
                    "pass_count": rev_res.summary.get("pass_count", 0),
                    "review_count": rev_res.summary.get("review_count", 0),
                    "fail_count": rev_res.summary.get("fail_count", 0),
                }
                review_record = PlanReview(
                    plan_id=plan.id,
                    version=1,
                    issues=[issue.model_dump() for issue in rev_res.issues],
                    summary=rev_summary,
                )
                session.add(review_record)

            created_plans.append(plan)

        # 5. Complete (100%)
        result_data = {
            "status": "success",
            "options_count": len(created_plans),
            "plan_ids": [str(p.id) for p in created_plans],
        }
        await repo.update_status(job, JobStatus.DONE, progress=100, result=result_data)
        await session.commit()

    logger.info("plan_generation_job_completed", job_id=str(j_id), count=len(created_plans))
    return result_data


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("arq_worker_startup")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("arq_worker_shutdown")


settings = get_settings()


class WorkerSettings:
    functions = [process_dummy_job, process_plan_generation_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300
