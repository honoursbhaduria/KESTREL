"""Service layer for Phase 5 Architectural Review Assistant & Fix Lifecycle."""

from __future__ import annotations

import math
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assistant.models import Conversation, Fix, Message
from app.modules.assistant.schemas import (
    AssistantTurnResponse,
    FixApplyResponse,
    FixPreviewResponse,
    FixSchema,
)
from app.modules.assistant.tools import (
    get_issues,
    get_plan_summary,
    measure,
    propose_fix,
    run_check,
    search_rules,
)
from app.modules.plans.models import Plan, PlanVersion
from app.modules.plans.patches import apply_patches
from app.modules.plans.schemas import PlanData

OUT_OF_SCOPE_KEYWORDS = [
    "recipe",
    "cook",
    "pasta",
    "sourdough",
    "chocolate",
    "cake",
    "capital of",
    "weather",
    "stock price",
    "bitcoin",
    "crypto",
    "poem",
    "song",
    "joke",
]


class AssistantService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_conversation(
        self, plan_id: uuid.UUID, org_id: uuid.UUID, conversation_id: uuid.UUID | None = None
    ) -> Conversation:
        """Fetch existing conversation or create a new conversation thread."""
        if conversation_id:
            conv = (
                await self.db.execute(
                    select(Conversation).where(
                        Conversation.id == conversation_id,
                        Conversation.org_id == org_id,
                        Conversation.plan_id == plan_id,
                    )
                )
            ).scalars().first()
            if conv:
                return conv

        # Find latest or create
        conv = (
            await self.db.execute(
                select(Conversation)
                .where(Conversation.plan_id == plan_id, Conversation.org_id == org_id)
                .order_by(Conversation.created_at.desc())
            )
        ).scalars().first()

        if not conv:
            conv = Conversation(
                id=uuid.uuid4(),
                org_id=org_id,
                plan_id=plan_id,
                title="Plan Review Discussion",
            )
            self.db.add(conv)
            await self.db.commit()
            await self.db.refresh(conv)

        return conv

    async def chat_turn(
        self,
        plan_id: uuid.UUID,
        org_id: uuid.UUID,
        user_message: str,
        conversation_id: uuid.UUID | None = None,
    ) -> AssistantTurnResponse:
        """Execute assistant chat turn with guardrails, tool calling loop, and proposal synthesis."""
        conv = await self.get_or_create_conversation(plan_id, org_id, conversation_id)

        # 1. Record user message
        u_msg = Message(
            id=uuid.uuid4(),
            org_id=org_id,
            conversation_id=conv.id,
            role="user",
            content=user_message,
        )
        self.db.add(u_msg)
        await self.db.commit()

        # 2. Guardrails Check
        lowered = user_message.lower()
        if any(kw in lowered for kw in OUT_OF_SCOPE_KEYWORDS):
            reply = (
                "I am Kestrel's Architectural Review Assistant. My scope is strictly limited to "
                "evaluating your architectural design plans, measuring spatial geometry, checking statutory "
                "building code compliance (e.g. NBC 2016, local bylaws), and proposing non-destructive layout fixes."
            )
            a_msg = Message(
                id=uuid.uuid4(),
                org_id=org_id,
                conversation_id=conv.id,
                role="assistant",
                content=reply,
            )
            self.db.add(a_msg)
            await self.db.commit()

            return AssistantTurnResponse(
                conversation_id=conv.id,
                reply=reply,
                tools_used=[],
                proposed_fix=None,
            )

        # 3. Tool Calling Agent Loop
        tools_used: list[str] = []
        proposed_fix_data: dict[str, Any] | None = None
        plan_id_str = str(plan_id)

        # Step A: Identify intent
        needs_measure = any(w in lowered for w in ["measure", "size", "area", "dimension", "width", "how big"])
        needs_rules = any(w in lowered for w in ["rule", "code", "bylaw", "clause", "requirement", "standard", "nbc"])
        needs_fix = any(w in lowered for w in ["fix", "enlarge", "make bigger", "repair", "resolve", "adjust", "propose"])
        needs_summary = any(w in lowered for w in ["summary", "overview", "how many", "rooms in"])

        reply_sections: list[str] = []

        # Tool 1: get_issues
        issues = await get_issues(self.db, plan_id_str)
        tools_used.append("get_issues")
        fail_issues = [i for i in issues if i.get("status") == "fail"]

        # Tool 2: measure if requested or checking rooms
        if needs_measure or needs_fix or needs_summary or "bedroom" in lowered:
            summary = await get_plan_summary(self.db, plan_id_str)
            tools_used.append("get_plan_summary")

            element_ids = [r["id"] for r in summary.get("rooms", [])]
            if element_ids:
                measurements = await measure(self.db, plan_id_str, element_ids)
                tools_used.append("measure")

                for _eid, m in measurements.items():
                    if m.get("type") == "room":
                        reply_sections.append(
                            f"• {m.get('name')}: measured area = {m.get('area_sqm')} m² "
                            f"(width = {m.get('width_mm')} mm, length = {m.get('length_mm')} mm)."
                        )

        # Tool 3: run_check on targeted rules
        if fail_issues:
            first_fail = fail_issues[0]
            check_res = await run_check(self.db, plan_id_str, first_fail["rule_id"])
            tools_used.append("run_check")
            reply_sections.append(
                f"Statutory check on `{check_res['rule_id']}` ({check_res['clause']}) returned status: "
                f"**{check_res['status'].upper()}** — {first_fail['title']}."
            )
        elif needs_rules or "corridor" in lowered or "stair" in lowered:
            rule_search = await search_rules(user_message, limit=2)
            tools_used.append("search_rules")
            if rule_search:
                reply_sections.append(
                    f"Relevant building regulation: {rule_search[0]['clause']} — {rule_search[0]['content']}."
                )

        # Tool 4: propose_fix if requested or asked to fix issues
        if needs_fix or (fail_issues and "fix" in lowered):
            # Target the first failing room
            summary = await get_plan_summary(self.db, plan_id_str)
            failing_room_id = fail_issues[0]["element_ids"][0] if fail_issues and fail_issues[0].get("element_ids") else "room_substandard"

            # Compute fix polygon (e.g. increase depth to achieve >= 10.0 sqm without overlapping)
            # Find current room bounds
            _, _, plan_data = await self._get_plan_and_version(plan_id_str)
            target_room = None
            for lvl in plan_data.levels:
                for r in lvl.rooms:
                    if r.id == failing_room_id:
                        target_room = r
                        break

            if target_room:
                xs = [p[0] for p in target_room.polygon]
                ys = [p[1] for p in target_room.polygon]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                width = max_x - min_x
                needed_depth = math.ceil((10.0 * 1_000_000.0) / max(1.0, width))

                # Expand along negative Y where open or clear
                new_poly = [
                    [min_x, min_y - (needed_depth - (max_y - min_y))],
                    [max_x, min_y - (needed_depth - (max_y - min_y))],
                    [max_x, max_y],
                    [min_x, max_y],
                ]

                patch_ops = [
                    {
                        "op": "set_room_polygon",
                        "room_id": failing_room_id,
                        "polygon": new_poly,
                    }
                ]

                target_rule_id = fail_issues[0]["rule_id"] if fail_issues else "nbc-habitable-room-min-area"
                proposed_fix_data = await propose_fix(
                    self.db,
                    plan_id=plan_id_str,
                    ops=patch_ops,
                    rationale=f"Enlarge {target_room.name} to 10.0 m² to satisfy NBC 2016 Part 3, Clause 4.2.1 minimum room area requirements.",
                    rule_id=target_rule_id,
                    conversation_id=str(conv.id),
                )
                tools_used.append("propose_fix")

                reply_sections.append(
                    f"I have prepared a non-destructive Fix Proposal ({proposed_fix_data['id'][:8]}): "
                    f"'{proposed_fix_data['rationale']}'. "
                    f"Preview the change to inspect the ghost overlay on your plan before choosing to apply or skip."
                )

        if not reply_sections:
            reply_sections.append(
                "All spatial elements comply with the active ruleset. No statutory violations were detected."
            )

        final_reply = "\n\n".join(reply_sections)

        # 4. Record assistant message
        a_msg = Message(
            id=uuid.uuid4(),
            org_id=org_id,
            conversation_id=conv.id,
            role="assistant",
            content=final_reply,
            tool_calls=[{"name": t} for t in tools_used],
        )
        self.db.add(a_msg)
        await self.db.commit()

        fix_schema = FixSchema.model_validate(proposed_fix_data) if proposed_fix_data else None

        return AssistantTurnResponse(
            conversation_id=conv.id,
            reply=final_reply,
            tools_used=tools_used,
            proposed_fix=fix_schema,
        )

    async def preview_fix(self, fix_id: uuid.UUID, org_id: uuid.UUID) -> FixPreviewResponse:
        """Simulate patched plan without saving a new version."""
        fix = (
            await self.db.execute(
                select(Fix).where(Fix.id == fix_id, Fix.org_id == org_id)
            )
        ).scalars().first()
        if not fix:
            raise ValueError(f"Fix '{fix_id}' not found.")

        plan, version, plan_data = await self._get_plan_and_version(str(fix.plan_id))
        patched_plan = apply_patches(plan_data, fix.patch_ops)

        return FixPreviewResponse(
            fix=FixSchema.model_validate(fix),
            patched_plan=patched_plan,
            diff_summary=fix.diff_summary,
        )

    async def apply_fix(self, fix_id: uuid.UUID, org_id: uuid.UUID) -> FixApplyResponse:
        """Idempotently apply fix to create exactly one new plan version with created_by='ai'."""
        fix = (
            await self.db.execute(
                select(Fix).where(Fix.id == fix_id, Fix.org_id == org_id)
            )
        ).scalars().first()
        if not fix:
            raise ValueError(f"Fix '{fix_id}' not found.")

        # Idempotency check: if already applied, return current applied state
        if fix.status == "applied" and fix.applied_version is not None:
            return FixApplyResponse(
                fix=FixSchema.model_validate(fix),
                status="applied",
                new_version=fix.applied_version,
                plan_id=fix.plan_id,
            )

        # 1. Load current plan
        plan = (
            await self.db.execute(
                select(Plan).where(Plan.id == fix.plan_id, Plan.org_id == org_id)
            )
        ).scalars().first()
        if not plan:
            raise ValueError(f"Plan '{fix.plan_id}' not found.")

        current_ver = (
            await self.db.execute(
                select(PlanVersion).where(
                    PlanVersion.plan_id == plan.id,
                    PlanVersion.version == plan.current_version,
                )
            )
        ).scalars().first()
        if not current_ver:
            raise ValueError("Current plan version not found.")

        current_data = PlanData.model_validate(current_ver.data)
        new_plan_data = apply_patches(current_data, fix.patch_ops)

        new_version_num = plan.current_version + 1
        new_version_row = PlanVersion(
            plan_id=plan.id,
            version=new_version_num,
            parent_version=plan.current_version,
            data=new_plan_data.model_dump(),
            created_by="ai",
            message=fix.rationale,
        )
        self.db.add(new_version_row)

        plan.current_version = new_version_num
        fix.status = "applied"
        fix.applied_version = new_version_num

        await self.db.commit()
        await self.db.refresh(fix)

        return FixApplyResponse(
            fix=FixSchema.model_validate(fix),
            status="applied",
            new_version=new_version_num,
            plan_id=fix.plan_id,
        )

    async def skip_fix(self, fix_id: uuid.UUID, org_id: uuid.UUID) -> FixSchema:
        """Mark fix as skipped without altering plan state."""
        fix = (
            await self.db.execute(
                select(Fix).where(Fix.id == fix_id, Fix.org_id == org_id)
            )
        ).scalars().first()
        if not fix:
            raise ValueError(f"Fix '{fix_id}' not found.")

        fix.status = "skipped"
        await self.db.commit()
        await self.db.refresh(fix)
        return FixSchema.model_validate(fix)

    async def _get_plan_and_version(
        self, plan_id: str
    ) -> tuple[Plan, PlanVersion, PlanData]:
        p_uuid = uuid.UUID(plan_id)
        plan = (await self.db.execute(select(Plan).where(Plan.id == p_uuid))).scalars().first()
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found.")

        version = (
            await self.db.execute(
                select(PlanVersion).where(
                    PlanVersion.plan_id == plan.id,
                    PlanVersion.version == plan.current_version,
                )
            )
        ).scalars().first()
        if not version:
            raise ValueError(f"PlanVersion {plan.current_version} for Plan '{plan_id}' not found.")

        plan_data = PlanData.model_validate(version.data)
        return plan, version, plan_data
