"""Pure functions for computing legally buildable envelopes from plot boundaries and rulesets.
Uses Shapely for robust 2D computational geometry.
"""

from typing import Any

import numpy as np
import structlog
from pydantic import BaseModel, Field
from shapely.geometry import Polygon

logger = structlog.get_logger(__name__)


class AppliedRuleRecord(BaseModel):
    """Citation of a rule applied during envelope derivation."""

    rule_id: str
    clause: str
    value: float | int | str
    verified: bool


class Envelope(BaseModel):
    """Computed legally buildable spatial envelope."""

    footprint_polygon: list[list[float]] = Field(
        default_factory=list,
        description="2D vertices of the buildable footprint in plan-local millimetres",
    )
    footprint_area_mm2: float = Field(
        ..., description="Buildable ground footprint area in square millimetres"
    )
    max_coverage_mm2: float = Field(
        ..., description="Maximum permissible ground coverage area in square millimetres"
    )
    max_builtup_mm2: float = Field(
        ..., description="Maximum permissible total built-up area in square millimetres (from FAR)"
    )
    max_height_mm: float = Field(
        ..., description="Maximum permissible building height in millimetres"
    )
    max_floors: int = Field(..., description="Maximum permissible above-ground floors")
    applied_rules: list[AppliedRuleRecord] = Field(default_factory=list)
    warning: str | None = None


def _ensure_ccw(poly: Polygon) -> Polygon:
    """Ensure polygon exterior vertices are oriented counter-clockwise."""
    from shapely import is_ccw

    if not is_ccw(poly.exterior):
        coords = list(poly.exterior.coords)[::-1]
        return Polygon(coords)
    return poly


def compute_envelope(
    plot_polygon: list[list[float]],
    road_sides: list[dict[str, Any]] | None = None,
    ruleset_params: dict[str, Any] | None = None,
) -> Envelope:
    """Compute buildable envelope for a plot polygon.

    Algorithm for irregular plots:
    1. Validates that the input plot polygon is a valid, closed 2D polygon with at least 3 vertices.
    2. Determines primary and secondary road-facing edges from `road_sides`.
    3. For quadrilateral or general irregular polygons, classifies edges into Front (road),
       Rear (furthest edge opposite primary road), and Side edges.
    4. Applies inward setbacks using a negative base buffer (poly.buffer(-min_setback, join_style='mitre'))
       combined with edge-specific setback exclusion strips subtracted via .difference(strip).
       This accurately handles non-convex corners (like L-shaped plots) and irregular multi-vertex
       boundaries without reflex clipping collapse or geometric anomalies.
    5. If the resulting footprint is degenerate or empty (e.g. plot dimensions smaller than sum of
       setbacks), returns footprint_area_mm2 = 0 and an explicit warning.
    6. Derives ground coverage and built-up areas (FAR) according to jurisdiction rules.
    """
    if len(plot_polygon) < 3:
        raise ValueError("Plot polygon must have at least 3 vertices.")

    poly = Polygon(plot_polygon)
    if not poly.is_valid:
        from shapely.validation import make_valid

        poly = make_valid(poly)
        if isinstance(poly, Polygon) and not poly.is_empty:
            pass
        else:
            raise ValueError("Plot polygon is topologically invalid (e.g. self-intersecting).")

    poly = _ensure_ccw(poly)
    plot_area_mm2 = poly.area
    plot_area_sqm = plot_area_mm2 / 1_000_000.0

    params = ruleset_params or {}
    ruleset_id = params.get("ruleset_id", "standard")

    # Determine setback distances based on plot area if tiered, or use explicit params
    front_setback = float(params.get("front_setback_mm", 3000.0))
    rear_setback = float(params.get("rear_setback_mm", 2000.0))
    side_setback = float(params.get("side_setback_mm", 1500.0))

    if "up-bylaws" in ruleset_id and "front_setback_mm" not in params:
        if plot_area_sqm <= 150.0:
            front_setback, rear_setback, side_setback = 2000.0, 1500.0, 1000.0
        elif plot_area_sqm <= 300.0:
            front_setback, rear_setback, side_setback = 3000.0, 2000.0, 1500.0
        elif plot_area_sqm <= 500.0:
            front_setback, rear_setback, side_setback = 4500.0, 3000.0, 2000.0
        else:
            front_setback, rear_setback, side_setback = 6000.0, 3000.0, 3000.0

    coverage_pct = float(params.get("ground_coverage_pct", 60.0))
    far = float(params.get("far", 1.5))
    max_height_mm = float(params.get("max_height_mm", 15000.0))
    max_floors = int(params.get("max_floors", 4))

    # Identify edges
    coords = list(poly.exterior.coords)
    # Exclude duplicated closure point if present
    if coords[0] == coords[-1]:
        coords = coords[:-1]
    n_vertices = len(coords)

    road_edges = set()
    if road_sides:
        for rs in road_sides:
            idx = int(rs.get("edge_index", 0)) % n_vertices
            road_edges.add(idx)
    else:
        road_edges.add(0)  # Default edge 0 as front

    primary_front_edge = min(road_edges)

    # Determine rear edge (opposite edge with furthest midpoint)
    v_a = np.array(coords[primary_front_edge])
    v_b = np.array(coords[(primary_front_edge + 1) % n_vertices])
    front_mid = (v_a + v_b) / 2.0

    furthest_edge = None
    max_dist = -1.0
    for i in range(n_vertices):
        if i in road_edges:
            continue
        e1 = np.array(coords[i])
        e2 = np.array(coords[(i + 1) % n_vertices])
        mid = (e1 + e2) / 2.0
        d = float(np.linalg.norm(mid - front_mid))
        if d > max_dist:
            max_dist = d
            furthest_edge = i

    rear_edge = (
        furthest_edge
        if furthest_edge is not None
        else (primary_front_edge + n_vertices // 2) % n_vertices
    )

    # Apply per-edge inward setbacks using negative buffer with edge-specific exclusion strips
    min_setback = min(front_setback, rear_setback, side_setback)
    footprint = poly.buffer(-min_setback, join_style="mitre")

    # If the base setback already shrinks the plot to nothing, it is too small
    if footprint.is_empty or footprint.area <= 1.0:
        footprint = Polygon()
    else:
        # For edges with setbacks greater than min_setback, subtract edge exclusion strips
        minx, miny, maxx, maxy = poly.bounds
        diag = float(np.hypot(maxx - minx, maxy - miny)) + 50000.0

        for i in range(n_vertices):
            if i in road_edges:
                d_setback = front_setback
            elif i == rear_edge:
                d_setback = rear_setback
            else:
                d_setback = side_setback

            extra_d = d_setback - min_setback
            if extra_d <= 1e-4:
                continue

            p1 = np.array(coords[i])
            p2 = np.array(coords[(i + 1) % n_vertices])
            edge_vec = p2 - p1
            edge_len = float(np.linalg.norm(edge_vec))
            if edge_len < 1e-4:
                continue

            unit_edge = edge_vec / edge_len
            inward_normal = np.array([-unit_edge[1], unit_edge[0]])

            # Build a strip covering the extra setback depth along this edge
            # Extend outwards by diag to ensure corners of this edge are clean
            strip_p1 = p1 - diag * 0.1 * unit_edge
            strip_p2 = p2 + diag * 0.1 * unit_edge
            strip_p3 = strip_p2 + d_setback * inward_normal
            strip_p4 = strip_p1 + d_setback * inward_normal
            # Also extend behind the edge to capture the full setback zone
            strip_p0a = strip_p1 - diag * 0.1 * inward_normal
            strip_p0b = strip_p2 - diag * 0.1 * inward_normal

            strip_poly = Polygon([strip_p0a, strip_p0b, strip_p3, strip_p4, strip_p0a])
            footprint = footprint.difference(strip_poly)

            if footprint.is_empty:
                break

    # Build applied rules citations
    applied_rules = [
        AppliedRuleRecord(
            rule_id=f"{ruleset_id}-front-setback",
            clause=params.get("front_clause", "Model Bylaws Table 4.1"),
            value=f"{front_setback:.0f} mm",
            verified=params.get("verified", True),
        ),
        AppliedRuleRecord(
            rule_id=f"{ruleset_id}-rear-setback",
            clause=params.get("rear_clause", "Model Bylaws Table 4.1"),
            value=f"{rear_setback:.0f} mm",
            verified=params.get("verified", True),
        ),
        AppliedRuleRecord(
            rule_id=f"{ruleset_id}-side-setback",
            clause=params.get("side_clause", "Model Bylaws Table 4.1"),
            value=f"{side_setback:.0f} mm",
            verified=params.get("verified", True),
        ),
        AppliedRuleRecord(
            rule_id=f"{ruleset_id}-max-coverage",
            clause=params.get("coverage_clause", "Model Bylaws Table 4.2"),
            value=f"{coverage_pct:.1f}%",
            verified=params.get("verified", True),
        ),
        AppliedRuleRecord(
            rule_id=f"{ruleset_id}-far",
            clause=params.get("far_clause", "Model Bylaws Table 4.2"),
            value=f"{far:.2f}",
            verified=params.get("verified", True),
        ),
        AppliedRuleRecord(
            rule_id=f"{ruleset_id}-height",
            clause=params.get("height_clause", "Model Bylaws Clause 4.8"),
            value=f"{max_height_mm:.0f} mm ({max_floors} floors)",
            verified=params.get("verified", True),
        ),
    ]

    max_coverage_mm2 = plot_area_mm2 * (coverage_pct / 100.0)
    max_builtup_mm2 = plot_area_mm2 * far

    if footprint.is_empty or footprint.area <= 1.0:
        return Envelope(
            footprint_polygon=[],
            footprint_area_mm2=0.0,
            max_coverage_mm2=max_coverage_mm2,
            max_builtup_mm2=max_builtup_mm2,
            max_height_mm=max_height_mm,
            max_floors=max_floors,
            applied_rules=applied_rules,
            warning="Buildable footprint is empty: plot dimensions are smaller than required setbacks.",
        )

    # If intersection created multiple parts, keep largest polygon
    if hasattr(footprint, "geoms"):
        footprint = max(footprint.geoms, key=lambda g: g.area)

    footprint_coords = [[round(pt[0], 2), round(pt[1], 2)] for pt in footprint.exterior.coords]

    return Envelope(
        footprint_polygon=footprint_coords,
        footprint_area_mm2=round(footprint.area, 2),
        max_coverage_mm2=round(max_coverage_mm2, 2),
        max_builtup_mm2=round(max_builtup_mm2, 2),
        max_height_mm=max_height_mm,
        max_floors=max_floors,
        applied_rules=applied_rules,
    )
