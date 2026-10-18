"""API router for Assistant Conversations, Messages, and Statutory Fix Proposals."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.assistant.models import Conversation, Fix, Message
from app.modules.assistant.schemas import (
    AssistantTurnRequest,
    AssistantTurnResponse,
    ConversationResponse,
    FixApplyResponse,
    FixPreviewResponse,
    FixSchema,
    MessageResponse,
)
from app.modules.assistant.service import AssistantService
from app.modules.auth.dependencies import AuthContext, get_current_auth_context
from app.modules.plans.models import Plan

router = APIRouter(tags=["assistant"])


@router.post(
    "/plans/{plan_id}/assistant",
    response_model=AssistantTurnResponse,
    summary="Submit assistant turn with tool calling and proposal synthesis",
)
async def post_assistant_message(
    plan_id: UUID,
    payload: AssistantTurnRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> AssistantTurnResponse:
    # Verify plan belongs to user's org
    plan = (
        await db.execute(
            select(Plan).where(Plan.id == plan_id, Plan.org_id == auth.org.id)
        )
    ).scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    service = AssistantService(db)
    return await service.chat_turn(
        plan_id=plan_id,
        org_id=auth.org.id,
        user_message=payload.message,
        conversation_id=payload.conversation_id,
    )


@router.get(
    "/plans/{plan_id}/conversations",
    response_model=list[ConversationResponse],
    summary="List conversations for a plan",
)
async def list_plan_conversations(
    plan_id: UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[ConversationResponse]:
    plan = (
        await db.execute(
            select(Plan).where(Plan.id == plan_id, Plan.org_id == auth.org.id)
        )
    ).scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    convs = (
        await db.execute(
            select(Conversation)
            .where(Conversation.plan_id == plan_id, Conversation.org_id == auth.org.id)
            .order_by(Conversation.created_at.desc())
        )
    ).scalars().all()

    return [ConversationResponse.model_validate(c) for c in convs]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="Get message history for a conversation",
)
async def get_conversation_messages(
    conversation_id: UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[MessageResponse]:
    conv = (
        await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.org_id == auth.org.id,
            )
        )
    ).scalars().first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    msgs = (
        await db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.org_id == auth.org.id,
            )
            .order_by(Message.created_at.asc())
        )
    ).scalars().all()

    return [MessageResponse.model_validate(m) for m in msgs]


@router.post(
    "/fixes/{fix_id}/preview",
    response_model=FixPreviewResponse,
    summary="Preview patched plan for a proposal without mutation",
)
async def preview_fix(
    fix_id: UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> FixPreviewResponse:
    service = AssistantService(db)
    try:
        return await service.preview_fix(fix_id=fix_id, org_id=auth.org.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/fixes/{fix_id}/apply",
    response_model=FixApplyResponse,
    summary="Apply proposal to create a new plan version with created_by='ai' (idempotent)",
)
async def apply_fix(
    fix_id: UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> FixApplyResponse:
    service = AssistantService(db)
    try:
        return await service.apply_fix(fix_id=fix_id, org_id=auth.org.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/fixes/{fix_id}/skip",
    response_model=FixSchema,
    summary="Skip proposal without creating a new plan version",
)
async def skip_fix(
    fix_id: UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> FixSchema:
    service = AssistantService(db)
    try:
        return await service.skip_fix(fix_id=fix_id, org_id=auth.org.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/plans/{plan_id}/fixes",
    response_model=list[FixSchema],
    summary="List all fix proposals for a plan",
)
async def list_plan_fixes(
    plan_id: UUID,
    auth: AuthContext = Depends(get_current_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[FixSchema]:
    plan = (
        await db.execute(
            select(Plan).where(Plan.id == plan_id, Plan.org_id == auth.org.id)
        )
    ).scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    fixes = (
        await db.execute(
            select(Fix)
            .where(Fix.plan_id == plan_id, Fix.org_id == auth.org.id)
            .order_by(Fix.created_at.desc())
        )
    ).scalars().all()

    return [FixSchema.model_validate(f) for f in fixes]
