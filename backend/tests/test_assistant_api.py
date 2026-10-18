"""Tests for Phase 5 Assistant API & Fix Lifecycle.
TDD tests covering:
- POST /api/v1/plans/{id}/assistant (Chat turn with tool calling & citations)
- POST /api/v1/fixes/{id}/preview (Ghost overlay plan preview without mutation)
- POST /api/v1/fixes/{id}/apply (Idempotent version creation with created_by='ai')
- POST /api/v1/fixes/{id}/skip (Status update without version increment)
- Guardrails against out-of-scope queries
- Introduced fail detection
"""

import uuid

import pytest
from httpx import AsyncClient

from app.modules.plans.schemas import Level, Opening, PlanData, Room, Wall


@pytest.fixture
async def plan_with_issue(client: AsyncClient, auth_org_a: dict) -> dict:
    """Create a project and plan with an undersized room to trigger assistant fixes."""
    headers = auth_org_a["headers"]

    # 1. Create project
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Assistant API Test Project"},
        headers=headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Set NBC ruleset
    await client.put(
        f"/api/v1/projects/{project_id}/ruleset",
        json={"ruleset_id": "india-nbc-2016"},
        headers=headers,
    )

    # 3. Create plan with undersized bedroom (7.0 sqm < 9.5 sqm)
    plan_payload = {
        "name": "Ground Level Scheme",
        "data": {
            "units": "mm",
            "levels": [
                {
                    "id": "lvl_1",
                    "name": "Ground Floor",
                    "elevation_mm": 0,
                    "floor_to_floor_mm": 3000,
                    "rooms": [
                        {
                            "id": "room_substandard",
                            "name": "Substandard Bedroom",
                            "type": "bedroom",
                            "polygon": [[0, 0], [2800, 0], [2800, 2500], [0, 2500]],
                        },
                        {
                            "id": "room_hall",
                            "name": "Living Hall",
                            "type": "living",
                            "polygon": [[2800, 0], [7000, 0], [7000, 4000], [2800, 4000]],
                        },
                    ],
                    "walls": [
                        {
                            "id": "wall_ext",
                            "start": [0, 0],
                            "end": [2800, 0],
                            "thickness_mm": 200,
                            "is_external": True,
                        }
                    ],
                    "openings": [],
                    "stairs": [],
                }
            ],
        },
        "message": "Initial scheme with undersized bedroom",
    }

    resp = await client.post(
        f"/api/v1/projects/{project_id}/plans",
        json=plan_payload,
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_assistant_chat_turn_detects_issue_and_proposes_fix(
    client: AsyncClient, auth_org_a: dict, plan_with_issue: dict
):
    """POST /api/v1/plans/{id}/assistant should run the tool loop, cite rules, and optionally propose a fix."""
    plan_id = plan_with_issue["id"]
    headers = auth_org_a["headers"]

    payload = {
        "message": "Does the bedroom meet statutory minimum size requirements under NBC 2016? If not, propose a fix.",
    }

    resp = await client.post(f"/api/v1/plans/{plan_id}/assistant", json=payload, headers=headers)
    assert resp.status_code == 200, f"Assistant call failed: {resp.text}"

    data = resp.json()
    assert "reply" in data
    assert "tools_used" in data
    assert len(data["tools_used"]) > 0

    # Assistant should cite clause or NBC
    reply_lower = data["reply"].lower()
    assert "nbc" in reply_lower or "4.2.1" in reply_lower or "9.5" in reply_lower or "bedroom" in reply_lower

    # If a fix was proposed, it should be attached
    if data.get("proposed_fix"):
        fix = data["proposed_fix"]
        assert fix["status"] == "proposed"
        assert "diff_summary" in fix


@pytest.mark.asyncio
async def test_fix_preview_does_not_mutate_plan_version(
    client: AsyncClient, auth_org_a: dict, plan_with_issue: dict
):
    """POST /api/v1/fixes/{id}/preview returns the simulated patched plan and diff without incrementing version."""
    plan_id = plan_with_issue["id"]
    headers = auth_org_a["headers"]

    # 1. Ask assistant to propose a fix
    chat_resp = await client.post(
        f"/api/v1/plans/{plan_id}/assistant",
        json={"message": "Please fix the undersized bedroom to meet NBC standards."},
        headers=headers,
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert chat_data.get("proposed_fix") is not None
    fix_id = chat_data["proposed_fix"]["id"]

    # 2. Request preview
    prev_resp = await client.post(f"/api/v1/fixes/{fix_id}/preview", headers=headers)
    assert prev_resp.status_code == 200
    prev_data = prev_resp.json()

    assert "patched_plan" in prev_data
    assert "diff_summary" in prev_data
    assert prev_data["fix"]["id"] == fix_id
    assert prev_data["fix"]["status"] == "proposed"

    # 3. Verify original plan remains at version 1
    plan_check = await client.get(f"/api/v1/plans/{plan_id}", headers=headers)
    assert plan_check.status_code == 200
    assert plan_check.json()["current_version"] == 1


@pytest.mark.asyncio
async def test_fix_apply_is_idempotent(
    client: AsyncClient, auth_org_a: dict, plan_with_issue: dict
):
    """POST /api/v1/fixes/{id}/apply creates a new version with created_by='ai' and is idempotent on repeat calls."""
    plan_id = plan_with_issue["id"]
    headers = auth_org_a["headers"]

    # 1. Propose fix
    chat_resp = await client.post(
        f"/api/v1/plans/{plan_id}/assistant",
        json={"message": "Enlarge the bedroom to satisfy NBC 2016"},
        headers=headers,
    )
    fix_id = chat_resp.json()["proposed_fix"]["id"]

    # 2. Apply fix
    apply_resp1 = await client.post(f"/api/v1/fixes/{fix_id}/apply", headers=headers)
    assert apply_resp1.status_code == 200
    apply_data1 = apply_resp1.json()

    assert apply_data1["status"] == "applied"
    assert apply_data1["new_version"] == 2

    # Verify plan current_version is now 2 and created_by is 'ai'
    plan_v2 = await client.get(f"/api/v1/plans/{plan_id}", headers=headers)
    assert plan_v2.json()["current_version"] == 2

    versions_resp = await client.get(f"/api/v1/plans/{plan_id}/versions", headers=headers)
    v2_info = next(v for v in versions_resp.json() if v["version"] == 2)
    assert v2_info["created_by"] == "ai"

    # 3. Apply the same fix again (idempotency check)
    apply_resp2 = await client.post(f"/api/v1/fixes/{fix_id}/apply", headers=headers)
    assert apply_resp2.status_code == 200
    apply_data2 = apply_resp2.json()
    assert apply_data2["new_version"] == 2

    # Verify NO version 3 was created
    plan_v2_check = await client.get(f"/api/v1/plans/{plan_id}", headers=headers)
    assert plan_v2_check.json()["current_version"] == 2


@pytest.mark.asyncio
async def test_fix_skip_leaves_plan_untouched(
    client: AsyncClient, auth_org_a: dict, plan_with_issue: dict
):
    """POST /api/v1/fixes/{id}/skip marks status='skipped' and does not alter the plan version."""
    plan_id = plan_with_issue["id"]
    headers = auth_org_a["headers"]

    chat_resp = await client.post(
        f"/api/v1/plans/{plan_id}/assistant",
        json={"message": "Propose fixing the bedroom size."},
        headers=headers,
    )
    fix_id = chat_resp.json()["proposed_fix"]["id"]

    skip_resp = await client.post(f"/api/v1/fixes/{fix_id}/skip", headers=headers)
    assert skip_resp.status_code == 200
    assert skip_resp.json()["status"] == "skipped"

    plan_check = await client.get(f"/api/v1/plans/{plan_id}", headers=headers)
    assert plan_check.json()["current_version"] == 1


@pytest.mark.asyncio
async def test_assistant_guardrails_on_unrelated_queries(
    client: AsyncClient, auth_org_a: dict, plan_with_issue: dict
):
    """Assistant must refuse to answer out-of-scope non-architectural questions."""
    plan_id = plan_with_issue["id"]
    headers = auth_org_a["headers"]

    payload = {
        "message": "What is the capital of France and what is a good recipe for sourdough bread?",
    }

    resp = await client.post(f"/api/v1/plans/{plan_id}/assistant", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    reply = data["reply"].lower()

    # Guardrails response
    assert any(w in reply for w in ("architect", "bylaw", "plan", "project", "scope", "design", "rule"))
