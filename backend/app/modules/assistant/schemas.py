"""Pydantic schemas for Assistant Conversations, Messages, Tools, and Fix Proposals."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.plans.schemas import PlanData


class ToolCall(BaseModel):
    id: str
    name: str
    args: dict[str, Any]


class MessageCreate(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: UUID
    plan_id: UUID
    title: str
    messages: list[MessageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FixSchema(BaseModel):
    id: UUID
    plan_id: UUID
    conversation_id: UUID | None = None
    status: Literal["proposed", "applied", "skipped"]
    rationale: str
    rule_id: str
    clause: str | None = None
    patch_ops: list[dict[str, Any]]
    diff_summary: dict[str, Any]
    introduced_fails: int = 0
    applied_version: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FixPreviewResponse(BaseModel):
    fix: FixSchema
    patched_plan: PlanData
    diff_summary: dict[str, Any]


class FixApplyResponse(BaseModel):
    fix: FixSchema
    status: Literal["applied"]
    new_version: int
    plan_id: UUID


class AssistantTurnRequest(BaseModel):
    message: str
    conversation_id: UUID | None = None


class AssistantTurnResponse(BaseModel):
    conversation_id: UUID
    reply: str
    tools_used: list[str] = Field(default_factory=list)
    proposed_fix: FixSchema | None = None
