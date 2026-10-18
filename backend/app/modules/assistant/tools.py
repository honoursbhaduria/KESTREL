"""Architectural Review Assistant Tools (Phase 5).
Pure, typed, Pydantic-validated tool calls that query spatial models, measure geometry,
execute statutory checkers, query building bylaws via RAG, and simulate non-destructive fix proposals.
"""

from __future__ import annotations

import math
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assistant.models import Fix
from app.modules.plans.models import Plan, PlanVersion
from app.modules.plans.patches import apply_patches
from app.modules.plans.schemas import PlanData
from app.modules.projects.models import Project
from app.modules.rules.engine import review_plan
from app.modules.rules.loader import get_ruleset, load_all_rulesets
from app.modules.rules.rag import search_rules as rag_search_rules


def _compute_polygon_area_sqm(pts: list[list[float]]) -> float:
    """Compute polygon area in square meters using Shoelace formula."""
    if len(pts) < 3:
        return 0.0
    area_mm2 = 0.0
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        area_mm2 += pts[i][0] * pts[j][1]
        area_mm2 -= pts[j][0] * pts[i][1]
    return abs(area_mm2) / 2_000_000.0


async def _get_plan_and_version(
    db: AsyncSession, plan_id: str
) -> tuple[Plan, PlanVersion, PlanData]:
    """Fetch Plan, current PlanVersion, and parsed PlanData."""
    p_uuid = uuid.UUID(plan_id)
    plan = (await db.execute(select(Plan).where(Plan.id == p_uuid))).scalars().first()
    if not plan:
        raise ValueError(f"Plan '{plan_id}' not found.")

    version = (
        await db.execute(
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


async def _get_project_ruleset(db: AsyncSession, project_id: uuid.UUID):
    """Fetch project ruleset or default to india-nbc-2016."""
    project = (await db.execute(select(Project).where(Project.id == project_id))).scalars().first()
    ruleset_id = project.ruleset_id if project and project.ruleset_id else "india-nbc-2016"
    ruleset = get_ruleset(ruleset_id)
    if not ruleset:
        # Fallback to first available ruleset
        available = load_all_rulesets()
        ruleset = available[0] if available else None
    return ruleset


async def get_plan_summary(db: AsyncSession, plan_id: str) -> dict[str, Any]:
    """Inspect the architectural scheme and return structural summary metrics."""
    plan, version, plan_data = await _get_plan_and_version(db, plan_id)

    total_area_sqm = 0.0
    rooms_summary = []

    for lvl in plan_data.levels:
        for r in lvl.rooms:
            area = _compute_polygon_area_sqm(r.polygon)
            total_area_sqm += area
            rooms_summary.append({
                "id": r.id,
                "name": r.name,
                "type": r.type,
                "level": lvl.name,
                "area_sqm": round(area, 2),
            })

    return {
        "plan_id": str(plan.id),
        "name": plan.name,
        "current_version": plan.current_version,
        "level_count": len(plan_data.levels),
        "room_count": sum(len(lvl.rooms) for lvl in plan_data.levels),
        "wall_count": sum(len(lvl.walls) for lvl in plan_data.levels),
        "opening_count": sum(len(lvl.openings) for lvl in plan_data.levels),
        "stair_count": sum(len(lvl.stairs) for lvl in plan_data.levels),
        "total_area_sqm": round(total_area_sqm, 2),
        "rooms": rooms_summary,
    }


async def get_issues(
    db: AsyncSession, plan_id: str, status: str | None = None
) -> list[dict[str, Any]]:
    """Run statutory rule checkers on the current plan and return issues filtered by status."""
    plan, _, plan_data = await _get_plan_and_version(db, plan_id)
    ruleset = await _get_project_ruleset(db, plan.project_id)

    if not ruleset:
        return []

    review_res = review_plan(plan=plan_data, envelope=None, ruleset=ruleset)
    issues_list = []

    for issue in review_res.issues:
        if status and issue.status != status:
            continue
        issues_list.append({
            "id": issue.id,
            "rule_id": issue.rule_id,
            "clause": issue.clause,
            "category": issue.category,
            "status": issue.status,
            "title": issue.message,
            "description": issue.message,
            "message": issue.message,
            "element_ids": issue.element_ids,
            "measured": issue.measured,
            "required": issue.required,
        })

    return issues_list


async def run_check(
    db: AsyncSession, plan_id: str, rule_id: str
) -> dict[str, Any]:
    """Execute a specific statutory checker against the plan and return findings."""
    plan, _, plan_data = await _get_plan_and_version(db, plan_id)
    ruleset = await _get_project_ruleset(db, plan.project_id)

    if not ruleset:
        return {"rule_id": rule_id, "clause": "N/A", "status": "pass", "issues": []}

    review_res = review_plan(plan=plan_data, envelope=None, ruleset=ruleset)
    matched_issues = [i for i in review_res.issues if i.rule_id == rule_id]

    status = "pass"
    if any(i.status == "fail" for i in matched_issues):
        status = "fail"
    elif any(i.status == "review" for i in matched_issues):
        status = "review"

    # Find clause description from ruleset
    clause = "NBC 2016"
    for r in ruleset.rules:
        if r.id == rule_id:
            clause = r.clause
            break

    return {
        "rule_id": rule_id,
        "clause": clause,
        "status": status,
        "issues": [
            {
                "id": i.id,
                "title": i.message,
                "description": i.message,
                "message": i.message,
                "status": i.status,
                "element_ids": i.element_ids,
                "measured": i.measured,
                "required": i.required,
            }
            for i in matched_issues
        ],
    }


async def measure(
    db: AsyncSession, plan_id: str, element_ids: list[str]
) -> dict[str, Any]:
    """Compute precise geometric measurements (areas, widths, lengths, clearances) for specified elements."""
    _, _, plan_data = await _get_plan_and_version(db, plan_id)
    results: dict[str, Any] = {}

    for eid in element_ids:
        found = False
        for lvl in plan_data.levels:
            # Check rooms
            for r in lvl.rooms:
                if r.id == eid:
                    xs = [p[0] for p in r.polygon]
                    ys = [p[1] for p in r.polygon]
                    width_mm = max(xs) - min(xs)
                    length_mm = max(ys) - min(ys)
                    if width_mm > length_mm:
                        width_mm, length_mm = length_mm, width_mm
                    area_sqm = _compute_polygon_area_sqm(r.polygon)
                    results[eid] = {
                        "type": "room",
                        "name": r.name,
                        "room_type": r.type,
                        "area_sqm": round(area_sqm, 2),
                        "width_mm": round(width_mm, 1),
                        "length_mm": round(length_mm, 1),
                    }
                    found = True
                    break
            if found:
                break

            # Check walls
            for w in lvl.walls:
                if w.id == eid:
                    length_mm = math.dist(w.start, w.end)
                    results[eid] = {
                        "type": "wall",
                        "length_mm": round(length_mm, 1),
                        "thickness_mm": w.thickness_mm,
                        "is_external": w.is_external,
                    }
                    found = True
                    break
            if found:
                break

            # Check openings
            for op in lvl.openings:
                if op.id == eid:
                    results[eid] = {
                        "type": "opening",
                        "opening_type": op.kind,
                        "width_mm": op.width_mm,
                        "height_mm": op.height_mm,
                        "sill_mm": op.sill_mm,
                    }
                    found = True
                    break
            if found:
                break

            # Check stairs
            for s in lvl.stairs:
                if s.id == eid:
                    area_sqm = _compute_polygon_area_sqm(s.polygon)
                    results[eid] = {
                        "type": "stair",
                        "area_sqm": round(area_sqm, 2),
                        "riser_mm": s.riser_mm,
                        "tread_mm": s.tread_mm,
                        "direction": s.direction,
                    }
                    found = True
                    break
            if found:
                break

    return results


async def search_rules(query: str, limit: int = 3) -> list[dict[str, Any]]:
    """Perform RAG / semantic search over statutory building codes."""
    try:
        rag_results = await rag_search_rules(query=query, limit=limit)
        if rag_results:
            return [
                {
                    "clause": r.section,
                    "content": r.content,
                    "document": r.document,
                    "section": r.section,
                    "similarity": round(r.score, 3),
                }
                for r in rag_results
            ]
    except Exception:
        pass

    # Keyword fallback over loaded rulesets
    results = []
    q_words = query.lower().split()
    for ruleset in load_all_rulesets():
        for rule in ruleset.rules:
            text = f"{rule.id} {rule.title} {rule.notes or ''} {rule.clause}".lower()
            if any(w in text for w in q_words):
                results.append({
                    "clause": rule.clause,
                    "content": f"{rule.title}: {rule.notes or ''}",
                    "document": ruleset.name,
                    "section": rule.clause,
                    "similarity": 0.85,
                })
                if len(results) >= limit:
                    break
        if len(results) >= limit:
            break

    return results


async def propose_fix(
    db: AsyncSession,
    plan_id: str,
    ops: list[dict[str, Any]],
    rationale: str,
    rule_id: str,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """propose_fix NEVER mutates the plan directly.
    It creates a Fix row (status: proposed), applies patches in-memory to calculate the issue diff,
    flags newly introduced fails, and stores the proposal for explicit user approval.
    """
    plan, version, plan_data = await _get_plan_and_version(db, plan_id)
    ruleset = await _get_project_ruleset(db, plan.project_id)

    # 1. Apply patches in-memory
    patched_plan = apply_patches(plan_data, ops)

    # 2. Run reviews on original and patched plans
    orig_review = review_plan(plan=plan_data, envelope=None, ruleset=ruleset) if ruleset else None
    new_review = review_plan(plan=patched_plan, envelope=None, ruleset=ruleset) if ruleset else None

    # 3. Compute issue diff
    orig_issues_map = {i.id: i for i in (orig_review.issues if orig_review else [])}
    new_issues_map = {i.id: i for i in (new_review.issues if new_review else [])}

    resolved = []
    introduced = []
    unchanged = []

    for i_id, orig_i in orig_issues_map.items():
        if orig_i.status == "fail":
            new_i = new_issues_map.get(i_id)
            if not new_i or new_i.status != "fail":
                resolved.append({
                    "id": orig_i.id,
                    "rule_id": orig_i.rule_id,
                    "title": orig_i.message,
                    "message": orig_i.message,
                    "status_before": orig_i.status,
                    "status_after": new_i.status if new_i else "pass",
                })
            else:
                unchanged.append({"id": orig_i.id, "rule_id": orig_i.rule_id, "title": orig_i.message})

    # Check for newly introduced fails or reviews
    introduced_fails = 0
    for i_id, new_i in new_issues_map.items():
        if new_i.status in ("fail", "review"):
            matching_orig = orig_issues_map.get(i_id)
            if not matching_orig or matching_orig.status == "pass":
                introduced.append({
                    "id": new_i.id,
                    "rule_id": new_i.rule_id,
                    "title": new_i.message,
                    "message": new_i.message,
                    "status": new_i.status,
                    "description": new_i.message,
                })
                if new_i.status == "fail":
                    introduced_fails += 1

    diff_summary = {
        "resolved": resolved,
        "introduced": introduced,
        "unchanged": unchanged,
    }

    # Extract clause reference
    clause = "NBC 2016"
    if ruleset:
        for r in ruleset.rules:
            if r.id == rule_id:
                clause = r.clause
                break

    fix = Fix(
        id=uuid.uuid4(),
        org_id=plan.org_id,
        plan_id=plan.id,
        conversation_id=uuid.UUID(conversation_id) if conversation_id else None,
        status="proposed",
        rationale=rationale,
        rule_id=rule_id,
        clause=clause,
        patch_ops=ops,
        diff_summary=diff_summary,
        introduced_fails=introduced_fails,
        applied_version=None,
    )
    db.add(fix)
    await db.commit()
    await db.refresh(fix)

    return {
        "id": str(fix.id),
        "plan_id": str(fix.plan_id),
        "conversation_id": str(fix.conversation_id) if fix.conversation_id else None,
        "status": fix.status,
        "rationale": fix.rationale,
        "rule_id": fix.rule_id,
        "clause": fix.clause,
        "patch_ops": fix.patch_ops,
        "diff_summary": fix.diff_summary,
        "introduced_fails": fix.introduced_fails,
        "applied_version": fix.applied_version,
        "created_at": fix.created_at.isoformat() if fix.created_at else "",
    }
