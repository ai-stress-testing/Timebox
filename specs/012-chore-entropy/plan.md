# Spec 012 — Chore Entropy: implementation notes / deviations

Implemented as a thin vertical slice: chores page slider drives the
existing `PATCH /chores/{id}` (via its `n_days` field, which lands on
`ChoreDefinition.n_current`), and a new `POST /chores/{id}/complete`
records completions and updates the Welford-based `recommended_n`.

## Deviations from spec.md

- **`ChoreDefinition.mc_weight` is not touched.** The spec's Architecture
  section says to "feed `recommended_n` vs `n_current` into `mc_weight`
  alongside spec 007's duration-based signal (same column, ... implementer's
  call on the exact blend)." Spec 007's duration-based signal isn't wired
  into `mc_weight` yet either, so there's nothing concrete to blend
  against, and the Non-goals section is explicit that "no change to the MC
  scheduler's core algorithm" is required. Left `mc_weight` as-is; a
  follow-up spec should define the blend once both signals exist.
- **`chore_service.to_out` became `async` and now does one extra
  `ChoreEntropy` lookup per chore** (in `list_chores`'s loop, so N+1 queries
  for N chores) to populate `recommended_n`. This is the "boring
  implementation behind the scalable interface" choice for a single-user
  SQLite prototype — a join or a batched lookup would remove the N+1 but
  isn't warranted at this scale yet.
- **`ChoreCompletion.days_since_previous` is nullable**, not `Numeric(6,2)
  NOT NULL` as the bare schema sketch in spec.md implies. A chore's first
  completion has no prior `last_completed_at` to diff against — the row is
  still written (for a complete audit log) but with a null gap, and the
  Welford update is skipped for it, per the spec's `record_completion`
  description.
- **`ChoreEntropy.chore_id` is a regular indexed+unique column, not the
  literal primary key** the spec's table sketch shows. Followed this
  codebase's existing style (`EventType`'s `EntityMixin` id + a
  `sqlite_where`-scoped unique index on the semantic key) instead of a
  bespoke non-`EntityMixin` model, for consistency with every other table
  in `Models/`.
- **No Alembic migration added.** This codebase creates tables via
  `Base.metadata.create_all` (see `app/Core/database.py` /
  `tests/conftest.py`'s `init_models`), not migrations — consistent with
  every other model in the app.

## Frontend notes

- `Slider`'s handle defaults to `recommended_n` (falling back to
  `n_current` when no completions have been logged yet), matching the
  spec's explicit intent that the handle should *not* mirror the current
  schedule, so the gap between "scheduled" and "recommended" stays visible.
  Releasing without dragging still fires no `PATCH` (only `onCommit` does).
- Added a "Done" button to each chore row (there was no existing
  mark-complete interaction anywhere in the UI) wired to the new
  `POST /chores/{id}/complete`.
