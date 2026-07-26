# Spec 005 — `attention_classes` as first-class metadata (GitHub #14)

**Status:** proposed — architecture + acceptance criteria only, not yet implemented.
**Depends on:** nothing. Everything downstream of `attention_class` (canvas
assignment, pomodoro gating) depends on this.

## Problem

`attention_class` (`active | involved | passive`) is a bare string enum
(`Schemas/base.py::AttentionClass`) that behavior is branched on in at least
two places today, with no single source of truth:

- `dispatch_maps/canvas_type.py::ATTENTION_DEFAULTS` — a **dead** dict already
  shaped exactly like the table this spec proposes (`pomodoro`, `residual`,
  `default_r` per class) that nothing actually reads.
- `Services/pomodoro_service.py:81` — `if event.attention_class !=
  AttentionClass.active.value:` — pomodoro applicability hardcoded as an
  equality check against one literal class, not a lookup.

Adding a fourth attention class today means touching Python enum + TS union +
every hardcoded branch. This spec turns `ATTENTION_DEFAULTS` from a dead
constant into the real row data those call sites read.

## Data model

New table, **seeded once at boot** (not per-user — this is app-level
configuration, not user content, so no encryption and no `user_id`):

```
attention_classes
  id                    UUIDv7 PK
  value                 String(16) unique   -- "active" | "involved" | "passive"
  label                 String(40)          -- display label, plaintext (not user content)
  description           Text
  pomodoro_applicable    Boolean
  residual_applicable    Boolean
  delay_on_no_complete   Boolean             -- from DB-Schemas.md; not yet consumed anywhere
  default_r              Numeric(4,3)        -- radial-canvas default distance (0..1), for spec 010
  default_alarm_class    String(24) nullable -- for spec 010's canvas_alarms.alarm_class
  created_at / updated_at
```

No `deleted_at` — this table is never user-facing CRUD, so `EntityMixin` is
the wrong fit; use a smaller mixin (`id`, `created_at`, `updated_at`) or a
plain `Base` subclass with explicit columns. Seed rows are fixed at three
(`active`, `involved`, `passive`); `value` is what code joins/looks up on,
**not** `id` — call sites already have the string, not a foreign key.

## Architecture

- `Models/attention_class.py` — the table above.
- `Repositories/attention_class_repo.py` — `list_all(session)`,
  `get_by_value(session, value)`. Trivial, no `user_id` filter.
- `Services/attention_class_service.py`:
  - `ensure_seeded(session)` — idempotent boot-time seed of the 3 rows
    (mirrors `event_type_service.ensure_seeded`'s shape, called once from
    `main.py`'s lifespan instead of per-request/per-user since this data
    isn't user-scoped).
  - `is_pomodoro_applicable(session, value: str) -> bool` and
    `is_residual_applicable(session, value: str) -> bool` — the two lookups
    that replace the hardcoded branches.
- **Migration of existing hardcoded logic** (this is the acceptance bar, not
  just "table exists"):
  - `pomodoro_service.py:81` changes from `!= AttentionClass.active.value` to
    `not await attention_class_service.is_pomodoro_applicable(session,
    event.attention_class)`.
  - `dispatch_maps/canvas_type.py::ATTENTION_DEFAULTS` is deleted; its three
    rows become the seed data in `attention_class_service.ensure_seeded`.
    `OVERLAP_TYPE_MAP` and `assign_canvas_type` are unrelated (they map
    *combinations* of classes to a `CanvasEventType`, not per-class config)
    and stay exactly as they are — this spec does not touch canvas-type
    assignment.
- **API**: `GET /attention-classes` — read-only, returns the 3 seeded rows.
  No create/update/delete endpoint in this spec (seed rows are fixed; adding
  a 4th class is a data migration + enum update either way, this table just
  stops that migration from also requiring a code-branch hunt).
- **Frontend**: `lib/api-schemas.ts` gets `attention_class_meta_schema` +
  list; a `use_attention_classes()` query hook. Nothing currently *needs* to
  render this — it exists so a future settings/debug view can, and so the
  radial canvas (spec 010) has `default_r`/`default_alarm_class` to read.

## Non-goals

- No per-user customization of attention classes (still a global, seeded
  enum-equivalent — just table-backed instead of code-backed).
- No new 4th class introduced by this spec.
- `delay_on_no_complete` is captured as a column (DB-Schemas.md lists it) but
  no code path consumes it yet — that's residual-flow work, out of scope here.

## Acceptance criteria

- [ ] `attention_classes` seeds exactly 3 rows at boot, idempotently (running
      `ensure_seeded` twice does not duplicate or error).
- [ ] `pomodoro_service.py` no longer contains a literal
      `AttentionClass.active` equality check for applicability — it calls the
      new lookup, and behavior is unchanged (a session on an `active` event
      still gates pomodoro exactly as before).
- [ ] `ATTENTION_DEFAULTS` is removed from `dispatch_maps/canvas_type.py`;
      `assign_canvas_type`'s existing test coverage still passes unmodified
      (proves canvas-type assignment was untouched).
- [ ] `GET /attention-classes` returns the 3 rows with correct flags.
- [ ] Backend tests cover: seed idempotency, the pomodoro-applicability
      lookup for all 3 classes, and a regression test asserting an `active`
      event still starts a pomodoro session end-to-end.
