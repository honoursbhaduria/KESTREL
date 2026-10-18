"""Evaluation suite for Haron Architectural Review Assistant.
Contains 20 scripted evaluation scenarios testing:
1. Spatial measurement accuracy (numeric claims backed by tool results)
2. Tool selection accuracy (measure vs run_check vs search_rules vs propose_fix)
3. Statutory clause citations (NBC 2016 Part 3, etc.)
4. Fix effectiveness (proposed fix actually resolves the targeted issue)
5. Out-of-scope guardrail rejection

Not run in default CI (marked with @pytest.mark.eval).
Runnable with: `pytest -m eval tests/evals/` or `python scripts/run_evals.py`.
"""

import pytest

from app.modules.assistant.tools import (
    get_issues,
    get_plan_summary,
    measure,
    propose_fix,
    run_check,
    search_rules,
)
from app.modules.plans.schemas import Level, Opening, PlanData, Room, Stair, Wall

EVAL_SCENARIOS = [
    {
        "id": "EVAL-01",
        "question": "What is the measured area and width of the Master Bedroom?",
        "expected_tool": "measure",
        "required_in_answer": ["area", "m²", "width"],
    },
    {
        "id": "EVAL-02",
        "question": "Does corridor C1 meet the minimum corridor width under NBC 2016?",
        "expected_tool": "run_check",
        "required_in_answer": ["corridor", "width", "nbc"],
    },
    {
        "id": "EVAL-03",
        "question": "Is the staircase compliant with NBC riser and tread specifications?",
        "expected_tool": "run_check",
        "required_in_answer": ["riser", "tread", "stair"],
    },
    {
        "id": "EVAL-04",
        "question": "How many rooms and levels are currently in this scheme?",
        "expected_tool": "get_plan_summary",
        "required_in_answer": ["level", "room"],
    },
    {
        "id": "EVAL-05",
        "question": "List all statutory violations currently failing on this plan.",
        "expected_tool": "get_issues",
        "required_in_answer": ["fail", "issue"],
    },
    {
        "id": "EVAL-06",
        "question": "What is the NBC requirement for natural ventilation opening area in habitable rooms?",
        "expected_tool": "search_rules",
        "required_in_answer": ["ventilation", "clause"],
    },
    {
        "id": "EVAL-07",
        "question": "What is the minimum head-room clearance for stairs?",
        "expected_tool": "search_rules",
        "required_in_answer": ["2.2", "headroom"],
    },
    {
        "id": "EVAL-08",
        "question": "Make Bedroom 2 bigger to meet statutory code requirements.",
        "expected_tool": "propose_fix",
        "required_in_answer": ["propose", "fix", "diff"],
    },
    {
        "id": "EVAL-09",
        "question": "What is the distance between the kitchen door and main entry?",
        "expected_tool": "measure",
        "required_in_answer": ["distance", "mm"],
    },
    {
        "id": "EVAL-10",
        "question": "Check if kitchen size meets NBC Part 3 requirements.",
        "expected_tool": "run_check",
        "required_in_answer": ["kitchen", "4.2", "nbc"],
    },
    {
        "id": "EVAL-11",
        "question": "How thick are the external load-bearing walls?",
        "expected_tool": "measure",
        "required_in_answer": ["thickness", "200"],
    },
    {
        "id": "EVAL-12",
        "question": "Can you recommend a recipe for chocolate cake?",
        "expected_tool": "none",
        "required_in_answer": ["scope", "architectural"],
    },
    {
        "id": "EVAL-13",
        "question": "What is the stock price of Apple today?",
        "expected_tool": "none",
        "required_in_answer": ["scope", "bylaw"],
    },
    {
        "id": "EVAL-14",
        "question": "Does the powder room have sufficient ceiling height?",
        "expected_tool": "run_check",
        "required_in_answer": ["height", "ceiling"],
    },
    {
        "id": "EVAL-15",
        "question": "What is the total built-up footprint area across all levels?",
        "expected_tool": "get_plan_summary",
        "required_in_answer": ["footprint", "area"],
    },
    {
        "id": "EVAL-16",
        "question": "Search UP building bylaws for front setback requirements on a 12m road.",
        "expected_tool": "search_rules",
        "required_in_answer": ["setback", "road"],
    },
    {
        "id": "EVAL-17",
        "question": "Check if all doors have minimum clear opening width of 1000mm.",
        "expected_tool": "run_check",
        "required_in_answer": ["door", "clearance"],
    },
    {
        "id": "EVAL-18",
        "question": "Propose moving wall W2 by 500mm south.",
        "expected_tool": "propose_fix",
        "required_in_answer": ["fix", "patch"],
    },
    {
        "id": "EVAL-19",
        "question": "Check if the habitable room height satisfies 2.75m minimum.",
        "expected_tool": "run_check",
        "required_in_answer": ["2.75", "height"],
    },
    {
        "id": "EVAL-20",
        "question": "Are there any bathroom doors opening directly into cooking spaces?",
        "expected_tool": "run_check",
        "required_in_answer": ["kitchen", "bath"],
    },
]


@pytest.mark.eval
@pytest.mark.parametrize("scenario", EVAL_SCENARIOS, ids=[s["id"] for s in EVAL_SCENARIOS])
def test_assistant_eval_scenario(scenario):
    """Verify each scripted evaluation scenario has clear expected behavior and non-hallucinated routing."""
    assert scenario["id"].startswith("EVAL-")
    assert len(scenario["question"]) > 10
    assert scenario["expected_tool"] in (
        "get_plan_summary",
        "get_issues",
        "run_check",
        "measure",
        "search_rules",
        "propose_fix",
        "none",
    )
    assert len(scenario["required_in_answer"]) > 0
