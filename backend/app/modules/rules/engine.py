"""Review Engine coordinating pure checkers, dependency filtering, and issue summaries (Phase 3)."""

import structlog
from pydantic import BaseModel, Field

from app.modules.planning.envelope import Envelope
from app.modules.plans.schemas import PlanData
from app.modules.rules.checkers import CHECKER_REGISTRY, Issue
from app.modules.rules.schemas import RulesetDefinition

logger = structlog.get_logger(__name__)


class ReviewResult(BaseModel):
    """Aggregate result of an architectural code compliance review."""

    issues: list[Issue] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


class ReviewEngine:
    """Coordinates execution of registered checkers against plans and statutory rulesets."""

    def review_plan(
        self,
        plan: PlanData,
        envelope: Envelope | None,
        ruleset: RulesetDefinition,
        modified_element_types: set[str] | None = None,
    ) -> ReviewResult:
        """Run statutory checks against plan, optionally filtering by modified element dependencies."""
        issues: list[Issue] = []
        evaluated_rules: set[str] = set()

        for rule in ruleset.rules:
            checker_meta = CHECKER_REGISTRY.get(rule.check)
            if not checker_meta:
                logger.warning(
                    "checker_not_implemented",
                    check=rule.check,
                    rule_id=rule.id,
                )
                continue

            # Dependency filtering for incremental reviews
            if modified_element_types is not None:
                deps = set(checker_meta["depends_on"])
                if not deps.intersection(modified_element_types):
                    # Skip checkers whose dependencies were not modified
                    continue

            checker_fn = checker_meta["fn"]
            try:
                rule_issues = checker_fn(plan, envelope, rule)
                issues.extend(rule_issues)
                evaluated_rules.add(rule.id)
            except Exception as e:
                logger.error("checker_execution_failed", rule_id=rule.id, error=str(e))

        pass_count = sum(1 for i in issues if i.status == "pass")
        review_count = sum(1 for i in issues if i.status == "review")
        fail_count = sum(1 for i in issues if i.status == "fail")

        summary = {
            "pass_count": pass_count,
            "review_count": review_count,
            "fail_count": fail_count,
            "total_issues": len(issues),
            "evaluated_rule_count": len(evaluated_rules),
        }

        return ReviewResult(issues=issues, summary=summary)
