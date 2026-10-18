"""Plan service managing plan versioning, patches, diffs, undo/redo, and reviews (Phase 3)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.modules.planning.envelope import Envelope
from app.modules.plans.models import Plan, PlanReview, PlanVersion
from app.modules.plans.patches import PlanDiff, apply_patches, compute_plan_diff
from app.modules.plans.schemas import (
    ApplyPatchesRequest,
    PlanCreate,
    PlanData,
    PlanResponse,
    PlanVersionResponse,
)
from app.modules.projects.models import Project
from app.modules.projects.service import ProjectService
from app.modules.rules.engine import ReviewEngine, ReviewResult
from app.modules.rules.loader import get_ruleset


class PlanService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_plan(
        self,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        data: PlanCreate,
    ) -> PlanResponse:
        # Validate project exists and belongs to org
        proj_stmt = select(Project).where(
            Project.id == project_id,
            Project.org_id == org_id,
        )
        res = await self.session.execute(proj_stmt)
        project = res.scalar_one_or_none()
        if not project:
            raise NotFoundError(message=f"Project '{project_id}' not found.")

        # Validate plan data
        if isinstance(data.data, PlanData):
            validated_plan = data.data
        else:
            validated_plan = PlanData.model_validate(data.data)

        plan_id = uuid.uuid4()
        plan = Plan(
            id=plan_id,
            org_id=org_id,
            project_id=project_id,
            name=data.name,
            current_version=1,
        )
        self.session.add(plan)

        version_record = PlanVersion(
            id=uuid.uuid4(),
            plan_id=plan_id,
            version=1,
            parent_version=None,
            data=validated_plan.model_dump(),
            created_by="user",
            message=data.message,
        )
        self.session.add(version_record)

        await self.session.commit()
        await self.session.refresh(plan)

        return PlanResponse(
            id=str(plan.id),
            project_id=str(plan.project_id),
            name=plan.name,
            current_version=plan.current_version,
            data=validated_plan,
            created_at=plan.created_at.isoformat(),
            updated_at=plan.updated_at.isoformat(),
        )

    async def get_plan(
        self,
        plan_id: uuid.UUID,
        org_id: uuid.UUID,
        version: int | None = None,
    ) -> PlanResponse:
        stmt = select(Plan).where(Plan.id == plan_id, Plan.org_id == org_id)
        res = await self.session.execute(stmt)
        plan = res.scalar_one_or_none()
        if not plan:
            raise NotFoundError(message=f"Plan '{plan_id}' not found.")

        target_version = version or plan.current_version
        v_stmt = select(PlanVersion).where(
            PlanVersion.plan_id == plan_id,
            PlanVersion.version == target_version,
        )
        v_res = await self.session.execute(v_stmt)
        version_rec = v_res.scalar_one_or_none()
        if not version_rec:
            raise NotFoundError(
                message=f"Plan version '{target_version}' not found for plan '{plan_id}'."
            )

        plan_data = PlanData.model_validate(version_rec.data)
        return PlanResponse(
            id=str(plan.id),
            project_id=str(plan.project_id),
            name=plan.name,
            current_version=target_version,
            data=plan_data,
            created_at=plan.created_at.isoformat(),
            updated_at=plan.updated_at.isoformat(),
        )

    async def apply_patches(
        self,
        plan_id: uuid.UUID,
        org_id: uuid.UUID,
        req: ApplyPatchesRequest,
    ) -> PlanResponse:
        stmt = select(Plan).where(Plan.id == plan_id, Plan.org_id == org_id)
        res = await self.session.execute(stmt)
        plan = res.scalar_one_or_none()
        if not plan:
            raise NotFoundError(message=f"Plan '{plan_id}' not found.")

        # Get current version data
        v_stmt = select(PlanVersion).where(
            PlanVersion.plan_id == plan_id,
            PlanVersion.version == plan.current_version,
        )
        v_res = await self.session.execute(v_stmt)
        current_version_rec = v_res.scalar_one_or_none()
        if not current_version_rec:
            raise NotFoundError(message="Current plan version data missing.")

        current_data = PlanData.model_validate(current_version_rec.data)

        try:
            updated_data = apply_patches(current_data, req.patches)
        except Exception as e:
            raise BadRequestError(message=f"Failed to apply patches: {e}") from e

        new_version = plan.current_version + 1
        new_version_rec = PlanVersion(
            id=uuid.uuid4(),
            plan_id=plan.id,
            version=new_version,
            parent_version=plan.current_version,
            data=updated_data.model_dump(),
            created_by=req.created_by,
            message=req.message or f"Applied {len(req.patches)} patch(es)",
        )
        self.session.add(new_version_rec)
        plan.current_version = new_version

        await self.session.commit()
        await self.session.refresh(plan)

        return PlanResponse(
            id=str(plan.id),
            project_id=str(plan.project_id),
            name=plan.name,
            current_version=plan.current_version,
            data=updated_data,
            created_at=plan.created_at.isoformat(),
            updated_at=plan.updated_at.isoformat(),
        )

    async def undo(self, plan_id: uuid.UUID, org_id: uuid.UUID) -> PlanResponse:
        stmt = select(Plan).where(Plan.id == plan_id, Plan.org_id == org_id)
        res = await self.session.execute(stmt)
        plan = res.scalar_one_or_none()
        if not plan:
            raise NotFoundError(message=f"Plan '{plan_id}' not found.")

        if plan.current_version <= 1:
            return await self.get_plan(plan_id, org_id)

        # Find current version to get its parent_version
        v_stmt = select(PlanVersion).where(
            PlanVersion.plan_id == plan_id,
            PlanVersion.version == plan.current_version,
        )
        v_res = await self.session.execute(v_stmt)
        curr = v_res.scalar_one_or_none()
        target_version = (
            curr.parent_version if curr and curr.parent_version else plan.current_version - 1
        )

        plan.current_version = target_version
        await self.session.commit()
        await self.session.refresh(plan)
        return await self.get_plan(plan_id, org_id)

    async def redo(self, plan_id: uuid.UUID, org_id: uuid.UUID) -> PlanResponse:
        stmt = select(Plan).where(Plan.id == plan_id, Plan.org_id == org_id)
        res = await self.session.execute(stmt)
        plan = res.scalar_one_or_none()
        if not plan:
            raise NotFoundError(message=f"Plan '{plan_id}' not found.")

        # Look for child version that has parent_version == current_version or next version
        v_stmt = (
            select(PlanVersion)
            .where(
                PlanVersion.plan_id == plan_id,
                PlanVersion.parent_version == plan.current_version,
            )
            .order_by(PlanVersion.version.asc())
        )
        v_res = await self.session.execute(v_stmt)
        child = v_res.scalars().first()

        if not child:
            # Fallback to current_version + 1 if exists
            v2_stmt = select(PlanVersion).where(
                PlanVersion.plan_id == plan_id,
                PlanVersion.version == plan.current_version + 1,
            )
            v2_res = await self.session.execute(v2_stmt)
            child = v2_res.scalar_one_or_none()

        if child:
            plan.current_version = child.version
            await self.session.commit()
            await self.session.refresh(plan)

        return await self.get_plan(plan_id, org_id)

    async def list_versions(
        self, plan_id: uuid.UUID, org_id: uuid.UUID
    ) -> list[PlanVersionResponse]:
        stmt = select(Plan).where(Plan.id == plan_id, Plan.org_id == org_id)
        res = await self.session.execute(stmt)
        plan = res.scalar_one_or_none()
        if not plan:
            raise NotFoundError(message=f"Plan '{plan_id}' not found.")

        v_stmt = (
            select(PlanVersion)
            .where(PlanVersion.plan_id == plan_id)
            .order_by(PlanVersion.version.asc())
        )
        v_res = await self.session.execute(v_stmt)
        versions = v_res.scalars().all()

        return [
            PlanVersionResponse(
                id=str(v.id),
                plan_id=str(v.plan_id),
                version=v.version,
                parent_version=v.parent_version,
                created_by=v.created_by,
                message=v.message,
                created_at=v.created_at.isoformat(),
            )
            for v in versions
        ]

    async def get_diff(
        self,
        plan_id: uuid.UUID,
        org_id: uuid.UUID,
        from_version: int,
        to_version: int,
    ) -> PlanDiff:
        stmt = select(Plan).where(Plan.id == plan_id, Plan.org_id == org_id)
        res = await self.session.execute(stmt)
        plan = res.scalar_one_or_none()
        if not plan:
            raise NotFoundError(message=f"Plan '{plan_id}' not found.")

        v_stmt = select(PlanVersion).where(
            PlanVersion.plan_id == plan_id,
            PlanVersion.version.in_([from_version, to_version]),
        )
        v_res = await self.session.execute(v_stmt)
        recs = {v.version: v for v in v_res.scalars().all()}

        if from_version not in recs or to_version not in recs:
            raise NotFoundError(
                message=f"Version {from_version} or {to_version} not found for diff."
            )

        plan_a = PlanData.model_validate(recs[from_version].data)
        plan_b = PlanData.model_validate(recs[to_version].data)

        return compute_plan_diff(plan_a, plan_b)

    async def review_plan(
        self,
        plan_id: uuid.UUID,
        org_id: uuid.UUID,
        ruleset_id: str | None = None,
    ) -> ReviewResult:
        stmt = select(Plan).where(Plan.id == plan_id, Plan.org_id == org_id)
        res = await self.session.execute(stmt)
        plan = res.scalar_one_or_none()
        if not plan:
            raise NotFoundError(message=f"Plan '{plan_id}' not found.")

        # Load project for envelope & ruleset
        proj_service = ProjectService(self.session)
        project = await proj_service.get_project(plan.project_id, org_id)

        target_ruleset_id = ruleset_id or project.ruleset_id or "india-nbc-2016"
        ruleset = get_ruleset(target_ruleset_id)
        if not ruleset:
            raise NotFoundError(message=f"Ruleset '{target_ruleset_id}' not found.")

        # Get envelope if plot exists
        envelope: Envelope | None = None
        if project.plot:
            try:
                envelope = await proj_service.get_envelope(project.id, org_id)
            except Exception:
                envelope = None

        # Load current plan version
        v_stmt = select(PlanVersion).where(
            PlanVersion.plan_id == plan_id,
            PlanVersion.version == plan.current_version,
        )
        v_res = await self.session.execute(v_stmt)
        v_rec = v_res.scalar_one_or_none()
        if not v_rec:
            raise NotFoundError(message="Plan version missing.")

        plan_data = PlanData.model_validate(v_rec.data)
        engine = ReviewEngine()
        result = engine.review_plan(plan=plan_data, envelope=envelope, ruleset=ruleset)

        # Archive review record
        review_rec = PlanReview(
            id=uuid.uuid4(),
            plan_id=plan.id,
            version=plan.current_version,
            issues=[i.model_dump() for i in result.issues],
            summary=result.summary,
        )
        self.session.add(review_rec)
        await self.session.commit()

        return result
