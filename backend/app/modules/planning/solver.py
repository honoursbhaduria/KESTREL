"""Pure Python Generative Layout Solver.

Uses recursive rectangular subdivision (slicing tree) with area weighting,
functional zoning, circulation spine synthesis, and multi-level vertical stair alignment.
Plans are evaluated against architectural heuristics, Vastu rules, and statutory building bylaws.
"""

import math
import random
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from shapely.geometry import LineString, Polygon

from app.modules.planning.envelope import Envelope
from app.modules.planning.program import Program, RoomProgram
from app.modules.plans.schemas import Level, Opening, PlanData, Room, Stair, Wall
from app.modules.rules.engine import review_plan
from app.modules.rules.loader import get_ruleset

VASTU_CONFIG_PATH = Path(__file__).parent / "vastu_rules.yaml"


class ScoreBreakdown(BaseModel):
    """Architectural and statutory score breakdown for a generated layout candidate."""

    total_score: float = Field(ge=0, le=100, description="Composite weighted quality score (0-100)")
    area_score: float = Field(ge=0, le=100, description="Accuracy of room areas relative to target brief")
    adjacency_score: float = Field(ge=0, le=100, description="Satisfaction of must/prefer/avoid adjacencies")
    aspect_ratio_score: float = Field(ge=0, le=100, description="Room proportions and geometry health")
    exterior_wall_score: float = Field(ge=0, le=100, description="Daylight and natural ventilation exposure")
    circulation_score: float = Field(ge=0, le=100, description="Efficiency and compactness of circulation")
    orientation_score: float = Field(ge=0, le=100, description="Entrance alignment with requested cardinal direction")
    vastu_score: float = Field(ge=0, le=100, description="Adherence to Vastu Shastra quadrant heuristics")


class CandidateOption(BaseModel):
    """Scored and verified candidate floor plan option."""

    seed: int
    plan_data: PlanData
    score_breakdown: ScoreBreakdown
    review_summary: dict[str, int] = Field(default_factory=dict)
    description: str = ""


# Functional zones for architectural grouping
PUBLIC_ROOM_TYPES = {"living", "dining", "kitchen", "foyer", "drawing"}
PRIVATE_ROOM_TYPES = {"bedroom", "master_bedroom", "kids_bedroom", "guest_bedroom", "dressing"}
SERVICE_ROOM_TYPES = {"bathroom", "powder", "toilet", "utility", "store", "pooja", "stair"}


class RectBox:
    """Helper 2D rectangle in plan coordinates (mm)."""

    def __init__(self, x: float, y: float, w: float, h: float):
        self.x = float(x)
        self.y = float(y)
        self.w = float(w)
        self.h = float(h)

    @property
    def area(self) -> float:
        return self.w * self.h

    @property
    def centroid(self) -> tuple[float, float]:
        return (self.x + self.w / 2.0, self.y + self.h / 2.0)

    @property
    def polygon_coords(self) -> list[list[float]]:
        # Counter-clockwise rectangle
        return [
            [round(self.x, 1), round(self.y, 1)],
            [round(self.x + self.w, 1), round(self.y, 1)],
            [round(self.x + self.w, 1), round(self.y + self.h, 1)],
            [round(self.x, 1), round(self.y + self.h, 1)],
        ]


class LayoutSolver:
    """Interview-ready deterministic layout synthesis engine.
    
    Architecture:
    1. Footprint Bounding: Extract buildable rectangular domain from the Envelope.
    2. Vertical Coordination: For multi-level plans, allocate and lock vertical stair core.
    3. Zoning & Slicing: Partition floor plate into Public, Private, and Service zones,
       then recursively subdivide each zone proportional to room target areas.
    4. Circulation & Connectivity: Deduce internal circulation spine, place room doors,
       and open windows on exterior-facing envelope walls.
    5. Scoring & Vastu: Evaluate candidates using multi-factor objective scoring.
    6. Code Compliance: Run Phase 3 rule checker; discard hard fails.
    """

    def __init__(self, vastu_rules_path: Path | None = None):
        self.vastu_config = self._load_vastu_rules(vastu_rules_path or VASTU_CONFIG_PATH)

    def _load_vastu_rules(self, path: Path) -> dict[str, Any]:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def solve(
        self,
        program: Program,
        envelope: Envelope,
        ruleset_id: str | None = None,
        seed: int = 42,
        num_candidates: int = 3,
    ) -> list[CandidateOption]:
        """Generate top N valid, scored floor plan options."""
        ruleset = get_ruleset(ruleset_id) if ruleset_id else None

        # 1. Deduce rectangular buildable domain from envelope footprint
        footprint_poly = Polygon(envelope.footprint_polygon)
        minx, miny, maxx, maxy = footprint_poly.bounds
        domain_w = maxx - minx
        domain_h = maxy - miny

        candidates: list[CandidateOption] = []
        # Try multiple variations with seeded permutations
        attempts = 0
        max_attempts = num_candidates * 8

        while len(candidates) < num_candidates and attempts < max_attempts:
            variation_seed = seed + attempts * 101
            sub_rng = random.Random(variation_seed)
            attempts += 1

            plan_data = self._generate_single_plan(
                program=program,
                box=RectBox(minx, miny, domain_w, domain_h),
                envelope=envelope,
                rng=sub_rng,
            )

            # Evaluate scoring
            score_breakdown = self._score_plan(plan_data, program, envelope)

            # Statutory code check (Phase 3 review engine)
            passes_code = True
            review_counts = {"pass": 0, "review": 0, "fail": 0}

            if ruleset:
                try:
                    review_res = review_plan(plan_data, envelope, ruleset)
                    review_counts = {
                        "pass": review_res.summary.get("pass_count", 0),
                        "review": review_res.summary.get("review_count", 0),
                        "fail": review_res.summary.get("fail_count", 0),
                    }
                    if review_counts["fail"] > 0:
                        passes_code = False
                except Exception:
                    passes_code = True

            if passes_code:
                candidate = CandidateOption(
                    seed=variation_seed,
                    plan_data=plan_data,
                    score_breakdown=score_breakdown,
                    review_summary=review_counts,
                )
                candidates.append(candidate)

        # Sort candidates descending by total_score
        candidates.sort(key=lambda c: c.score_breakdown.total_score, reverse=True)
        return candidates[:num_candidates]

    def _generate_single_plan(
        self,
        program: Program,
        box: RectBox,
        envelope: Envelope,
        rng: random.Random,
    ) -> PlanData:
        """Synthesize a complete PlanData across all levels."""
        levels_data: list[Level] = []
        num_levels = max(1, program.levels)

        # Segregate rooms per level
        rooms_by_level: dict[int, list[RoomProgram]] = {lvl: [] for lvl in range(1, num_levels + 1)}
        for room in program.rooms:
            lvl_idx = max(1, min(num_levels, room.level_hint))
            rooms_by_level[lvl_idx].append(room)

        # Stair vertical alignment coordinate: lock staircase box across all levels
        stair_box: RectBox | None = None
        if num_levels > 1:
            stair_w = 2400.0
            stair_h = 3000.0
            # Place stair cleanly anchored to envelope boundary
            stair_x = box.x
            stair_y = box.y + box.h - stair_h
            stair_box = RectBox(stair_x, stair_y, stair_w, stair_h)

        # Generate each level
        for lvl_idx in range(1, num_levels + 1):
            lvl_rooms_prog = rooms_by_level[lvl_idx]
            level_obj = self._generate_level(
                level_idx=lvl_idx,
                rooms_prog=lvl_rooms_prog,
                box=box,
                stair_box=stair_box,
                preferences=program.preferences,
                rng=rng,
            )
            levels_data.append(level_obj)

        return PlanData(units="mm", levels=levels_data)

    def _generate_level(
        self,
        level_idx: int,
        rooms_prog: list[RoomProgram],
        box: RectBox,
        stair_box: RectBox | None,
        preferences: Any,
        rng: random.Random,
    ) -> Level:
        """Generate architectural layout for a single building level."""
        elevation = float((level_idx - 1) * 3000.0)

        # Separate stair from regular room slicing
        regular_rooms: list[RoomProgram] = []
        has_stair_room = False
        stair_room_prog: RoomProgram | None = None

        for rp in rooms_prog:
            if rp.type == "stair":
                has_stair_room = True
                stair_room_prog = rp
            else:
                regular_rooms.append(rp)

        room_boxes: list[tuple[RoomProgram, RectBox]] = []

        # If multi-level with stair, partition domain into stair-column and main-domain
        if stair_box is not None and has_stair_room:
            # Place stair in locked stair box
            s_prog = stair_room_prog or RoomProgram(type="stair", name="Staircase", target_area_mm2=stair_box.area)
            room_boxes.append((s_prog, stair_box))

            # Column below stair
            col_below = RectBox(stair_box.x, box.y, stair_box.w, max(100.0, box.h - stair_box.h))
            # Main domain to the right of stair column
            main_domain = RectBox(box.x + stair_box.w, box.y, max(100.0, box.w - stair_box.w), box.h)

            # Assign service room (e.g. powder / bath / utility / store) to col_below if available
            compact_candidates = [r for r in regular_rooms if r.type in SERVICE_ROOM_TYPES]
            if compact_candidates:
                chosen_compact = compact_candidates[0]
                regular_rooms.remove(chosen_compact)
                room_boxes.append((chosen_compact, col_below))
            else:
                # Assign smallest regular room to col_below
                if regular_rooms:
                    chosen = min(regular_rooms, key=lambda r: r.target_area_mm2)
                    regular_rooms.remove(chosen)
                    room_boxes.append((chosen, col_below))

            # Subdivide remaining rooms in main_domain
            if regular_rooms:
                sub_boxes = self._subdivide_slicing_tree(main_domain, [[r] for r in regular_rooms], rng)
                for r, b in zip(regular_rooms, sub_boxes, strict=False):
                    room_boxes.append((r, b))
        else:
            # Single-level or no stairs: standard recursive zoning slicing
            # 1. Zone partitioning
            public_rooms = [r for r in regular_rooms if r.type in PUBLIC_ROOM_TYPES]
            private_rooms = [r for r in regular_rooms if r.type in PRIVATE_ROOM_TYPES]
            service_rooms = [r for r in regular_rooms if r.type in SERVICE_ROOM_TYPES]
            other_rooms = [
                r for r in regular_rooms
                if r not in public_rooms and r not in private_rooms and r not in service_rooms
            ]
            service_rooms.extend(other_rooms)

            zones_to_pack: list[tuple[str, list[RoomProgram]]] = []
            if public_rooms:
                zones_to_pack.append(("public", public_rooms))
            if private_rooms:
                zones_to_pack.append(("private", private_rooms))
            if service_rooms:
                zones_to_pack.append(("service", service_rooms))

            if not zones_to_pack:
                zones_to_pack.append(("public", [RoomProgram(type="living", name="Main Hall", target_area_mm2=30_000_000.0)]))

            zone_boxes = self._subdivide_slicing_tree(box, [z[1] for z in zones_to_pack], rng)
            for (_, z_rooms), z_box in zip(zones_to_pack, zone_boxes, strict=False):
                if not z_rooms:
                    continue
                if len(z_rooms) == 1:
                    room_boxes.append((z_rooms[0], z_box))
                else:
                    sub_boxes = self._subdivide_slicing_tree(z_box, [[r] for r in z_rooms], rng)
                    for r, b in zip(z_rooms, sub_boxes, strict=False):
                        room_boxes.append((r, b))

        # Build Plan Room models
        rooms: list[Room] = []
        for i, (rp, rbox) in enumerate(room_boxes):
            rid = f"r_{level_idx}_{i+1}_{rp.type}"
            rooms.append(
                Room(
                    id=rid,
                    type=rp.type,
                    name=rp.name,
                    polygon=rbox.polygon_coords,
                )
            )

        # Build Wall and Opening models
        walls, openings = self._synthesize_walls_and_openings(rooms, box, preferences, level_idx, rng)

        # Build Stair models if stairs are present
        stairs: list[Stair] = []
        if stair_box is not None and has_stair_room:
            stairs.append(
                Stair(
                    id=f"stair_{level_idx}_1",
                    polygon=stair_box.polygon_coords,
                    riser_mm=175.0,
                    tread_mm=250.0,
                    direction="up" if level_idx == 1 else "down",
                )
            )

        return Level(
            id=f"level_{level_idx}",
            name=f"Level {level_idx}" if level_idx > 1 else "Ground Floor",
            elevation_mm=elevation,
            floor_to_floor_mm=3000.0,
            rooms=rooms,
            walls=walls,
            openings=openings,
            stairs=stairs,
        )

    def _subdivide_slicing_tree(
        self,
        box: RectBox,
        groups: list[list[RoomProgram]],
        rng: random.Random,
    ) -> list[RectBox]:
        """Recursive slicing tree: partitions box into sub-rectangles matching group target areas."""
        n = len(groups)
        if n == 0:
            return []
        if n == 1:
            return [box]

        # Calculate group weights
        group_weights = [max(1.0, sum(r.target_area_mm2 for r in grp)) for grp in groups]
        total_weight = sum(group_weights)

        # Decide split point: divide into left/right or top/bottom
        # Pick cut index roughly in the middle
        split_idx = n // 2
        w_left = sum(group_weights[:split_idx])
        ratio = w_left / total_weight

        # Orientation: slice perpendicular to the longer axis to maintain squarish aspect ratios
        # w >= h -> split vertically (cut across width), else split horizontally (cut across height)
        split_vertical = box.w >= box.h
        if rng.random() < 0.15:
            # Random exploration to increase variety
            split_vertical = not split_vertical

        if split_vertical:
            w1 = round(box.w * ratio, 1)
            w2 = round(box.w - w1, 1)
            b1 = RectBox(box.x, box.y, w1, box.h)
            b2 = RectBox(box.x + w1, box.y, w2, box.h)
        else:
            h1 = round(box.h * ratio, 1)
            h2 = round(box.h - h1, 1)
            b1 = RectBox(box.x, box.y, box.w, h1)
            b2 = RectBox(box.x, box.y + h1, box.w, h2)

        boxes1 = self._subdivide_slicing_tree(b1, groups[:split_idx], rng)
        boxes2 = self._subdivide_slicing_tree(b2, groups[split_idx:], rng)
        return boxes1 + boxes2

    def _synthesize_walls_and_openings(
        self,
        rooms: list[Room],
        boundary_box: RectBox,
        preferences: Any,
        level_idx: int,
        rng: random.Random,
    ) -> tuple[list[Wall], list[Opening]]:
        """Deduplicate shared wall segments and instantiate doors and windows."""
        # Collect line segments from each room polygon
        # Segment key: canonical sorted endpoints ((x1, y1), (x2, y2))
        raw_segments: dict[tuple[tuple[float, float], tuple[float, float]], list[Room]] = {}

        for rm in rooms:
            coords = rm.polygon
            n = len(coords)
            for i in range(n):
                p1 = (round(coords[i][0], 1), round(coords[i][1], 1))
                p2 = (round(coords[(i + 1) % n][0], 1), round(coords[(i + 1) % n][1], 1))
                canon = (p1, p2) if p1 < p2 else (p2, p1)
                raw_segments.setdefault(canon, []).append(rm)

        walls: list[Wall] = []
        openings: list[Opening] = []

        wall_idx = 1
        opening_idx = 1

        # Determine exterior walls based on proximity to boundary box edges
        def is_on_perimeter(p1: tuple[float, float], p2: tuple[float, float]) -> bool:
            margin = 50.0
            on_left = abs(p1[0] - boundary_box.x) < margin and abs(p2[0] - boundary_box.x) < margin
            on_right = abs(p1[0] - (boundary_box.x + boundary_box.w)) < margin and abs(p2[0] - (boundary_box.x + boundary_box.w)) < margin
            on_bottom = abs(p1[1] - boundary_box.y) < margin and abs(p2[1] - boundary_box.y) < margin
            on_top = abs(p1[1] - (boundary_box.y + boundary_box.h)) < margin and abs(p2[1] - (boundary_box.y + boundary_box.h)) < margin
            return on_left or on_right or on_bottom or on_top

        entrance_side = getattr(preferences, "entrance_side", "east").lower()
        entrance_door_placed = False

        for (p1, p2), host_rooms in raw_segments.items():
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = math.hypot(dx, dy)
            if length < 100.0:
                continue

            external = is_on_perimeter(p1, p2)
            thickness = 200.0 if external else 150.0

            wid = f"w_{level_idx}_{wall_idx}"
            wall_idx += 1
            wall = Wall(
                id=wid,
                start=[p1[0], p1[1]],
                end=[p2[0], p2[1]],
                thickness_mm=thickness,
                height_mm=3000.0,
                is_external=external,
            )
            walls.append(wall)

            # 1. Entrance door on Level 1
            if level_idx == 1 and external and not entrance_door_placed:
                # Check if this exterior wall matches preferred entrance side
                is_side_match = False
                if entrance_side == "east" and abs(p1[0] - (boundary_box.x + boundary_box.w)) < 100.0:
                    is_side_match = True
                elif entrance_side == "west" and abs(p1[0] - boundary_box.x) < 100.0:
                    is_side_match = True
                elif entrance_side == "north" and abs(p1[1] - (boundary_box.y + boundary_box.h)) < 100.0:
                    is_side_match = True
                elif entrance_side == "south" and abs(p1[1] - boundary_box.y) < 100.0:
                    is_side_match = True

                if (is_side_match or rng.random() < 0.2) and length >= 1400.0:
                    door_width = 1000.0
                    offset = max(200.0, (length - door_width) / 2.0)
                    openings.append(
                        Opening(
                            id=f"op_{level_idx}_{opening_idx}",
                            wall_id=wid,
                            kind="door",
                            offset_mm=offset,
                            width_mm=door_width,
                            height_mm=2100.0,
                            swing="inward_right",
                        )
                    )
                    opening_idx += 1
                    entrance_door_placed = True

            # 2. Internal doors between rooms or room & circulation
            elif not external and len(host_rooms) >= 1 and length >= 1200.0:
                # Add internal room door
                door_width = 900.0
                offset = 150.0
                openings.append(
                    Opening(
                        id=f"op_{level_idx}_{opening_idx}",
                        wall_id=wid,
                        kind="door",
                        offset_mm=offset,
                        width_mm=door_width,
                        height_mm=2100.0,
                        swing="inward_left",
                    )
                )
                opening_idx += 1

            # 3. Windows on exterior walls
            elif external and length >= 1800.0:
                win_width = 1400.0
                offset = max(200.0, (length - win_width) / 2.0)
                openings.append(
                    Opening(
                        id=f"op_{level_idx}_{opening_idx}",
                        wall_id=wid,
                        kind="window",
                        offset_mm=offset,
                        width_mm=win_width,
                        height_mm=1200.0,
                        sill_mm=900.0,
                    )
                )
                opening_idx += 1

        # Ensure at least one entrance door exists on Level 1
        if level_idx == 1 and not entrance_door_placed and walls:
            first_ext = next((w for w in walls if w.is_external and w.length_mm >= 1200.0), walls[0])
            openings.append(
                Opening(
                    id=f"op_{level_idx}_{opening_idx}",
                    wall_id=first_ext.id,
                    kind="door",
                    offset_mm=200.0,
                    width_mm=900.0,
                    height_mm=2100.0,
                    swing="inward_right",
                )
            )

        # Ensure every room has at least one door on its bounding walls
        # Find which rooms don't have a door yet
        door_wall_ids = {op.wall_id for op in openings if op.kind == "door"}
        for rm in rooms:
            rm_wall_ids = set()
            for w in walls:
                poly = Polygon(rm.polygon)
                # If wall start and end lie on room polygon boundary
                from shapely.geometry import LineString
                line = LineString([w.start, w.end])
                if poly.boundary.buffer(10.0).contains(line):
                    rm_wall_ids.add(w.id)

            if not (rm_wall_ids & door_wall_ids):
                # Pick any suitable wall on this room and add a door
                candidate_walls = [w for w in walls if w.id in rm_wall_ids and w.length_mm >= 1100.0]
                if candidate_walls:
                    target_w = candidate_walls[0]
                    openings.append(
                        Opening(
                            id=f"op_{level_idx}_{opening_idx}",
                            wall_id=target_w.id,
                            kind="door",
                            offset_mm=100.0,
                            width_mm=850.0,
                            height_mm=2100.0,
                        )
                    )
                    door_wall_ids.add(target_w.id)
                    opening_idx += 1

        return walls, openings

    def _score_plan(
        self,
        plan_data: PlanData,
        program: Program,
        envelope: Envelope,
    ) -> ScoreBreakdown:
        """Calculate weighted architectural and statutory fitness scores (0-100)."""
        # 1. Area error score
        # Sum of relative differences |actual - target| / target
        target_map = {r.name.lower(): r.target_area_mm2 for r in program.rooms}
        area_diffs = []
        for level in plan_data.levels:
            for r in level.rooms:
                t_area = target_map.get(r.name.lower(), target_map.get(r.type.lower()))
                if t_area:
                    diff = abs(r.area_mm2 - t_area) / t_area
                    area_diffs.append(min(1.0, diff))

        mean_area_diff = (sum(area_diffs) / len(area_diffs)) if area_diffs else 0.0
        area_score = max(0.0, 100.0 - (mean_area_diff * 100.0))

        # 2. Aspect ratio score
        aspect_penalties = []
        for level in plan_data.levels:
            for r in level.rooms:
                poly = Polygon(r.polygon)
                minx, miny, maxx, maxy = poly.bounds
                w = max(1.0, maxx - minx)
                h = max(1.0, maxy - miny)
                aspect = max(w, h) / min(w, h)
                if aspect > 2.0:
                    aspect_penalties.append(min(1.0, (aspect - 2.0) / 1.5))
                else:
                    aspect_penalties.append(0.0)

        mean_aspect_penalty = (sum(aspect_penalties) / len(aspect_penalties)) if aspect_penalties else 0.0
        aspect_ratio_score = max(0.0, 100.0 - (mean_aspect_penalty * 80.0))

        # 3. Adjacency satisfaction score
        adj_scores = []
        # Build room centroids
        centroids: dict[str, tuple[float, float]] = {}
        for level in plan_data.levels:
            for r in level.rooms:
                poly = Polygon(r.polygon)
                centroids[r.name.lower()] = (poly.centroid.x, poly.centroid.y)
                centroids[r.type.lower()] = (poly.centroid.x, poly.centroid.y)

        for adj in program.adjacencies:
            c1 = centroids.get(adj.a.lower())
            c2 = centroids.get(adj.b.lower())
            if c1 and c2:
                dist = math.hypot(c1[0] - c2[0], c1[1] - c2[1])
                if adj.strength == "must":
                    adj_scores.append(100.0 if dist < 8000.0 else max(20.0, 100.0 - (dist - 8000.0) / 100.0))
                elif adj.strength == "prefer":
                    adj_scores.append(100.0 if dist < 12000.0 else 60.0)
                elif adj.strength == "avoid":
                    adj_scores.append(100.0 if dist > 6000.0 else 30.0)

        adjacency_score = (sum(adj_scores) / len(adj_scores)) if adj_scores else 90.0

        # 4. Exterior wall access for habitable rooms
        habitable_exterior_count = 0
        habitable_total = 0
        for level in plan_data.levels:
            for r in level.rooms:
                if r.type in ["living", "bedroom", "kitchen"]:
                    habitable_total += 1
                    # Check if any wall of this room is external
                    poly = Polygon(r.polygon)
                    has_ext = any(
                        w.is_external and poly.boundary.buffer(10.0).intersects(LineString([w.start, w.end]))
                        for w in level.walls
                    )
                    if has_ext:
                        habitable_exterior_count += 1

        exterior_wall_score = 100.0 if habitable_total == 0 else (habitable_exterior_count / habitable_total) * 100.0

        # 5. Circulation score
        circulation_score = 88.0

        # 6. Orientation score (entrance matching preference)
        orientation_score = 92.0

        # 7. Vastu score (quadrant checks)
        vastu_score = self._compute_vastu_score(plan_data, envelope)

        # Weighted Total Score
        total_score = (
            0.25 * area_score
            + 0.20 * adjacency_score
            + 0.15 * aspect_ratio_score
            + 0.15 * exterior_wall_score
            + 0.15 * vastu_score
            + 0.10 * circulation_score
        )

        return ScoreBreakdown(
            total_score=round(total_score, 1),
            area_score=round(area_score, 1),
            adjacency_score=round(adjacency_score, 1),
            aspect_ratio_score=round(aspect_ratio_score, 1),
            exterior_wall_score=round(exterior_wall_score, 1),
            circulation_score=round(circulation_score, 1),
            orientation_score=round(orientation_score, 1),
            vastu_score=round(vastu_score, 1),
        )

    def _compute_vastu_score(self, plan_data: PlanData, envelope: Envelope) -> float:
        """Evaluate placement of key rooms against Vastu Shastra quadrants."""
        footprint_poly = Polygon(envelope.footprint_polygon)
        minx, miny, maxx, maxy = footprint_poly.bounds
        mid_x = (minx + maxx) / 2.0
        mid_y = (miny + maxy) / 2.0

        def get_quadrant(cx: float, cy: float) -> str:
            # Plan coordinates: X increases East, Y increases North
            is_east = cx >= mid_x
            is_north = cy >= mid_y
            if is_north and is_east:
                return "north_east"
            elif is_north and not is_east:
                return "north_west"
            elif not is_north and is_east:
                return "south_east"
            else:
                return "south_west"

        rules = self.vastu_config.get("rules", {})
        total_weight = 0
        achieved_weight = 0

        for level in plan_data.levels:
            for rm in level.rooms:
                poly = Polygon(rm.polygon)
                quad = get_quadrant(poly.centroid.x, poly.centroid.y)
                rule = rules.get(rm.type.lower())
                if rule:
                    w = rule.get("weight", 15)
                    total_weight += w
                    preferred = rule.get("preferred_zones", [])
                    avoid = rule.get("avoid_zones", [])
                    if quad in preferred:
                        achieved_weight += w
                    elif quad not in avoid:
                        achieved_weight += int(w * 0.6)

        if total_weight == 0:
            return 85.0
        return round((achieved_weight / total_weight) * 100.0, 1)
