# PHASE 1 — Foundation, Design System & System Design

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
