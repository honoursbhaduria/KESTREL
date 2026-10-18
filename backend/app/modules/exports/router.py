"""API router for Plan 3D GLB Models and exports (Phase 5 Part B)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import AuthContext, get_current_auth_context
from app.modules.exports.gltf import generate_plan_glb
from app.modules.plans.models import Plan, PlanVersion
from app.modules.plans.schemas import PlanData

router = APIRouter(tags=["exports"])

# In-memory cache for generated GLB binaries keyed by (plan_id, version)
_GLB_CACHE: dict[tuple[UUID, int], bytes] = {}


@router.get(
    "/plans/{plan_id}/versions/{version}/model.glb",
    summary="Download binary glTF 2.0 3D model for plan version",
    response_class=Response,
)
async def get_plan_model_glb(
    plan_id: UUID,
    version: int,
    auth: AuthContext = Depends(get_current_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    # 1. Verify plan belongs to user's org
    plan = (
        await db.execute(
            select(Plan).where(Plan.id == plan_id, Plan.org_id == auth.org.id)
        )
    ).scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    cache_key = (plan_id, version)
    if cache_key in _GLB_CACHE:
        return Response(content=_GLB_CACHE[cache_key], media_type="model/gltf-binary")

    # 2. Fetch specific plan version
    ver_row = (
        await db.execute(
            select(PlanVersion).where(
                PlanVersion.plan_id == plan_id,
                PlanVersion.version == version,
            )
        )
    ).scalars().first()
    if not ver_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Version {version} not found")

    # 3. Generate 3D binary container
    plan_data = PlanData.model_validate(ver_row.data)
    glb_bytes = generate_plan_glb(plan_data)
    _GLB_CACHE[cache_key] = glb_bytes

    return Response(
        content=glb_bytes,
        media_type="model/gltf-binary",
        headers={"Content-Disposition": f'attachment; filename="model_{plan_id}_v{version}.glb"'},
    )
