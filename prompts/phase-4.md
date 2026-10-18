# PHASE 4 — AI Plan Generation

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
