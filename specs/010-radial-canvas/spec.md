# Spec 010 — Radial Canvas: multi-alarm placement view (GitHub #20)

**Status:** proposed — architecture + acceptance criteria only, not yet implemented.
**Depends on:** spec 005 (`attention_classes.default_r`/`default_alarm_class`)
for sensible defaults; functions without it (fall back to literals) but is
cleaner built after.

## Problem

`canvas_event_type` is computed on every event today
(`dispatch_maps/canvas_type.py::assign_canvas_type`, called from
`event_service._reassign_canvas_types` on every create/patch/delete that
touches an overlap) — but it is **never rendered as anything other than a
read-only text badge** in the edit-event drawer
(`canvas-badges.ts` → `Badge title="Assigned automatically by the server"`).
The entire point of the classification — positioning tasks by urgency/weight
on a radial timeline with draggable checkpoints — has no UI at all. This
spec builds that UI and the session/alarm data model it needs; it does not
change how `canvas_event_type` is computed (untouched).

## Data model

```
canvas_sessions
  id             UUIDv7 PK
  user_id        String(36)
  opened_at
  closed_at      nullable
  item_count     Integer default 0

canvas_items
  id                UUIDv7 PK
  canvas_session_id  String(36)
  event_id           String(36)
  user_id            String(36)
  label              Text nullable        -- denormalized snapshot? see note below
  canvas_event_type   String(16)          -- copied from the event at placement time
  attention_class     String(16)
  r                  Numeric(4,3)         -- 0..1, radial distance (center=urgent per issue body)
  theta              Numeric(6,3)         -- degrees or radians, implementer's call — pick one and be consistent, degrees is more debuggable
  attention_weight    Numeric(4,3)
  zoom_count          Integer default 0
  zoom_total_delta    Numeric(8,3) default 0
  zoom_mean_delta      Numeric(8,3) default 0   -- derived, could be computed on read instead of stored — implementer's call
  status              String(16)          -- "placed" | "dismissed"
  placed_at
  last_moved_at        nullable
  dismissed_at          nullable

canvas_alarms
  id               UUIDv7 PK
  canvas_item_id    String(36)
  user_id           String(36)
  alarm_class        String(24)   -- "passive_check" | "focus_checkpoint" | "break" | "refresh"
  label             String(80) nullable
  offset_minutes     Integer      -- relative to the event's start, can be negative (before) or positive
  fires_at          DateTime
  handle_position     Numeric(4,3)  -- where on the radial line the draggable handle sits, independent of r/theta
  status            String(16)    -- "pending" | "fired" | "acknowledged" | "snoozed" | "dismissed"
  fired_at          nullable
  acknowledged_at    nullable
  snooze_minutes     Integer nullable
  snoozed_until       DateTime nullable

canvas_position_history
  id             UUIDv7 PK
  canvas_item_id  String(36)
  user_id         String(36)
  r_before / theta_before
  r_after / theta_after
  moved_at
```

`label` on `canvas_items`: **do not** duplicate the event's encrypted title
here in plaintext. Either omit `label` entirely and have the frontend join
against the event it already has loaded (the canvas is always viewing a set
of events the user already fetched via the normal, decrypted `/events`
call), or store `label_enc` with the same field crypto as everything else.
Prefer omitting it — the canvas is a *view* over existing events, not a
parallel data source, so there's no reason to persist the title twice.

## Architecture

- `Models/canvas.py` — the four tables above (or split into
  `canvas_session.py`/`canvas_item.py`/`canvas_alarm.py` if that reads
  better; this codebase splits one model per file elsewhere, e.g.
  `pomodoro.py` holds three related tables together, so grouping is fine).
- `Repositories/canvas_repo.py` — session CRUD, item placement/move/dismiss,
  alarm CRUD.
- `Services/canvas_service.py`:
  - `open_session(session, user_id) -> CanvasSessionOut`.
  - `place_item(session, user_id, canvas_session_id, event_id, r, theta) ->
    CanvasItemOut` — validates the event belongs to the user, snapshots its
    current `canvas_event_type`/`attention_class`, derives
    `attention_weight` (a pure function of `r` + `attention_class`, lives in
    `Pipelines/` since it's deterministic math, not I/O).
  - `move_item(session, user_id, item_id, r, theta)` — writes a
    `canvas_position_history` row, updates the item's `zoom_*` aggregates if
    the move includes a zoom delta, updates `last_moved_at`.
  - `create_alarm` / `acknowledge_alarm` / `snooze_alarm`.
- **API**: `POST /canvas/sessions`, `POST /canvas/sessions/{id}/items`,
  `PATCH /canvas/items/{id}` (position updates), `POST
  /canvas/items/{id}/alarms`, `PATCH /canvas/alarms/{id}` (ack/snooze).
- **Frontend** — the actual new surface, a fifth nav-adjacent view (or a
  modal/overlay launched from the calendar, implementer's call):
  - Canvas rendering via `<canvas>` + a small hand-rolled r/theta layout
    (per the artifact/graphics guidance this repo's agents follow elsewhere:
    reach for `<canvas>`/WebGL over hand-authored SVG path data for anything
    generative).
  - Draggable item handles update `r`/`theta` optimistically, PATCH on
    drag-end (not on every frame).
  - Alarm handles are separate draggable elements along an item's radial
    line, per the issue's "multi-alarm placement" framing.

## Non-goals

- No automated placement suggestion (r/theta is user-dragged in this spec;
  an AI-suggested starting position is a future enhancement, not required
  for v1).
- Does not change `assign_canvas_type`/`canvas_event_type` computation.
- `canvas_position_history` is write-only bookkeeping in this spec — no
  "replay my drag history" UI required to ship.

## Acceptance criteria

- [ ] Placing an event on the canvas creates one `canvas_items` row with a
      snapshotted `canvas_event_type` matching the event's current value at
      placement time.
- [ ] Moving an item persists a `canvas_position_history` row and updates
      `r`/`theta`/`last_moved_at` on the item.
- [ ] `attention_weight` derivation is a pure, unit-tested function
      (deterministic given `r` + `attention_class`, no DB access).
- [ ] Creating an alarm with a negative `offset_minutes` (before the event)
      and a positive one (after) both compute `fires_at` correctly relative
      to the event's `start_at`.
- [ ] Dismissing a canvas item does not delete or modify the underlying
      event — the canvas is provably a view, not a second source of truth.
- [ ] No plaintext event title is stored on `canvas_items` — a live-DB-read
      test confirms this, matching the pattern used for encrypted fields
      elsewhere.
