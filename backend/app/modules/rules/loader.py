"""Loader for rulesets defined in YAML files.
Validates each file with Pydantic schemas.
"""

from pathlib import Path
from typing import Any

import structlog
import yaml

from app.modules.rules.schemas import RulesetDefinition, RulesetSummary

logger = structlog.get_logger(__name__)

_RULESETS_CACHE: dict[str, RulesetDefinition] = {}


def get_rules_dir() -> Path:
    """Locate the root rules directory."""
    # Try repository root (3 levels up from backend/app/modules/rules)
    repo_rules = Path(__file__).resolve().parents[3] / "rules"
    if repo_rules.is_dir():
        return repo_rules

    # Fallback to current working directory or relative path
    cwd_rules = Path.cwd() / "rules"
    if cwd_rules.is_dir():
        return cwd_rules

    # If backend directory is CWD
    parent_rules = Path.cwd().parent / "rules"
    if parent_rules.is_dir():
        return parent_rules

    return repo_rules


def load_ruleset_from_file(file_path: Path) -> RulesetDefinition:
    """Parse and validate a single ruleset YAML file."""
    with open(file_path, encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Ruleset file {file_path} did not contain a YAML mapping.")

    return RulesetDefinition.model_validate(data)


def load_all_rulesets(force_reload: bool = False) -> list[RulesetDefinition]:
    """Scan rules directory and load all valid rulesets into cache."""
    global _RULESETS_CACHE
    if _RULESETS_CACHE and not force_reload:
        return list(_RULESETS_CACHE.values())

    rules_dir = get_rules_dir()
    loaded: dict[str, RulesetDefinition] = {}

    if not rules_dir.exists():
        logger.warning("rules_dir_not_found", path=str(rules_dir))
        return []

    for yaml_path in sorted(rules_dir.glob("*/*.yaml")):
        try:
            ruleset = load_ruleset_from_file(yaml_path)
            loaded[ruleset.id] = ruleset
            logger.info(
                "ruleset_loaded", id=ruleset.id, count=len(ruleset.rules), path=str(yaml_path)
            )
        except Exception as e:
            logger.error("ruleset_load_error", path=str(yaml_path), error=str(e))
            raise

    _RULESETS_CACHE = loaded
    return list(loaded.values())


def get_ruleset(ruleset_id: str) -> RulesetDefinition | None:
    """Retrieve a single ruleset by ID."""
    if not _RULESETS_CACHE:
        load_all_rulesets()
    return _RULESETS_CACHE.get(ruleset_id)


def list_rulesets_summary() -> list[RulesetSummary]:
    """Return lightweight summaries for all loaded rulesets."""
    rulesets = load_all_rulesets()
    return [
        RulesetSummary(
            id=r.id,
            name=r.name,
            jurisdiction=r.jurisdiction,
            version=r.version,
            description=r.description,
            rule_count=len(r.rules),
        )
        for r in rulesets
    ]
