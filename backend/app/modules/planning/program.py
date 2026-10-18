"""Architectural program models and statutory envelope feasibility verification."""

import copy
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.modules.planning.envelope import Envelope
from app.modules.rules.schemas import Ruleset


class RoomProgram(BaseModel):
    """Programmatic spatial requirement for a single room."""

    type: str = Field(description="Room category: living, bedroom, kitchen, dining, bathroom, stair, pooja, utility, store")
    name: str = Field(description="Architectural designation, e.g. Master Bedroom, Living Room, Powder Toilet")
    target_area_mm2: float = Field(gt=0, description="Target carpet area in square millimetres")
    min_width_mm: float = Field(default=2400.0, gt=0, description="Minimum allowable clear dimension in millimetres")
    level_hint: int = Field(default=1, ge=1, description="Target floor index: 1 for ground floor, 2 for first floor")
    needs_exterior_wall: bool = Field(default=True, description="Whether room requires natural light and ventilation on exterior wall")
    needs_attached_bath: bool = Field(default=False, description="Whether room requires en-suite bathroom connection")

    @property
    def target_area_sqm(self) -> float:
        return self.target_area_mm2 / 1_000_000.0


class Adjacency(BaseModel):
    """Topological relationship requirement between two functional spaces."""

    a: str
    b: str
    strength: Literal["must", "prefer", "avoid"] = "prefer"


class Preferences(BaseModel):
    """Architectural and orientation design preferences."""

    entrance_side: Literal["north", "east", "south", "west"] = "east"
    vastu: bool = True
    parking: bool = True
    style_notes: str = ""


class Program(BaseModel):
    """Structured architectural design program."""

    levels: int = Field(default=1, ge=1, le=5)
    rooms: list[RoomProgram] = Field(default_factory=list)
    adjacencies: list[Adjacency] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)

    @property
    def total_target_area_mm2(self) -> float:
        return sum(r.target_area_mm2 for r in self.rooms)

    @property
    def total_target_area_sqm(self) -> float:
        return self.total_target_area_mm2 / 1_000_000.0


class FeasibilityViolation(BaseModel):
    """Specific statutory envelope or code conflict."""

    category: str
    item: str
    measured: float
    required: float
    message: str


class FeasibilityResult(BaseModel):
    """Result of validating an architectural program against envelope and ruleset constraints."""

    is_feasible: bool
    total_proposed_area_sqm: float
    max_builtup_area_sqm: float
    ground_coverage_sqm: float
    max_coverage_sqm: float
    explanation: str | None = None
    suggested_program: Program | None = None
    violations: list[FeasibilityViolation] = Field(default_factory=list)


# Standard minimum requirements for rooms from statutory rulesets (e.g. NBC 2016)
STANDARD_ROOM_MINIMUMS: dict[str, dict[str, float]] = {
    "living": {"min_area_sqm": 9.5, "min_width_mm": 2400.0},
    "bedroom": {"min_area_sqm": 9.5, "min_width_mm": 2400.0},
    "kitchen": {"min_area_sqm": 5.0, "min_width_mm": 1800.0},
    "dining": {"min_area_sqm": 7.5, "min_width_mm": 2100.0},
    "bathroom": {"min_area_sqm": 1.8, "min_width_mm": 1200.0},
    "pooja": {"min_area_sqm": 2.0, "min_width_mm": 1200.0},
    "stair": {"min_area_sqm": 4.0, "min_width_mm": 1800.0},
    "utility": {"min_area_sqm": 2.0, "min_width_mm": 1200.0},
}


def validate_program_feasibility(
    program: Program,
    envelope: Envelope,
    ruleset: Ruleset | None = None,
) -> FeasibilityResult:
    """Verify that the proposed program conforms to legal buildable envelope (FAR, Coverage) and room minimums.
    If infeasible, provides a suggested scaled program rather than silently shrinking.
    """
    total_proposed_mm2 = program.total_target_area_mm2
    total_proposed_sqm = total_proposed_mm2 / 1_000_000.0
    max_builtup_sqm = envelope.max_builtup_mm2 / 1_000_000.0

    ground_rooms_mm2 = sum(r.target_area_mm2 for r in program.rooms if r.level_hint == 1)
    ground_coverage_sqm = ground_rooms_mm2 / 1_000_000.0
    max_coverage_sqm = envelope.max_coverage_mm2 / 1_000_000.0

    violations: list[FeasibilityViolation] = []
    explanations: list[str] = []

    # 1. FAR / Total built-up check
    # Add a tiny 0.1 sqm tolerance for rounding
    if total_proposed_sqm > max_builtup_sqm + 0.1:
        diff_sqm = total_proposed_sqm - max_builtup_sqm
        violations.append(
            FeasibilityViolation(
                category="far",
                item="Total Built-Up Area",
                measured=total_proposed_sqm,
                required=max_builtup_sqm,
                message=f"Total proposed area of {total_proposed_sqm:.1f} sqm exceeds maximum permissible built-up area of {max_builtup_sqm:.1f} sqm (FAR exceeded by {diff_sqm:.1f} sqm).",
            )
        )
        explanations.append(
            f"Proposed program of {total_proposed_sqm:.1f} sqm exceeds permissible built-up area of {max_builtup_sqm:.1f} sqm from FAR."
        )

    # 2. Ground coverage check
    if ground_coverage_sqm > max_coverage_sqm + 0.1:
        diff_cov = ground_coverage_sqm - max_coverage_sqm
        violations.append(
            FeasibilityViolation(
                category="coverage",
                item="Ground Coverage",
                measured=ground_coverage_sqm,
                required=max_coverage_sqm,
                message=f"Ground floor rooms ({ground_coverage_sqm:.1f} sqm) exceed maximum allowable ground coverage of {max_coverage_sqm:.1f} sqm by {diff_cov:.1f} sqm.",
            )
        )
        explanations.append(
            f"Ground floor footprint ({ground_coverage_sqm:.1f} sqm) exceeds maximum ground coverage ({max_coverage_sqm:.1f} sqm)."
        )

    # 3. Room minimum size statutory checks
    for r in program.rooms:
        req = STANDARD_ROOM_MINIMUMS.get(r.type.lower())
        if req:
            min_area_sqm = req["min_area_sqm"]
            r_area_sqm = r.target_area_sqm
            if r_area_sqm < min_area_sqm - 0.05:
                violations.append(
                    FeasibilityViolation(
                        category="room_minimum",
                        item=f"{r.name} Area",
                        measured=r_area_sqm,
                        required=min_area_sqm,
                        message=f"{r.name} area ({r_area_sqm:.2f} sqm) is below statutory minimum requirement of {min_area_sqm:.2f} sqm.",
                    )
                )
                explanations.append(f"{r.name} area ({r_area_sqm:.2f} sqm) is below minimum of {min_area_sqm:.2f} sqm.")

    is_feasible = len(violations) == 0
    suggested_program: Program | None = None

    if not is_feasible:
        # Build an adjusted suggested program
        # If FAR exceeded, proportionally scale down room areas so they sum to max_builtup_sqm (with safe margin)
        suggested_prog = copy.deepcopy(program)
        if total_proposed_sqm > max_builtup_sqm:
            scale_factor = (max_builtup_sqm * 0.95) / total_proposed_sqm
            for r in suggested_prog.rooms:
                min_sqm = STANDARD_ROOM_MINIMUMS.get(r.type.lower(), {}).get("min_area_sqm", 2.0)
                new_sqm = max(min_sqm, r.target_area_sqm * scale_factor)
                r.target_area_mm2 = new_sqm * 1_000_000.0

        # If individual rooms were below minimum, raise them to minimum
        for r in suggested_prog.rooms:
            req = STANDARD_ROOM_MINIMUMS.get(r.type.lower())
            if req and r.target_area_sqm < req["min_area_sqm"]:
                r.target_area_mm2 = req["min_area_sqm"] * 1_000_000.0

        suggested_program = suggested_prog

    return FeasibilityResult(
        is_feasible=is_feasible,
        total_proposed_area_sqm=round(total_proposed_sqm, 2),
        max_builtup_area_sqm=round(max_builtup_sqm, 2),
        ground_coverage_sqm=round(ground_coverage_sqm, 2),
        max_coverage_sqm=round(max_coverage_sqm, 2),
        explanation="; ".join(explanations) if explanations else None,
        suggested_program=suggested_program,
        violations=violations,
    )
