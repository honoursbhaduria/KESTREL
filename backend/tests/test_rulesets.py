"""Tests for rulesets as data, YAML schema validation, and project assignment (Phase 2).
Enforces strict TDD: tests written before implementation.
"""

import pytest
from httpx import AsyncClient
from pydantic import ValidationError


async def create_test_project(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Ruleset Test Villa"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_ruleset_yaml_loader_and_schema():
    """Seed rulesets must load cleanly and validate all required rule fields."""
    from app.modules.rules.loader import load_all_rulesets

    rulesets = load_all_rulesets()
    assert len(rulesets) >= 3

    expected_ids = {"india-nbc-2016", "up-bylaws", "uttarakhand-bylaws"}
    found_ids = {r.id for r in rulesets}
    assert expected_ids.issubset(found_ids)

    valid_categories = {
        "setback",
        "far",
        "coverage",
        "height",
        "room_size",
        "width",
        "ventilation",
        "stair",
        "parking",
    }

    # Verify India NBC 2016
    nbc = next(r for r in rulesets if r.id == "india-nbc-2016")
    assert len(nbc.rules) > 0
    for rule in nbc.rules:
        assert rule.id
        assert rule.title
        assert rule.clause
        assert rule.category in valid_categories
        assert rule.severity in ("fail", "review")
        assert isinstance(rule.verified, bool)
        assert isinstance(rule.params, dict)
        if not rule.verified:
            assert "TODO" in rule.notes or "source" in rule.notes.lower()


@pytest.mark.asyncio
async def test_ruleset_validation_rejects_malformed_rule():
    """Ruleset loader must raise ValidationError on malformed rules."""
    from app.modules.rules.schemas import RuleDefinition

    # Missing category
    with pytest.raises(ValidationError):
        RuleDefinition.model_validate(
            {
                "id": "bad-rule",
                "title": "Bad Rule",
                "clause": "Clause 1",
                # category missing
                "applies_to": "plot",
                "check": "check_dummy",
                "params": {},
                "severity": "fail",
                "verified": True,
            }
        )

    # Invalid category
    with pytest.raises(ValidationError):
        RuleDefinition.model_validate(
            {
                "id": "bad-cat",
                "title": "Bad Category",
                "clause": "Clause 1",
                "category": "invalid_category_name",
                "applies_to": "plot",
                "check": "check_dummy",
                "params": {},
                "severity": "fail",
                "verified": True,
            }
        )

    # Invalid severity
    with pytest.raises(ValidationError):
        RuleDefinition.model_validate(
            {
                "id": "bad-sev",
                "title": "Bad Severity",
                "clause": "Clause 1",
                "category": "height",
                "applies_to": "plot",
                "check": "check_dummy",
                "params": {},
                "severity": "critical_error",  # must be fail or review
                "verified": True,
            }
        )


@pytest.mark.asyncio
async def test_get_rulesets_endpoint(client: AsyncClient, auth_org_a: dict):
    """GET /api/v1/rulesets returns list of ruleset metadata."""
    resp = await client.get("/api/v1/rulesets", headers=auth_org_a["headers"])
    assert resp.status_code == 200
    data = resp.json()

    assert isinstance(data, list)
    assert len(data) >= 3

    ids = [r["id"] for r in data]
    assert "india-nbc-2016" in ids
    assert "up-bylaws" in ids
    assert "uttarakhand-bylaws" in ids

    sample = data[0]
    assert "id" in sample
    assert "name" in sample
    assert "jurisdiction" in sample
    assert "version" in sample
    assert "rule_count" in sample


@pytest.mark.asyncio
async def test_get_ruleset_by_id_endpoint(client: AsyncClient, auth_org_a: dict):
    """GET /api/v1/rulesets/{id} returns full ruleset with all rules."""
    resp = await client.get(
        "/api/v1/rulesets/india-nbc-2016", headers=auth_org_a["headers"]
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == "india-nbc-2016"
    assert "rules" in data
    assert len(data["rules"]) > 0

    # Non-existent ruleset returns 404
    resp_404 = await client.get(
        "/api/v1/rulesets/non-existent-ruleset", headers=auth_org_a["headers"]
    )
    assert resp_404.status_code == 404


@pytest.mark.asyncio
async def test_set_project_ruleset_endpoint(client: AsyncClient, auth_org_a: dict):
    """PUT /api/v1/projects/{id}/ruleset assigns ruleset to project."""
    project_id = await create_test_project(client, auth_org_a["headers"])

    # Assign UP Bylaws
    resp = await client.put(
        f"/api/v1/projects/{project_id}/ruleset",
        headers=auth_org_a["headers"],
        json={"ruleset_id": "up-bylaws"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ruleset_id"] == "up-bylaws"

    # Get project to verify persistence
    resp_proj = await client.get(
        f"/api/v1/projects/{project_id}",
        headers=auth_org_a["headers"],
    )
    assert resp_proj.status_code == 200
    assert resp_proj.json()["ruleset_id"] == "up-bylaws"

    # Assign invalid ruleset returns 404/400
    resp_bad = await client.put(
        f"/api/v1/projects/{project_id}/ruleset",
        headers=auth_org_a["headers"],
        json={"ruleset_id": "invalid-ruleset-xyz"},
    )
    assert resp_bad.status_code in (400, 404)


@pytest.mark.asyncio
async def test_ruleset_project_tenancy(
    client: AsyncClient, auth_org_a: dict, auth_org_b: dict
):
    """Org B cannot set ruleset on Org A's project (404 Not Found)."""
    project_id = await create_test_project(client, auth_org_a["headers"])

    resp = await client.put(
        f"/api/v1/projects/{project_id}/ruleset",
        headers=auth_org_b["headers"],
        json={"ruleset_id": "up-bylaws"},
    )
    assert resp.status_code == 404
