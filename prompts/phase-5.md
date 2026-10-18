# PHASE 5 — Review Assistant & 3D Model

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
   the patched plan (not saved as a version), re-runs the review on it, and stores
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
