# PHASE 2 — Plot, Rulesets & Buildable Envelope

Read CLAUDE.md. Phases 1 is complete. This is Phase 2 of 6.

GOAL
Architect draws the plot, picks a jurisdiction, and sees the legally buildable
envelope with every constraint explained and cited.

BACKEND
1. plots (projects module): one plot per project.
   - Fields: boundary (PostGIS Polygon, stored in a local metric projection, mm),
     original geo boundary (WGS84) if drawn on map, north_angle_deg, road_sides
     (list of edge indices + road width), plot_area_mm2 (computed).
   - PUT /projects/{id}/plot — validate: polygon closed, non-self-intersecting,
     at least 3 vertices, area within sane bounds. Reject with clear errors.
   - Support input two ways: polygon drawn on map, or simple rectangle by width × depth.
2. rules module — rulesets as data:
   - Loader for rules/<jurisdiction>/<version>.yaml validated by Pydantic.
   - Rule fields: id, title, clause (document + section), category (setback, far,
     coverage, height, room_size, width, ventilation, stair, parking), applies_to,
     check (checker name), params, severity (fail|review), verified (bool), notes.
   - Seed rulesets: india-nbc-2016 (room minimums, widths, heights, stairs,
     ventilation) and up-bylaws + uttarakhand-bylaws (setbacks by plot size/road
     width, FAR, ground coverage, max height).
   - DO NOT INVENT NUMBERS. If you don't have the document text, write the rule with
     verified: false and notes: "TODO: source". List every unverified rule in your
     final summary so I can fill them from the official PDFs.
   - GET /rulesets, GET /rulesets/{id}; PUT /projects/{id}/ruleset.
3. Envelope computation (planning module, pure functions, Shapely):
   - Inputs: plot polygon, road sides, ruleset params.
   - Steps: apply per-side setbacks (front/rear/side, which can depend on plot area
     and road width) → buildable footprint polygon; max ground coverage area;
     max total built-up area from FAR; max height / max floors.
   - Output: Envelope {footprint_polygon, max_coverage_mm2, max_builtup_mm2,
     max_height_mm, max_floors, applied_rules: [{rule_id, clause, value, verified}]}.
   - GET /projects/{id}/envelope (computed, cached until plot/ruleset changes).
   - Handle irregular (non-rectangular) plots. Document the approach in a docstring.
4. Rule RAG for explanations (not for decisions):
   - Table rule_chunks with pgvector embeddings; ingestion script that takes the source
     PDFs from rules/sources/, chunks them, stores clause references.
   - GET /rules/search?q= returns top chunks with document + section.
   - If I haven't put PDFs in rules/sources/ yet, build the pipeline and test it with
     a small sample text file.

FRONTEND
- Project → Plot screen: map (MapLibre or Leaflet, OSM tiles) to draw a polygon OR a
  width × depth form. Edit vertices, mark road-facing edges, set north arrow.
- Live dimension labels on edges in mm, CoordLabel readouts on hover (landing page
  style), plot area display.
- Ruleset picker.
- Envelope view: plot outline, setback lines labelled with distances, buildable
  footprint shaded, side panel listing each constraint with value + clause +
  verified badge (unverified shown as "Review").

TESTS
- Envelope: rectangle plot, L-shaped plot, corner plot (two road sides), plot too small
  to build (empty envelope → clear error), each rule category applied correctly.
- Ruleset YAML validation rejects malformed rules.
- Plot validation rejects self-intersecting polygons.

ACCEPTANCE CHECKLIST
[ ] Draw a plot on the map → see envelope with labelled setbacks
[ ] Every number shown in the UI traces to a rule id + clause
[ ] List of unverified rules delivered to me
[ ] Tests + CI green
Summarize, list decisions and open questions, then stop.
