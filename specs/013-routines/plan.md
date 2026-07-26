# Spec 013 — Routines: implementation plan + deviations

Implemented end-to-end (backend + frontend) on `sprint-1`, in parallel with
two sibling features. Backend router is fully wired into its own module;
frontend page is built and verified in isolation, not yet wired into the
central dispatch map (by design — see the "not yet wired" note in the final
report).

## Deviations from spec.md

- **`RoutineRun.status` gains a `pending` value.** `spec.md`'s data-model
  section lists `in_progress|completed|abandoned`, but the architecture
  section's `schedule_routine` description explicitly requires a run row
  created "not yet started" when a routine is placed on the calendar without
  being run. Widened `RoutineRunStatus` to `pending|in_progress|completed|
  abandoned` to make that state representable; `start_run` always creates
  its own fresh `in_progress` run (with step runs) rather than resuming a
  `pending` one — `schedule_routine`'s run row is a placeholder link
  (`event_id` set) for a future "launch the run view from the calendar
  block" feature, not wired to `start_run` in this slice.
- **Step/routine names are AES-GCM encrypted** via `crypto.encrypt_field`,
  per spec.md's "sensitive text ... same field crypto as event titles"
  instruction — noted here because step names are pretty low-sensitivity in
  practice, but consistency with the rest of the encrypted-at-rest fields
  was judged more valuable than the modest simplicity gain of leaving them
  plaintext.
- **`RoutineStep` soft-delete does not cascade from `Routine` soft-delete.**
  Deleting a routine soft-deletes only the `routines` row; its steps stay in
  the table (invisible to the API since every steps query is routine-scoped
  through a live routine anyway, but not marked `deleted_at`). A background
  purge job cascading soft-deletes was out of scope for this slice.
- **`RoutineRunOut.steps[].step_name/estimated_minutes/is_optional` are
  denormalized onto the step-run DTO** (looked up from `RoutineStep` at read
  time, including soft-deleted steps) rather than requiring the frontend to
  separately fetch and join `GET /routines/{id}/steps`. Not in spec.md's
  schema sketch but needed for the run view to render a step's name at all.
- **Two `APIRouter`s in one module** (`routines.router` prefix `/routines`,
  `routines.runs_router` prefix `/runs`) because spec.md's own path list
  addresses run-advance/finish/abandon by run id alone
  (`/runs/{runId}/...`), not nested under `/routines/{id}`. Both need
  mounting in `main.py` — see the final report's exact snippet.
- **Frontend "Pause" is UI-only.** The run view's Pause button freezes the
  on-screen step/run timers (a local pause-window calculation) but does not
  call any endpoint or persist a paused state — spec.md lists Pause as a
  run-view control but the data model has no `paused` status for either
  `routine_runs` or `routine_step_runs`, and adding one was judged out of
  scope for this slice. Resuming a run after a page reload will show the
  server-computed elapsed time (not the paused snapshot).
- **Reordering ships as up/down-arrow controls, not drag-and-drop** — spec.md
  explicitly allows this ("a plain up/down-arrow reorder control is an
  acceptable alternative to full drag-and-drop if that's faster to build
  correctly"). Both directions call the same `POST .../steps/reorder` with
  the full ordered id list.
- **Test-only app wiring workaround.** `apps/api/tests/test_routines.py`
  attaches `routines.router`/`routines.runs_router` to the already-built
  `app.main.app` instance at import time (guarded so it only runs once) and
  imports `app.Models.routine` for its Base.metadata side effect, because
  `apps/api/app/main.py` and `apps/api/app/Models/__init__.py` are the two
  other in-flight features' hard boundary for this run and could not be
  edited. Once those files are wired for real, this workaround becomes
  redundant but harmless (the guard no-ops on an already-included router).

## Testing

- `apps/api/tests/test_routine_steps.py` — pure unit tests for
  `Pipelines/routine_steps.py` (`renumber_positions`,
  `renumber_after_delete`), no DB.
- `apps/api/tests/test_routines.py` — full run lifecycle (start → advance ×
  N → auto-complete), explicit `finish_run` rejection once already
  completed, skip-optional-only path (including the 409 rejection of
  skipping a required step), abandon path (completed step actuals
  untouched), reorder + delete-closes-gap, and the schedule funnel
  (`schedule_routine` → real event visible via `GET /events`, plus the
  no-steps-to-schedule 409).
