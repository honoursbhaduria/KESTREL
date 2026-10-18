# Phase Prompts

Paste one prompt per session, in order. Each assumes `CLAUDE.md` is in the repo root.
Don't start a phase until the previous phase's acceptance checklist passes.

---

## PHASE 1 — Foundation, Design System & System Design

```
Read CLAUDE.md fully before doing anything. This is Phase 1 of 6.

GOAL
Set up the foundation every later phase builds on: repo structure, backend skeleton,
auth + multi-tenancy, local infra, CI, the design system extracted from our landing
page, and the written system design. No product features yet.

STEP 0 — INSPECT AND REPORT FIRST (do not write code yet)
1. Inspect the existing landing page code. Report: framework, version, styling approach
   (Tailwind/CSS modules/etc.), fonts, animation libraries, build tool.
2. Clone the reference repos into references/ exactly as listed in CLAUDE.md §8 and add
   references/ to .gitignore.
3. Read system-design-notes chapters 01, 02, 03, 04, 15, 19, 20, 24.
4. Give me a short report and a proposed monorepo layout (frontend/, backend/, docs/,
   rules/). Wait for my approval.

STEP 1 — SYSTEM DESIGN DOC
Write docs/system-design.md using the chapter 03 framework:
- Requirements: functional (plot → envelope → plans → review → assistant → 3D →
  interiors → export) and non-functional (latency targets, availability, cost limits).
- Back-of-envelope estimates (chapter 02): orgs, users, projects/user, plan JSON size,
  plan versions/project, generation jobs/day, renders/day, storage/month, LLM cost/project.
- High-level architecture diagram (Mermaid): frontend, FastAPI API, arq worker,
  Postgres+PostGIS+pgvector, Redis, object storage, LLM provider, image provider.
- Data flow for: plan generation job, assistant fix proposal, interior render webhook.
- Scaling plan: what we do at 100 / 10k / 100k users (stateless API, read replicas,
  CDN, queue partitioning). State clearly that we start as a modular monolith.
- Failure modes: LLM provider down, image webhook never arrives, worker crash mid-job.

STEP 2 — BACKEND SKELETON
- backend/ with uv, Python 3.12, FastAPI, Pydantic v2, pydantic-settings.
- Module layout exactly as CLAUDE.md §5 (empty modules are fine except auth/projects/jobs).
- core/: config, structured JSON logging (structlog) with request IDs, global error
  handler returning a consistent error shape {code, message, details}.
- db/: async SQLAlchemy 2.0 session, base model with id (UUID), org_id, created_at,
  updated_at; Alembic configured; PostGIS and pgvector extensions enabled in first
  migration.
- auth module: register, login, refresh, logout; Argon2 hashing; JWT access (short) +
  refresh (rotating, stored hashed). Orgs + memberships (roles: owner, member).
  Registering creates a personal org.
- projects module: CRUD for projects, scoped by org_id IN THE REPOSITORY LAYER.
- jobs module: Job table (id, org_id, type, status, progress, result, error,
  idempotency_key) + GET /jobs/{id} + SSE /jobs/{id}/events. Worker (arq) with one
  dummy task to prove the pipeline works end to end.
- /health (liveness) and /ready (DB + Redis check). /metrics (Prometheus).

STEP 3 — INFRA
- docker-compose.yml: api, worker, postgres (postgis image + pgvector), redis, minio.
- .env.example listing every variable with a comment.
- Makefile or justfile: up, down, migrate, test, lint, format.
- CI (GitHub Actions): ruff, pyright/mypy, pytest with Postgres service,
  alembic upgrade check, frontend lint + build.

STEP 4 — DESIGN SYSTEM
- Extract the landing page's real values (colors, fonts, sizes, spacing, radii,
  borders, shadows, motion durations) into one tokens file. Copy values, don't eyeball.
- Build shared components matching the landing page style: Button, Card, Panel,
  StatusPill (Pass / Review / Fail), CoordLabel ("X: 8052 MM"), BracketLabel ("[01]"),
  DataRow, GridBackground, Input, Modal, Toast.
- App shell: sidebar/topbar, auth pages (login/register), projects list, empty project
  page. All using the shared components only.
- Generate TypeScript API types from FastAPI's OpenAPI schema; one API client wrapper
  with auth refresh handling.
- Show me screenshots of login + projects list before moving on.

TESTS (required)
- Auth: register, login, refresh rotation, bad password, expired token.
- Tenancy: user from org A cannot read/update/delete org B's project (404, not 403).
- Jobs: dummy job goes queued → running → done; SSE emits updates.

ACCEPTANCE CHECKLIST
[ ] docker compose up brings everything up; migrations run cleanly
[ ] docs/system-design.md complete with Mermaid diagrams and estimates
[ ] I can register, log in, create/list/delete projects in the UI
[ ] UI visually matches the landing page (screenshots)
[ ] CI green
When done: summarize what you built, how to run it, and every decision you made
that I should know about. Then stop.
```

---

## PHASE 2 — Plot, Rulesets & Buildable Envelope

```
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
```

---

## PHASE 3 — Plan Model, 2D Workspace & Review Engine

```
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
```

---

## PHASE 4 — AI Plan Generation

```
Read CLAUDE.md, especially §2.1. Phases 1–3 are complete. This is Phase 4 of 6.

GOAL
Brief + envelope → 3 to 5 valid, scored floor plan options. The LLM structures the
brief; deterministic code produces all geometry.

BACKEND
1. LLM wrapper (app/ai/llm.py): provider-agnostic, structured output into Pydantic
   models, retries with backoff, timeout, token + cost logging into usage_events
   (org_id, kind, model, input_tokens, output_tokens, cost). Prompts live in
   app/ai/prompts/ as versioned files, not inline strings.
2. Brief → Program:
   - PUT /projects/{id}/brief with free text.
   - LLM returns Program: levels, rooms [{type, name, target_area_mm2, min_width_mm,
     level_hint, needs_exterior_wall, needs_attached_bath}], adjacencies
     [{a, b, strength: must|prefer|avoid}], preferences {entrance_side, vastu: bool,
     parking: bool, style_notes}.
   - Validate the program against the envelope BEFORE generating: total target area
     vs max built-up area (FAR); room minimums from the ruleset. If infeasible, return
     a clear explanation and a suggested adjusted program — don't silently shrink.
   - The user can edit the structured program in the UI before generating.
3. Layout solver (planning module, pure Python, heavily commented — I must be able to
   explain it in an interview):
   - Recursive rectangular subdivision of the envelope footprint (slicing tree),
     area-weighted, with randomized split order to produce many candidates.
   - Zoning first: public (living, dining, kitchen, entrance) vs private (bedrooms)
     vs service (bath, utility, stairs), then subdivide each zone.
   - Insert a circulation spine/corridor; place stairs for multi-level plans and
     align stairs vertically across levels.
   - Convert room rectangles → walls (shared walls deduplicated) → doors (one per
     room on the circulation side, adjacency-aware) → windows on exterior walls.
   - Score each candidate: area error, must/prefer/avoid adjacency, aspect ratio
     penalty, exterior wall access for habitable rooms, circulation length, entrance
     side, vastu preferences if enabled (document which vastu heuristics you use and
     keep them in a config file, not hardcoded).
   - Run the Phase 3 rule engine on the top candidates; drop any with hard fails;
     return top N with score breakdown.
   - Deterministic given a seed (store the seed for reproducibility).
   - Performance target: generation job finishes under 30 s for a 2-floor 4BHK.
4. Job: POST /projects/{id}/generate → 202 + job_id, idempotency key required.
   Worker runs solver, streams progress over SSE ("Indexing / Zoning / Placing /
   Checking" — mirror the landing page's Observe/Flag/Propose/Apply phase UI).
   Each option is saved as a Plan with created_by: solver.
5. LLM writes a 2–3 sentence description of each option from its score breakdown
   (the LLM describes; it does not judge).

FRONTEND
- Brief screen: textarea + "Structure brief" → editable program table (rooms, areas,
  adjacencies, preferences) + feasibility panel (FAR used vs allowed).
- Generate button → progress UI in landing page style (phases, counters).
- Options screen: grid of option cards, each a mini SVG plan + score breakdown +
  issue counts + description. Compare two side by side. "Open in workspace".

TESTS
- Solver: every output room within envelope, no overlaps, every room reachable from
  entrance (graph check), target areas within tolerance, same seed → same output.
- Infeasible program is detected and explained.
- LLM layer: tests use recorded fixtures/mocks; no network in CI.
- Benchmark script reporting generation time for 3 program sizes.

ACCEPTANCE CHECKLIST
[ ] Type a brief → edit program → generate → see 3–5 valid options in < 30 s
[ ] Open an option in the workspace; review shows no hard fails
[ ] Usage/cost logged per org
[ ] Tests + CI green
Summarize, show sample outputs (screenshots), list known solver weaknesses, then stop.
```

---

## PHASE 5 — Review Assistant & 3D Model

```
Read CLAUDE.md, especially the Assistant section in §5. Phases 1–4 are complete.
This is Phase 5 of 6.

GOAL
(a) The overlay assistant from the landing page: ask about the plan, get answers with
the rule cited, receive fix proposals with preview, apply only on approval.
(b) A 3D model of the plan in the browser.

PART A — ASSISTANT (assistant module)
1. Conversation storage: conversations, messages (role, content, tool_calls), scoped to
   plan + org.
2. Tool-calling loop (single agent, max N tool steps, timeout):
   Tools (Pydantic-validated inputs/outputs, each a thin call into existing services):
   - get_plan_summary(plan_id)
   - get_issues(plan_id, status?)
   - run_check(plan_id, rule_id)
   - measure(plan_id, element_ids) → widths, areas, distances
   - search_rules(query) → RAG chunks with clause refs
   - propose_fix(plan_id, ops: list[PatchOp], rationale, rule_id)
3. propose_fix NEVER applies. It creates a Fix row (status: proposed) and computes:
   the patched plan (not saved as a version), re-run the review on it, and stores
   the issue diff (resolved / introduced / unchanged). If the fix introduces new
   fails, the assistant must say so.
4. Endpoints: POST /plans/{id}/assistant (stream tokens via SSE),
   POST /fixes/{id}/preview, POST /fixes/{id}/apply (idempotent, creates a new plan
   version with created_by: ai and message = rationale), POST /fixes/{id}/skip.
5. Guardrails: assistant answers only about this project/plan and building rules;
   every numeric claim must come from a tool result, not the model's memory — enforce
   in the system prompt and add an eval for it.
6. Evals: tests/evals/ with ~20 scripted questions over fixture plans ("Does corridor
   C2 meet width?", "Make bedroom 2 bigger", "Is the stair compliant?"). Check tool
   selection, cited clause, and that proposed fixes actually resolve the issue.
   Runnable with one command; not in normal CI (costs money).

PART A — FRONTEND
- Floating assistant panel over the workspace styled like the landing page
  "Kestrel · overlay" card.
- Fix card: rationale, rule + clause, Apply / Preview / Skip.
- Preview = ghost overlay on the plan (changed elements highlighted, before/after
  toggle) + issue diff list.
- Clicking an issue in the review console offers "Ask assistant to fix".
- Change log panel: every applied fix, who approved it, revert button.

PART B — 3D
1. Backend: plan → glTF export function (walls extruded with thickness and height,
   openings cut as holes, floor slabs per level, stairs as simple steps).
   GET /plans/{id}/versions/{v}/model.glb, cached in object storage keyed by
   plan version.
2. Frontend: react-three-fiber viewer.
   - Orbit mode + first-person walkthrough mode (WASD, collision with walls optional).
   - Level isolation / cut-away (hide upper levels), section plane slider.
   - Click a wall/room in 3D → selects the same element in 2D (shared selection state).
   - Issues highlighted in 3D the same way as 2D.
   - Lighting: sun direction from north angle + time-of-day slider (simple directional
     light; no heavy rendering).
   - Performance: one draw call per material where possible; target 60 fps for a
     2-floor house on a normal laptop.

TESTS
- Fix flow: propose → preview → apply creates exactly one version; apply twice is
  idempotent; skip leaves plan untouched.
- Fix that introduces a new fail is reported in the diff.
- glTF export: valid file, wall count matches plan, opening holes present.

ACCEPTANCE CHECKLIST
[ ] Ask "does corridor X meet width?" → correct answer with clause
[ ] Ask for a fix → preview → apply → new version → review updated → revert works
[ ] 3D model matches the 2D plan; selection syncs between them
[ ] Eval report delivered
Summarize, list decisions and open questions, then stop.
```

---

## PHASE 6 — Interiors, Exports, Billing & Production Launch

```
Read CLAUDE.md. Phases 1–5 are complete. This is Phase 6 of 6.

GOAL
Finish the feature set (interior renders, exports), add credits/billing, harden
everything from the system design doc, and deploy to production.

PART A — INTERIOR RENDERS (renders module)
1. Image wrapper (app/ai/images.py): provider-agnostic; supports sync and
   webhook-async providers (pattern from ai-real-estate-stager — patterns only, no
   copied code).
2. Flow: user picks a room in 3D, sets camera → frontend captures a clean render
   (walls/floor/windows, no furniture) → uploads via presigned URL → POST
   /plans/{id}/renders {room_id, style, notes, image_key} → job → provider →
   result stored in object storage → webhook or polling completes the job.
3. Styles as config (modern minimal, Scandinavian, Indian contemporary, etc.), prompt
   built from room type + style + room dimensions + window positions.
4. Webhook endpoint verifies provider signature; idempotent on provider job id;
   timeout sweeper marks stuck jobs failed and refunds credits.
5. Frontend: render gallery per project; before/after drag slider; download;
   regenerate with tweaks.

PART B — EXPORTS (exports module)
- DXF (ezdxf): layers for walls, doors, windows, dimensions, room labels, envelope,
  setback lines; correct units (mm).
- PDF sheet: plan per level + dimensions + room schedule (name, area) + title block
  (project, date, version, ruleset) + issue summary.
- glTF (reuse Phase 5).
- All exports are jobs; results via presigned download URLs; tie each export to a
  plan version.
- IFC: only a spike — investigate ifcopenshell, write findings in docs/ifc-spike.md,
  don't ship it.

PART C — CREDITS & BILLING
- Credit ledger table (append-only: org_id, delta, reason, ref_id, balance_after).
  Never store balance as a mutable field without the ledger.
- Costs per action in config: generate, assistant message, render, export.
- Check + reserve credits before a job; commit on success; refund on failure.
- Payment provider integration (Razorpay for India; keep it behind an interface so
  Stripe can be added). Webhook → ledger credit. Verify signatures. Idempotent.
- Billing page: balance, ledger history, buy credits.

PART D — HARDENING (from docs/system-design.md)
- Rate limiting: Redis token bucket per user and per org; stricter buckets for
  generate, assistant, renders; 429 with Retry-After.
- Idempotency keys enforced on every money- or job-creating endpoint.
- Queue: retries with exponential backoff, max attempts, dead-letter list + admin
  view to retry.
- Security: CORS locked down, security headers, upload size/type limits, presigned URL
  expiry, secrets only from env, dependency audit (pip-audit, npm audit), OWASP top 10
  pass over every endpoint — write findings in docs/security-review.md.
- Observability: Sentry (API, worker, frontend); Prometheus metrics for p95 latency,
  job duration and failure rate by type, LLM/image cost per org per day; alert rules
  documented.
- Load test (k6 or Locust): realistic mix of reads, patches, review runs; report p95
  and the first bottleneck found.
- Backups: Postgres automated backups + a tested restore procedure in docs/runbook.md.

PART E — DEPLOY
- Frontend on Vercel. API + worker as containers (Render/Fly/Railway — propose one
  with reasoning). Managed Postgres with PostGIS + pgvector, managed Redis,
  Cloudflare R2.
- Staging and production environments; CI deploys staging on main, production on tag.
- Zero-downtime migrations (expand → migrate → contract) documented.
- docs/runbook.md: deploy, rollback, rotate secrets, restore backup, handle stuck jobs.

TESTS
- Render job: success, provider failure (refund), webhook replay (idempotent),
  timeout sweeper.
- Credits: concurrent jobs can't overspend (test with parallel requests).
- Payment webhook: bad signature rejected, replay ignored.
- DXF opens and has expected layers/entity counts.
- E2E (Playwright): register → plot → brief → generate → review → assistant fix →
  3D → render → export.

ACCEPTANCE CHECKLIST
[ ] Full E2E flow passes on staging
[ ] Load test report + security review delivered
[ ] Production deployed; runbook complete
[ ] Every unverified rule still listed (cannot launch to paying users with
    unverified setback/FAR rules — flag this clearly)
Summarize, list remaining risks and recommended next steps, then stop.
```
