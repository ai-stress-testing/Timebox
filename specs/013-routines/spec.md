# Spec 013 — Routines: reusable sequential task sequences (GitHub #25)

**Status:** proposed — architecture + acceptance criteria only, not yet implemented.
**Depends on:** nothing structurally. Per-step actuals feed spec 007
(`duration_profiles`) once both exist; calendar placement reuses the
existing events model + timeboxing (issue #12's to-do funnel is the closest
existing precedent for "a non-event thing that turns into a calendar block").

## Problem

A **routine** is an ordered sequence of tasks done together — a morning
routine, a gym circuit, a closing checklist. Users want to define the
sequence once, **run it step-by-step**, and learn how long each step *and
the whole routine* actually take. Timebox has single events and chores but
no notion of an ordered, reusable multi-step sequence with its own execution
view. This is a planning/execution unit — deliberately no attention or
keystroke monitoring, consistent with the direction this backlog pass
steered toward (specs 005–012) and away from (the now-closed
attention-monitoring track).

## Data model

All user-scoped, UUIDv7 PKs, soft delete; sensitive text AES-GCM encrypted
(same field crypto as event titles, via `crypto.encrypt_field`):

- `routines`: `id, user_id, name_enc, description_enc?, color,
  estimated_minutes (derived = Σ step estimates, recomputed on step
  change — not stored independently of its steps, to avoid drift), is_active,
  created/updated/deleted_at`
- `routine_steps`: `id, routine_id, user_id, position (int), name_enc,
  estimated_minutes, is_optional (bool), created/updated/deleted_at` —
  ordered by `position`.
- `routine_runs`: `id, routine_id, user_id, status (in_progress|completed|
  abandoned), started_at, ended_at, total_actual_minutes, event_id?` — one
  execution.
- `routine_step_runs`: `id, routine_run_id, routine_step_id, user_id, status
  (pending|active|done|skipped), started_at, ended_at, actual_minutes`.

`estimated_minutes` on `routines` as a derived value: recompute it in the
service layer whenever a step is added/removed/re-estimated (`SELECT
SUM(estimated_minutes) FROM routine_steps WHERE routine_id = ...` — cheap,
no need to cache given routines have at most a handful of steps) rather than
maintaining it as an independently-writable column that can drift from its
steps.

## Architecture

- `Models/routine.py` — all four tables (one model file per related group,
  same convention as `pomodoro.py` holding three tables).
- `Repositories/routine_repo.py` — routine/step CRUD (ordered by
  `position`), run/step-run CRUD.
- `Services/routine_service.py`:
  - `create_routine`, `add_step` (assigns next `position`), `reorder_steps`
    (given an ordered list of step ids, renumber `position` — a single pure
    function taking `(current_steps, new_order) -> updated_positions`,
    unit-testable without a DB).
  - `delete_step` — soft-delete, then renumber remaining steps' `position`
    to stay contiguous (no gaps — simplifies the run view's "next step"
    logic to `position + 1`, not "next non-deleted position").
  - `start_run(session, user_id, routine_id) -> RoutineRunOut` — creates a
    `routine_runs` row (`status=in_progress`) and one `routine_step_runs`
    row per current step (`status=pending`, first one flipped to `active`).
  - `advance_step(session, user_id, run_id, step_run_id, actual_minutes?,
    skipped?)` — marks the current step `done` or `skipped` (skip only valid
    if `routine_steps.is_optional`), records `actual_minutes`, activates the
    next `pending` step. If no steps remain, the run auto-completes (see
    `finish_run`).
  - `finish_run(session, user_id, run_id)` — sets `status=completed` (or the
    caller can `abandon_run` instead, `status=abandoned`), sums
    `actual_minutes` across step runs into `total_actual_minutes`.
  - `schedule_routine(session, user_id, routine_id, start_at, event_type,
    attention_class?)` — same shape as spec 012's issue-#12 precedent
    (`todo_service.schedule_todo`): builds an `EventCreate` from the
    routine's name + derived `estimated_minutes`, calls the existing
    `event_service.create_event`, links the resulting event id into a new
    `routine_runs` row (`event_id` set, `status` still `pending`/not yet
    started) so opening that calendar block can offer "launch the run view."
- **API**:
  - `GET/POST /routines` · `PATCH/DELETE /routines/{id}`
  - `GET/POST /routines/{id}/steps` · `PATCH/DELETE
    /routines/{id}/steps/{stepId}` · `POST /routines/{id}/steps/reorder { ordered_step_ids }`
  - `POST /routines/{id}/runs` (start) · `POST
    /runs/{runId}/steps/{stepRunId}/advance { actual_minutes?, skipped? }` ·
    `POST /runs/{runId}/finish` · `POST /runs/{runId}/abandon`
  - `POST /routines/{id}/schedule { start_at, event_type, attention_class?
    }` — the calendar-placement funnel.
  - `GET /routines/{id}/runs?limit=` (history)
- **Frontend**: a dedicated **Routines** page (new top-nav item — the app is
  already at 4 nav items after issue #12 added "To do"; a 5th is fine, or
  fold Routines under an existing page if the header gets crowded,
  implementer's call) with list + step builder (reorder via drag →
  `position`, live total-estimate display), and a focused **run view**
  (current step, large running timer, Done/Skip/Pause/Abandon, whole-run
  timer alongside) — reuse the pomodoro timer's `mm:ss` formatting helper
  (`Components/focus/session-timer.tsx`) rather than writing a second
  countdown formatter.

## Non-goals

- No attention/keystroke monitoring during a run — purely user-driven
  Done/Skip actions, no automatic step-completion detection.
- No routine templates/sharing (single-user app; a routine is just data like
  any other).
- Reordering ships via an explicit reorder endpoint taking a full ordered id
  list (simplest correct approach) — no drag-and-drop-with-partial-diff
  protocol required.

## Acceptance criteria

- [ ] A routine with N ordered steps runs start→finish, recording per-step
      and total actual minutes; skipped optional steps are excluded from
      `total_actual_minutes`.
- [ ] Reordering persists by `position`; deleting a step soft-deletes and
      renumbers the rest to stay contiguous (verified: no gaps in
      `position` after a mid-sequence delete).
- [ ] `reorder_steps`'s renumbering logic is a pure, unit-tested function
      independent of the DB.
- [ ] A routine can be placed on the calendar as an estimate-sized block
      (via `schedule_routine`, reusing `event_service.create_event`) that
      links back to a `routine_runs` row.
- [ ] Abandoning a run mid-sequence leaves completed steps' actuals intact
      and does not affect the routine definition itself.
- [ ] Backend tests cover the full run lifecycle (start → advance × N →
      finish, and a separate skip + abandon path); `tsc` + web build clean.
