"""Pure rule engine checkers for architectural plan verification (Phase 3)."""

from typing import Any, Callable, Literal
import math
from pydantic import BaseModel, Field
from shapely.geometry import Point, Polygon

from app.modules.planning.envelope import Envelope
from app.modules.plans.schemas import PlanData, Room
from app.modules.rules.schemas import RuleDefinition


class Issue(BaseModel):
    """Specific architectural or regulatory issue discovered by a checker."""

    id: str
    rule_id: str
    clause: str
    category: str
    status: Literal["pass", "review", "fail"]
    element_ids: list[str] = Field(default_factory=list)
    measured: float | int | str
    required: float | int | str
    message: str


# Registry for checker functions
CHECKER_REGISTRY: dict[str, dict[str, Any]] = {}


def checker(name: str, depends_on: list[str] | None = None) -> Callable:
    """Decorator registering pure rule checker functions with dependency tracking."""

    def decorator(fn: Callable) -> Callable:
        CHECKER_REGISTRY[name] = {
            "fn": fn,
            "depends_on": depends_on or ["plan"],
        }
        return fn

    return decorator


def _status(rule: RuleDefinition, condition_met: bool) -> Literal["pass", "review", "fail"]:
    """Resolve issue status enforcing the invariant: unverified rules can only return 'review'."""
    if condition_met:
        return "pass"
    if not rule.verified:
        return "review"
    return "fail" if rule.severity == "fail" else "review"


@checker("min_room_area", depends_on=["room"])
def check_min_room_area(
    plan: PlanData, envelope: Envelope | None, rule: RuleDefinition
) -> list[Issue]:
    """Check that room areas comply with minimum statutory standards."""
    issues: list[Issue] = []
    params = rule.params
    target_type = params.get("room_type")
    min_area_sqm = float(params.get("min_area_sqm", 9.5))

    for lvl in plan.levels:
        for r in lvl.rooms:
            # If target_type specified, check matching type; otherwise check habitable rooms
            if target_type and r.type != target_type:
                continue
            if not target_type and r.type not in ["bedroom", "living", "habitable", "study"]:
                continue

            area_sqm = r.area_sqm
            passed = area_sqm >= (min_area_sqm - 0.05)
            st = _status(rule, passed)

            if not passed or st == "pass":
                issues.append(
                    Issue(
                        id=f"{rule.id}-{r.id}",
                        rule_id=rule.id,
                        clause=rule.clause,
                        category=rule.category,
                        status=st,
                        element_ids=[r.id],
                        measured=f"{area_sqm:.2f} sqm",
                        required=f"{min_area_sqm:.2f} sqm",
                        message=(
                            f"Room '{r.name}' area ({area_sqm:.2f} sqm) meets requirement ({min_area_sqm:.2f} sqm)."
                            if passed
                            else f"Room '{r.name}' area ({area_sqm:.2f} sqm) is below required minimum ({min_area_sqm:.2f} sqm)."
                        ),
                    )
                )
    return issues


@checker("min_room_width", depends_on=["room"])
def check_min_room_width(
    plan: PlanData, envelope: Envelope | None, rule: RuleDefinition
) -> list[Issue]:
    """Check that room clear width satisfies statutory minima."""
    issues: list[Issue] = []
    params = rule.params
    target_type = params.get("room_type", "kitchen")
    min_width_mm = float(params.get("min_width_mm", 1800.0))

    for lvl in plan.levels:
        for r in lvl.rooms:
            if target_type and r.type != target_type:
                continue

            # Compute bounding box dimension as width heuristic
            xs = [p[0] for p in r.polygon]
            ys = [p[1] for p in r.polygon]
            w = max(xs) - min(xs)
            h = max(ys) - min(ys)
            min_dim_mm = min(w, h)

            passed = min_dim_mm >= (min_width_mm - 5.0)
            st = _status(rule, passed)

            if not passed or st == "pass":
                issues.append(
                    Issue(
                        id=f"{rule.id}-{r.id}",
                        rule_id=rule.id,
                        clause=rule.clause,
                        category=rule.category,
                        status=st,
                        element_ids=[r.id],
                        measured=f"{min_dim_mm:.0f} mm",
                        required=f"{min_width_mm:.0f} mm",
                        message=(
                            f"Room '{r.name}' minimum dimension ({min_dim_mm:.0f} mm) meets standard ({min_width_mm:.0f} mm)."
                            if passed
                            else f"Room '{r.name}' minimum dimension ({min_dim_mm:.0f} mm) is narrower than required ({min_width_mm:.0f} mm)."
                        ),
                    )
                )
    return issues


@checker("min_ceiling_height", depends_on=["level"])
def check_min_ceiling_height(
    plan: PlanData, envelope: Envelope | None, rule: RuleDefinition
) -> list[Issue]:
    """Check that floor-to-floor height satisfies minimum clear ceiling height."""
    issues: list[Issue] = []
    min_height_mm = float(rule.params.get("min_height_mm", 2750.0))

    for lvl in plan.levels:
        h = lvl.floor_to_floor_mm
        passed = h >= (min_height_mm - 5.0)
        st = _status(rule, passed)

        issues.append(
            Issue(
                id=f"{rule.id}-{lvl.id}",
                rule_id=rule.id,
                clause=rule.clause,
                category=rule.category,
                status=st,
                element_ids=[lvl.id],
                measured=f"{h:.0f} mm",
                required=f"{min_height_mm:.0f} mm",
                message=(
                    f"Level '{lvl.name}' ceiling height ({h:.0f} mm) meets standard ({min_height_mm:.0f} mm)."
                    if passed
                    else f"Level '{lvl.name}' ceiling height ({h:.0f} mm) is below statutory minimum ({min_height_mm:.0f} mm)."
                ),
            )
        )
    return issues


@checker("door_clear_width", depends_on=["opening"])
def check_door_clear_width(
    plan: PlanData, envelope: Envelope | None, rule: RuleDefinition
) -> list[Issue]:
    """Check door opening widths meet egress and accessibility thresholds."""
    issues: list[Issue] = []
    min_width_mm = float(rule.params.get("min_door_width_mm", 750.0))

    for lvl in plan.levels:
        for op in lvl.openings:
            if op.kind != "door":
                continue
            passed = op.width_mm >= (min_width_mm - 5.0)
            st = _status(rule, passed)

            if not passed or st == "pass":
                issues.append(
                    Issue(
                        id=f"{rule.id}-{op.id}",
                        rule_id=rule.id,
                        clause=rule.clause,
                        category=rule.category,
                        status=st,
                        element_ids=[op.id],
                        measured=f"{op.width_mm:.0f} mm",
                        required=f"{min_width_mm:.0f} mm",
                        message=(
                            f"Door '{op.id}' clear width ({op.width_mm:.0f} mm) meets egress minimum ({min_width_mm:.0f} mm)."
                            if passed
                            else f"Door '{op.id}' clear width ({op.width_mm:.0f} mm) is narrower than minimum ({min_width_mm:.0f} mm)."
                        ),
                    )
                )
    return issues


@checker("corridor_clear_width", depends_on=["room"])
def check_corridor_clear_width(
    plan: PlanData, envelope: Envelope | None, rule: RuleDefinition
) -> list[Issue]:
    """Check corridor clear width."""
    issues: list[Issue] = []
    min_corridor_mm = float(rule.params.get("min_corridor_width_mm", 1000.0))

    for lvl in plan.levels:
        for r in lvl.rooms:
            if r.type != "corridor":
                continue
            xs = [p[0] for p in r.polygon]
            ys = [p[1] for p in r.polygon]
            w = min(max(xs) - min(xs), max(ys) - min(ys))
            passed = w >= (min_corridor_mm - 5.0)
            st = _status(rule, passed)

            issues.append(
                Issue(
                    id=f"{rule.id}-{r.id}",
                    rule_id=rule.id,
                    clause=rule.clause,
                    category=rule.category,
                    status=st,
                    element_ids=[r.id],
                    measured=f"{w:.0f} mm",
                    required=f"{min_corridor_mm:.0f} mm",
                    message=(
                        f"Corridor '{r.name}' width ({w:.0f} mm) meets minimum ({min_corridor_mm:.0f} mm)."
                        if passed
                        else f"Corridor '{r.name}' width ({w:.0f} mm) is below minimum ({min_corridor_mm:.0f} mm)."
                    ),
                )
            )
    return issues


@checker("stair_riser_tread", depends_on=["stair"])
def check_stair_riser_tread(
    plan: PlanData, envelope: Envelope | None, rule: RuleDefinition
) -> list[Issue]:
    """Check that stair risers do not exceed max and treads meet min."""
    issues: list[Issue] = []
    max_riser_mm = float(rule.params.get("max_riser_mm", 190.0))
    min_tread_mm = float(rule.params.get("min_tread_mm", 250.0))

    for lvl in plan.levels:
        for st in lvl.stairs:
            riser_ok = st.riser_mm <= (max_riser_mm + 1.0)
            tread_ok = st.tread_mm >= (min_tread_mm - 1.0)
            passed = riser_ok and tread_ok
            status_val = _status(rule, passed)

            issues.append(
                Issue(
                    id=f"{rule.id}-{st.id}",
                    rule_id=rule.id,
                    clause=rule.clause,
                    category=rule.category,
                    status=status_val,
                    element_ids=[st.id],
                    measured=f"Riser: {st.riser_mm:.0f} mm, Tread: {st.tread_mm:.0f} mm",
                    required=f"Riser <= {max_riser_mm:.0f} mm, Tread >= {min_tread_mm:.0f} mm",
                    message=(
                        f"Stair '{st.id}' proportions are code-compliant."
                        if passed
                        else f"Stair '{st.id}' violates limits (Riser {st.riser_mm:.0f}mm vs max {max_riser_mm:.0f}mm, Tread {st.tread_mm:.0f}mm vs min {min_tread_mm:.0f}mm)."
                    ),
                )
            )
    return issues


@checker("window_to_floor_ratio", depends_on=["room", "opening"])
def check_window_to_floor_ratio(
    plan: PlanData, envelope: Envelope | None, rule: RuleDefinition
) -> list[Issue]:
    """Check that aggregate window area provides at least 1/8 (12.5%) ventilation area."""
    issues: list[Issue] = []
    min_ratio = float(rule.params.get("min_ratio", 0.125))

    for lvl in plan.levels:
        for r in lvl.rooms:
            if r.type not in ["bedroom", "living", "habitable", "study", "kitchen"]:
                continue
            r_poly = Polygon(r.polygon)
            room_area_sqm = r_poly.area / 1_000_000.0

            # Find windows associated with this room or its boundaries
            total_window_area_sqm = 0.0
            window_ids = []
            for op in lvl.openings:
                if op.kind == "window":
                    # Check if window host wall is near room
                    wall = next((w for w in lvl.walls if w.id == op.wall_id), None)
                    if wall:
                        dx = wall.end[0] - wall.start[0]
                        dy = wall.end[1] - wall.start[1]
                        wall_len = math.hypot(dx, dy)
                        if wall_len > 0:
                            win_center = op.offset_mm + op.width_mm / 2.0
                            win_x = wall.start[0] + (dx / wall_len) * win_center
                            win_y = wall.start[1] + (dy / wall_len) * win_center
                            if r_poly.distance(Point(win_x, win_y)) < 400.0:
                                total_window_area_sqm += (op.width_mm * op.height_mm) / 1_000_000.0
                                window_ids.append(op.id)

            ratio = total_window_area_sqm / max(room_area_sqm, 0.01)
            passed = ratio >= (min_ratio - 0.01)
            st = _status(rule, passed)

            if not passed or st == "pass":
                issues.append(
                    Issue(
                        id=f"{rule.id}-{r.id}",
                        rule_id=rule.id,
                        clause=rule.clause,
                        category=rule.category,
                        status=st,
                        element_ids=[r.id] + window_ids,
                        measured=f"{ratio * 100:.1f}% ({total_window_area_sqm:.2f} sqm)",
                        required=f"{min_ratio * 100:.1f}% ({room_area_sqm * min_ratio:.2f} sqm)",
                        message=(
                            f"Room '{r.name}' natural ventilation ({ratio * 100:.1f}%) satisfies minimum ({min_ratio * 100:.1f}%)."
                            if passed
                            else f"Room '{r.name}' natural window ventilation ({ratio * 100:.1f}%) is below statutory minimum ({min_ratio * 100:.1f}%)."
                        ),
                    )
                )
    return issues


@checker("inside_envelope", depends_on=["envelope", "room", "wall"])
def check_inside_envelope(
    plan: PlanData, envelope: Envelope | None, rule: RuleDefinition
) -> list[Issue]:
    """Check that ground level building rooms and walls do not protrude outside the envelope."""
    issues: list[Issue] = []
    if not envelope or not envelope.footprint_polygon:
        return issues

    footprint_poly = Polygon(envelope.footprint_polygon)
    ground_level = plan.levels[0] if plan.levels else None
    if not ground_level:
        return issues

    protruding_rooms = []
    for r in ground_level.rooms:
        r_poly = Polygon(r.polygon)
        # Check if room extends outside envelope footprint by more than 50mm tolerance
        diff = r_poly.difference(footprint_poly)
        if diff.area > 5000.0:  # > 0.005 sqm protrusion
            protruding_rooms.append(r.id)

    passed = len(protruding_rooms) == 0
    st = _status(rule, passed)

    issues.append(
        Issue(
            id=f"{rule.id}-ground-boundary",
            rule_id=rule.id,
            clause=rule.clause,
            category=rule.category,
            status=st,
            element_ids=protruding_rooms,
            measured=f"{len(protruding_rooms)} elements outside" if not passed else "0 elements outside",
            required="All elements inside envelope",
            message=(
                "All ground floor rooms and external walls are strictly contained within the buildable envelope."
                if passed
                else f"Plan contains {len(protruding_rooms)} room(s) protruding outside the legally buildable envelope."
            ),
        )
    )
    return issues


@checker("ground_coverage", depends_on=["envelope", "room"])
def check_ground_coverage(
    plan: PlanData, envelope: Envelope | None, rule: RuleDefinition
) -> list[Issue]:
    """Check that ground floor coverage does not exceed maximum permissible coverage."""
    issues: list[Issue] = []
    if not envelope:
        return issues

    ground_level = plan.levels[0] if plan.levels else None
    if not ground_level:
        return issues

    ground_area_sqm = sum(r.area_sqm for r in ground_level.rooms)
    max_coverage_sqm = envelope.max_coverage_mm2 / 1_000_000.0

    passed = ground_area_sqm <= (max_coverage_sqm + 0.1)
    st = _status(rule, passed)

    issues.append(
        Issue(
            id=f"{rule.id}-coverage",
            rule_id=rule.id,
            clause=rule.clause,
            category=rule.category,
            status=st,
            element_ids=[ground_level.id],
            measured=f"{ground_area_sqm:.1f} sqm",
            required=f"<= {max_coverage_sqm:.1f} sqm",
            message=(
                f"Ground coverage ({ground_area_sqm:.1f} sqm) satisfies permissible limit ({max_coverage_sqm:.1f} sqm)."
                if passed
                else f"Ground coverage ({ground_area_sqm:.1f} sqm) exceeds permissible limit ({max_coverage_sqm:.1f} sqm)."
            ),
        )
    )
    return issues


@checker("far", depends_on=["envelope", "room", "level"])
def check_far(
    plan: PlanData, envelope: Envelope | None, rule: RuleDefinition
) -> list[Issue]:
    """Check that total built-up area across all levels does not exceed FAR limits."""
    issues: list[Issue] = []
    if not envelope:
        return issues

    total_builtup_sqm = sum(r.area_sqm for lvl in plan.levels for r in lvl.rooms)
    max_builtup_sqm = envelope.max_builtup_mm2 / 1_000_000.0

    passed = total_builtup_sqm <= (max_builtup_sqm + 0.1)
    st = _status(rule, passed)

    issues.append(
        Issue(
            id=f"{rule.id}-far",
            rule_id=rule.id,
            clause=rule.clause,
            category=rule.category,
            status=st,
            element_ids=[lvl.id for lvl in plan.levels],
            measured=f"{total_builtup_sqm:.1f} sqm",
            required=f"<= {max_builtup_sqm:.1f} sqm",
            message=(
                f"Total built-up area ({total_builtup_sqm:.1f} sqm) complies with FAR cap ({max_builtup_sqm:.1f} sqm)."
                if passed
                else f"Total built-up area ({total_builtup_sqm:.1f} sqm) exceeds FAR cap ({max_builtup_sqm:.1f} sqm)."
            ),
        )
    )
    return issues
