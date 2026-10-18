# Project Brief — AI Home Design Platform for Architects

Read this whole file before writing any code. It is the source of truth for scope,
architecture and conventions. If something here conflicts with what you find in the
repo, stop and ask.

---

## 1. What we are building

A web platform that helps an architect go from **a plot of land + a client brief** to
**a code-checked floor plan, a 3D model, and furnished interior visuals** — with an AI
assistant that flags problems and proposes fixes, but only edits after approval.

The landing page already exists. Its promise is the product loop we must deliver:

> **Observe → Flag → Propose → Apply.**
> Read the model, flag what a reviewer would send back (with the rule attached),
> preview a fix and its knock-on effects, apply only on approval, log every change,
> make every change reversible.

This is a **web app**, not a Revit/AutoCAD/Rhino plugin. Plugins are out of scope.
Export to DXF/IFC so architects can continue in their own tools.

### Core user flow (MVP)

1. **Plot** — architect draws the plot boundary on a map (OSM tiles) or enters
   dimensions; marks road-facing side(s) and north.
2. **Rules** — picks the jurisdiction ruleset (setbacks, FAR/FSI, ground coverage,
   height, min room sizes). System computes the **buildable envelope**.
3. **Brief** — describes the program in plain language ("3BHK, 2 floors, parking,
   pooja room, east-facing entrance, vastu preferred"). AI turns it into a structured
   program.
4. **Generate** — system produces 3–5 floor plan options inside the envelope.
5. **Review** — every option gets a pass/fail/review checklist (like the "Review
   console" on the landing page). Click an issue → see it highlighted on the plan.
6. **Assistant** — chat panel: "Does corridor C2 meet the width rule?" → answer with
   the rule cited → "Shift partitions 50 mm east. Preview?" → Apply / Preview / Skip.
7. **3D** — the selected plan extruded into a navigable 3D model in the browser.
8. **Interiors** — pick a room + style → AI-generated furnished render.
9. **Export** — PDF sheet, DXF, glTF (IFC later).

---

## 2. Non-negotiable technical decisions

### 2.1 The LLM never draws coordinates

LLMs are bad at geometry. They produce overlapping rooms, impossible dimensions and
plans that ignore setbacks. So:

- **LLM's job:** parse the brief → structured program (rooms, target areas,
  adjacencies, preferences); explain rule results; turn a chat request into a
  structured edit command; write descriptions.
- **Deterministic code's job:** envelope computation, layout generation, rule checks,
  applying edits. All geometry is computed by code we can test.

Layout generation approach (start simple, improve later):

1. Build an adjacency graph from the program (kitchen–dining, bedroom–bath, etc.).
2. Generate candidates with **recursive rectangular subdivision of the envelope**
   (slicing-tree / squarified-treemap style), weighted by target areas.
3. Score candidates: area error, adjacency satisfaction, aspect ratios, daylight on
   habitable rooms, circulation length, orientation/vastu preferences (if enabled).
4. Keep the top N. Run the rule engine. Discard hard failures.
5. Later, if needed: replace/augment with OR-Tools CP-SAT for constraint-based packing.

Use **Shapely** for all 2D geometry. Store plot/envelope geometry in **PostGIS**.

### 2.2 The Plan JSON is the core contract

Everything — 2D editor, 3D viewer, rule engine, assistant edits, exports — reads and
writes one versioned schema. Define it once as Pydantic models in the backend and
generate TypeScript types for the frontend from the OpenAPI schema.

Minimum shape (millimetres, plan-local coordinates, origin = plot corner):

```
Plan
  id, project_id, version, parent_version, created_by (user|ai|solver)
  units: "mm"
  levels: [Level]
Level
  id, name, elevation_mm, floor_to_floor_mm
  rooms:   [Room   { id, type, name, polygon: [[x,y],...] }]
  walls:   [Wall   { id, start, end, thickness_mm, height_mm, is_external }]
  openings:[Opening{ id, wall_id, kind: door|window, offset_mm, width_mm,
                     height_mm, sill_mm, swing? }]
  stairs:  [Stair  { id, polygon, riser_mm, tread_mm, direction }]
```

Every edit (AI or human) is a **patch** that produces a new `Plan` version. Never
mutate in place. This gives us the landing page's "every change is logged and
reversible" for free.

### 2.3 Rules are data, not code — and never invented

- Rules live in versioned YAML files: `rules/<jurisdiction>/<version>.yaml`.
- Each rule has: `id`, `clause` (source document + section), `applies_to`,
  `check` (which checker function), `params` (the numbers), `severity`,
  `verified: true|false`.
- Sources to start with: **National Building Code of India 2016 (Part 3)** for minimum
  room sizes, widths, heights, ventilation; the relevant **state/city building
  bylaws** for setbacks, FAR, ground coverage, height (start with Uttar Pradesh and
  Uttarakhand).
- **Do not make up numbers.** If you do not have the actual document text, add the rule
  with `verified: false` and a `TODO: source` note. The UI must show unverified rules
  as "Review" not "Pass/Fail".
- Checker functions are pure Python: `(plan, params) -> list[Issue]`. Each one gets
  unit tests with a passing and a failing fixture.
- Also add a RAG index over the source PDFs so the assistant can quote the exact clause
  when explaining a result (pattern from `deep-agent-real-estate`). RAG is for
  *explaining*; the checker functions are what *decide*.

### 2.4 Async jobs for anything slow

Plan generation, rule passes over big projects, image renders and exports run as
background jobs. API returns `202 + job_id`; frontend subscribes via SSE (or polls).
External image APIs that support webhooks should call back into a webhook endpoint
(pattern from `ai-real-estate-stager`).

---

## 3. Stack

### Backend (FastAPI)

| Concern | Choice |
|---|---|
| Framework | FastAPI, Pydantic v2, Python 3.12, `uv` for deps |
| DB | PostgreSQL + PostGIS, SQLAlchemy 2.0 (async), Alembic migrations |
| Cache / rate limit / queue broker | Redis |
| Background jobs | `arq` (async, simple). Move to Celery only if we outgrow it |
| Object storage | S3-compatible (Cloudflare R2 or MinIO locally) via presigned URLs |
| Geometry | Shapely, (later) OR-Tools |
| Exports | `ezdxf` (DXF), `trimesh` or `pygltflib` (glTF), `ifcopenshell` (IFC, later) |
| LLM | Provider-agnostic wrapper (`app/ai/llm.py`); structured outputs validated by Pydantic |
| Image gen | Provider-agnostic wrapper (`app/ai/images.py`) |
| Auth | JWT access + refresh, Argon2 password hashing; org/team model from day one |
| Observability | `structlog` JSON logs, request IDs, Sentry, Prometheus `/metrics` |
| Tests | `pytest`, `pytest-asyncio`, `httpx.AsyncClient`, factory fixtures |

**Architecture: modular monolith.** One deployable FastAPI app + one worker process,
split into clear domain modules. **No microservices.** We have no scale problem yet,
and microservices would multiply complexity for zero benefit. Module boundaries are
designed so a module *could* be extracted later.

### Frontend

- **Use the same framework the existing landing page uses.** Inspect it first and
  report what it is before adding anything.
- 3D: `three` via `@react-three/fiber` + `@react-three/drei` (if React).
- 2D plan view/editor: SVG first (simplest, crisp, easy to hit-test). Canvas/Konva only
  if performance demands it.
- Map for plot drawing: Leaflet or MapLibre with OSM tiles.
- API types generated from FastAPI's OpenAPI schema (`openapi-typescript`).

---

## 4. UI: match the landing page exactly

The whole app must look like it belongs to the landing page. Before building any
screen:

1. Read the landing page source. Extract its design tokens (colors, fonts, font sizes,
   spacing, radii, borders, shadows, motion) into one shared tokens file/theme. Do not
   eyeball — copy the actual values.
2. Reuse its visual language consistently:
   - Technical/drafting feel: grid backgrounds, thin rules, coordinate readouts
     (`X: 8052 MM`), corner coordinate labels (`[0, 0]`, `[1200, 800]`).
   - Bracketed numeric labels: `[01]`, `[Phase 01 / 04]`, `[Click a violation]`.
   - Status vocabulary: **Pass / Review / Fail**.
   - Assistant panel styled like the landing page "overlay" card with
     **Apply / Preview / Skip** actions.
   - Review list styled like the landing page "Review · Project 0412" card.
   - Pipeline progress styled like "Observe / Flag / Propose / Apply" and
     "Indexing · Rooms indexed: 214".
3. Build shared components first (Button, Card, StatusPill, CoordLabel, Panel,
   DataRow), then screens. No one-off styling in screens.
4. Show me screenshots of the first two screens before building the rest.

Screens: Projects list · Project → Plot · Brief · Options · Plan workspace (2D + review
list + assistant) · 3D view · Interiors · Exports · Settings/Team.

---

## 5. Backend layout

```
backend/
  app/
    main.py                 # app factory, middleware, routers
    core/                   # config (pydantic-settings), security, logging, errors
    db/                     # session, base model, migrations (alembic/)
    modules/
      auth/                 # users, orgs, memberships, tokens
      projects/             # projects, plots (PostGIS), briefs
      rules/                # ruleset loader, checker registry, checkers/, issues
      planning/             # envelope, program parsing, layout solver, scoring
      plans/                # Plan schema, versions, patches, diff, undo/redo
      assistant/            # chat, tool definitions, proposals (Fix objects)
      renders/              # 3D export, interior image generation
      exports/              # dxf, gltf, pdf, (ifc)
      jobs/                 # job model, status, SSE endpoint
    ai/                     # llm.py, images.py, prompts/, rag/
    workers/                # arq worker settings + task functions
  rules/                    # YAML rulesets per jurisdiction
  tests/                    # mirrors app/ structure; fixtures/ has sample plans
```

Each module: `router.py` (HTTP only), `service.py` (business logic), `models.py`
(SQLAlchemy), `schemas.py` (Pydantic), `repository.py` (DB access). Routers never
touch the DB directly.

### Key endpoints (v1)

```
POST   /api/v1/auth/register | login | refresh
GET    /api/v1/projects            POST /api/v1/projects
PUT    /api/v1/projects/{id}/plot          # polygon, north, road sides
GET    /api/v1/projects/{id}/envelope      # computed buildable area
PUT    /api/v1/projects/{id}/brief         # free text → structured program (LLM)
POST   /api/v1/projects/{id}/generate      # → 202 job_id, creates N options
GET    /api/v1/projects/{id}/options
GET    /api/v1/plans/{plan_id}/versions/{v}
POST   /api/v1/plans/{plan_id}/patches     # apply an edit → new version
POST   /api/v1/plans/{plan_id}/undo
POST   /api/v1/plans/{plan_id}/review      # → issues list
POST   /api/v1/plans/{plan_id}/assistant   # chat turn → answer and/or Fix proposal
POST   /api/v1/fixes/{fix_id}/preview      # returns the patched plan without saving
POST   /api/v1/fixes/{fix_id}/apply
POST   /api/v1/plans/{plan_id}/renders     # interior render job
POST   /api/v1/plans/{plan_id}/exports     # dxf | gltf | pdf
GET    /api/v1/jobs/{job_id}               GET /api/v1/jobs/{job_id}/events (SSE)
POST   /api/v1/webhooks/images/{provider}
```

### Assistant design

Tool-calling loop (supervisor-routes-to-tools pattern from `deep-agent-real-estate`,
but keep it to one agent with tools until there's a real reason for more):

- Tools: `get_plan`, `get_issues`, `run_check(rule_id)`, `measure(element_ids)`,
  `search_rules(query)` (RAG), `propose_patch(patch)`.
- `propose_patch` **never applies**. It stores a `Fix` (status `proposed`) with the
  patch, a human explanation, the rule it addresses, and the predicted side effects
  (re-run checks on the patched plan and diff the issue list).
- Only `POST /fixes/{id}/apply` applies, and only from a user action.
- Every tool input/output validated with Pydantic. Log every tool call.

---

## 6. System design requirements

Clone the system design notes (see §8) and apply these chapters — they are the
relevant ones for this product:

| Chapter | Apply it to |
|---|---|
| 01 Scaling | Stateless API, sessions in Redis/JWT, DB read replicas later, CDN for static + renders |
| 02 Back-of-envelope | Write a short estimate: users, projects/user, plan JSON size, renders/day, storage/month |
| 03 Framework | Write `docs/system-design.md` using its structure before coding the backend |
| 04 Rate limiter | Redis token bucket per user + per org; stricter limits on `/generate`, `/renders`, `/assistant` (they cost money) |
| 10 Notification | Job-finished notifications (in-app first, email later) |
| 15 Google Drive | Versioning model for plans, file storage + metadata split |
| 19 Message queue | Job queue semantics: idempotent tasks, retries with backoff, dead-letter |
| 20 Monitoring | Metrics: job latency, job failure rate, LLM cost per project, p95 API latency |
| 24 S3 object storage | Renders/exports in object storage, presigned upload/download, never through the API |

Skip the other chapters — they're not relevant here.

Also required:
- **Idempotency keys** on `/generate`, `/renders`, `/exports`, `/fixes/{id}/apply`.
- **Usage metering**: record LLM tokens and image generations per org (credits model
  like `ai-real-estate-stager`; billing integration later).
- **Multi-tenancy**: every row scoped by `org_id`; enforce in the repository layer and
  test that one org cannot read another org's project.
- `docker-compose.yml` for local: api, worker, postgres+postgis, redis, minio.
- CI: lint (`ruff`), type check (`mypy` or `pyright`), tests, migration check.

---

## 7. Build order (milestones)

Do one milestone at a time. At the end of each: tests pass, `docker compose up` works,
and give me a short summary of what was built and how to try it.

Six phases. Full instructions for each are in `PHASE_PROMPTS.md`.

1. **Foundation** — system design doc, FastAPI skeleton, auth + orgs, jobs, infra, CI,
   design system extracted from the landing page.
2. **Plot, rulesets & envelope** — map plot drawing, PostGIS, YAML rulesets, envelope
   computation, rule RAG.
3. **Plan model, 2D workspace & review engine** — Plan schema, versions, patches,
   SVG workspace, checkers, review console.
4. **AI plan generation** — brief → program (LLM), layout solver, scoring, options.
5. **Assistant & 3D** — tool-calling assistant, Fix preview/apply, Three.js model.
6. **Interiors, exports, billing & launch** — renders, DXF/PDF, credits, hardening,
   deployment.

---

## 8. Reference repositories

Clone into `references/` (add `references/` to `.gitignore`). **Read them for patterns
only. Do not copy code from them** — see licenses.

```bash
mkdir -p references && cd references
git clone --depth 1 https://github.com/SamurAIGPT/ai-real-estate-stager.git
git clone --depth 1 https://github.com/narender-rk10/Gen-AI-Home-Interior-Designer.git
git clone --depth 1 https://github.com/Tejas-TA/deep-agent-real-estate.git
git clone --depth 1 https://github.com/TechWithTy/deal-scale.git
git clone --depth 1 https://github.com/liquidslr/system-design-notes.git
```

| Repo | What to learn from it | License note |
|---|---|---|
| ai-real-estate-stager | Async image jobs + webhook delivery, credits model, before/after slider, staging gallery | MIT — patterns fine |
| Gen-AI-Home-Interior-Designer | FastAPI + Gemini image-to-image request shape, room-type/style parameters | **CC BY-NC-ND — do not copy or adapt code** |
| deep-agent-real-estate | Supervisor + tool routing, Pydantic-validated tools, RAG over zoning/bylaw text, OSM amenity lookups | Check license before reusing anything |
| deal-scale | Repo hygiene only: CI, docker-compose, commit conventions. **Its product (investor CRM / lead gen) is not ours** | **Proprietary — do not copy anything** |
| system-design-notes | Chapters listed in §6 | Notes, reference only |

---

## 9. Code conventions

- **Readable over clever.** The founder must be able to explain every file in an
  interview. Clear names, small functions, docstrings on public functions explaining
  *why*, no magic.
- Type hints everywhere. No `Any` without a comment explaining why.
- No dead code, no commented-out code, no placeholder "TODO: implement" functions
  shipped as if done.
- Every geometry function and every rule checker has unit tests.
- Never hardcode secrets; `.env.example` lists every variable.
- Don't add a dependency without saying why in the PR/summary.
- When unsure about a requirement, ask — don't guess and build.
