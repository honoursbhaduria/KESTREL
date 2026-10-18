"""Pydantic schemas for rulesets and rule definitions."""

from typing import Any, Literal

from pydantic import BaseModel, Field

RuleCategory = Literal[
    "setback",
    "far",
    "coverage",
    "height",
    "room_size",
    "width",
    "ventilation",
    "stair",
    "parking",
]

RuleSeverity = Literal["fail", "review"]


class RuleDefinition(BaseModel):
    """Definition of an architectural constraint rule loaded from YAML."""

    id: str = Field(..., description="Unique rule identifier")
    title: str = Field(..., description="Human-readable rule title")
    clause: str = Field(..., description="Source legal document and clause/section reference")
    category: RuleCategory = Field(..., description="Rule category")
    applies_to: str = Field(..., description="Target entity type (e.g. plot, building, room:habitable)")
    check: str = Field(..., description="Checker function identifier")
    params: dict[str, Any] = Field(default_factory=dict, description="Numerical parameters and thresholds")
    severity: RuleSeverity = Field("fail", description="Violation severity: fail or review")
    verified: bool = Field(..., description="Whether this rule is verified against official source text")
    notes: str = Field("", description="Source verification notes or TODO tags")


class RulesetDefinition(BaseModel):
    """Full ruleset including metadata and list of individual rules."""

    id: str
    name: str
    jurisdiction: str
    version: str
    description: str = ""
    rules: list[RuleDefinition] = Field(default_factory=list)


class RulesetSummary(BaseModel):
    """Lightweight metadata summary for ruleset picker and listing."""

    id: str
    name: str
    jurisdiction: str
    version: str
    description: str
    rule_count: int


class SetProjectRulesetRequest(BaseModel):
    """Request payload to set the governing ruleset for a project."""

    ruleset_id: str = Field(..., description="Identifier of the ruleset to associate")
