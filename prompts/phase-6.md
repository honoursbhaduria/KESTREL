# PHASE 6 — Interiors, Exports, Billing & Production Launch

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
