"""API router for rulesets and rule RAG search."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.session import get_db_session
from app.modules.auth.dependencies import AuthContext, get_current_auth_context
from app.modules.rules.loader import get_ruleset, list_rulesets_summary
from app.modules.rules.rag import SearchResult, search_rules
from app.modules.rules.schemas import RulesetDefinition, RulesetSummary

router = APIRouter(tags=["rules"])


@router.get("/rulesets", response_model=list[RulesetSummary])
async def list_rulesets(
    auth: AuthContext = Depends(get_current_auth_context),
) -> list[RulesetSummary]:
    """List all available jurisdiction building rulesets."""
    return list_rulesets_summary()


@router.get("/rulesets/{ruleset_id}", response_model=RulesetDefinition)
async def get_ruleset_detail(
    ruleset_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
) -> RulesetDefinition:
    """Retrieve full ruleset definition including all rules, clauses, and parameters."""
    ruleset = get_ruleset(ruleset_id)
    if not ruleset:
        raise NotFoundError(f"Ruleset '{ruleset_id}' not found")
    return ruleset


@router.get("/rules/search", response_model=list[SearchResult])
async def search_rule_citations(
    q: str = Query(default="", description="Search query for architectural clauses and rules"),
    limit: int = Query(default=5, ge=1, le=20),
    auth: AuthContext = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[SearchResult]:
    """Semantic and lexical RAG search across ingested building code regulations."""
    if not q.strip():
        return []
    return await search_rules(query=q, limit=limit, session=session)
