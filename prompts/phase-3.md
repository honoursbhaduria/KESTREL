# PHASE 3 — Plan Model, 2D Workspace & Review Engine

Read CLAUDE.md. Phases 1–2 are complete. This is Phase 3 of 6.

GOAL
The core of the product: a versioned Plan model, a 2D plan workspace, and a rule
engine that produces the Pass / Review / Fail checklist with click-to-highlight.
Plans in this phase come from hand-made fixtures (generation is Phase 4).

BACKEND
1. Plan schema (plans module) — exactly the shape in CLAUDE.md §2.2, Pydantic v2,
   millimetres. Add validators: room polygons valid and non-overlapping, openings
   fit inside their wall, walls connect at endpoints within tolerance.
2. Versioning:
   - Tables: plans (id, project_id, name, current_version), plan_versions (plan_id,
     version, parent_version, data JSONB, created_by: user|ai|solver, message).
   - Patches: a small typed set of operations, NOT free-form JSON patch:
     move_wall, set_wall_thickness, add_opening, move_opening, resize_opening,
     remove_opening, set_room_type, rename_room, split_room, merge_rooms.
     Each op is a Pydantic model with a pure apply(plan) -> plan function.
   - POST /plans/{id}/patches applies ops atomically → new version. Room polygons are
     recomputed from walls after wall edits (document how).
   - POST /plans/{id}/undo, POST /plans/{id}/redo, GET /plans/{id}/versions,
     GET /plans/{id}/diff?from=&to=.
3. Rule engine (rules module):
   - Checker registry: @checker("min_room_area") decorated pure functions
     (plan, envelope, params) -> list[Issue].
   - Implement checkers: min_room_area, min_room_width, min_ceiling_height,
     door_clear_width, corridor_clear_width, stair_riser_tread, window_to_floor_ratio
     (ventilation), inside_envelope, ground_coverage, far.
   - Issue: id, rule_id, clause, status (pass|review|fail), element_ids, measured,
     required, message. Rules with verified: false can only return review.
   - POST /plans/{id}/review → full pass, stores results per version.
   - Make the review incremental-friendly: checkers declare which element types they
     depend on, so later we can re-check only what a patch touched.
4. Seed fixtures: tests/fixtures/plans/ with 3 realistic plans (2BHK single floor,
   3BHK two floors, a plan with deliberate violations).

FRONTEND — Plan workspace (most important screen in the app)
- SVG plan view: walls (thickness drawn), rooms filled + labelled with name and area,
  doors with swing arcs, windows, stairs. Pan/zoom. Grid background. Level switcher.
- Dimensions: overall and per-room, toggleable. Live X/Y mm cursor readout.
- Select an element → properties panel (editable thickness, opening width, etc.)
  → each edit sends a patch.
- Drag a wall to move it (snap to 50 mm grid) → patch.
- Undo/redo (buttons + Cmd/Ctrl+Z).
- Review console panel styled like the landing page "Review · Project 0412" card:
  grouped by category, Pass/Review/Fail pills, counts at top ("3 open issues").
  Click an issue → highlight the elements on the plan and zoom to them; show
  measured vs required + clause.
- Version history panel: list versions with author (user/ai/solver) and message;
  click to view; restore.

TESTS
- Every patch op: apply, invalid input rejected, undo restores exact previous data.
- Every checker: one passing and one failing fixture.
- Review on the "violations" fixture returns exactly the expected issues.
- Property test (hypothesis) for move_wall: plan stays valid after random moves
  within bounds.

ACCEPTANCE CHECKLIST
[ ] Open a fixture plan, edit walls/openings, undo/redo, see versions
[ ] Run review, click an issue, see it highlighted with measured vs required
[ ] Screenshots of the workspace match landing page style
[ ] Tests + CI green
Summarize, list decisions and open questions, then stop.
