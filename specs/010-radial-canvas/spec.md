# Spec 010 — Radial Canvas: timer/stopwatch placement view (GitHub #20)

**Status:** proposed — architecture + acceptance criteria only, not yet implemented.
**Depends on:** spec 005 (`attention_classes.default_r`/`default_alarm_class`)
for sensible defaults when a timer isn't linked to an event; functions
without it (fall back to literals) but is cleaner built after.
**Revision note:** this replaces the first draft of spec 010, which modeled
the canvas as a read-only *view* over existing events. Direction: the canvas
is its own interface built around a new, directly-created primitive — a
timer or stopwatch — not a projection of the calendar.

## Problem

`canvas_event_type` is computed on every event today
(`dispatch_maps/canvas_type.py::assign_canvas_type`) but is never rendered
as anything beyond a read-only text badge in the edit-event drawer. Separately,
there is no lightweight, ad-hoc timing tool in the app at all — pomodoro
sessions (`Components/focus/session-timer.tsx`) are tightly bound to a
specific calendar event and the 40-minute break rule; there's no "just start
a stopwatch for this" or "give me a 10-minute timer" primitive independent
of the event model. The Radial Canvas is that tool: its own interface where
the core object is a **timer or stopwatch**, placed radially, directly
CRUD-able by clicking it.

## Core interaction (the part to build first)

1. User opens the Canvas page and adds a **timer** (counts down from a set
   duration) or a **stopwatch** (counts up from zero) — this is the primary
   creation action, not a byproduct of placing an existing event.
2. The new timer/stopwatch appears immediately on the canvas ("dynamically
   appended"), positioned at a default `r`/`theta` the user can drag to
   adjust.
3. Every timer/stopwatch renders **title + MM:SS**, live-updating locally
   (client-side interval against a server timestamp, not a per-second
   network round-trip — same principle as `session-timer.tsx`'s existing
   `mm:ss` formatter, reused here rather than rewritten).
4. **Clicking** a timer/stopwatch opens it for CRUD: edit its title, edit
   its duration (timer mode), start/pause/reset it, or delete it outright.

A timer/stopwatch *may* optionally link back to a calendar event (for
context and to inherit `attention_class`/`canvas_event_type`-driven
placement defaults), but linkage is optional, not required — most timers on
this canvas will be created directly and never touch the events table at
all. This is the key architectural change from the first draft: `canvas_items`
is no longer a snapshot/view of `events`, it's a first-class CRUD entity in
its own right.

## Data model

```
canvas_items
  id                 UUIDv7 PK
  user_id             String(36)
  title_enc           Text                 -- own encrypted title (AES-GCM, same field crypto as event titles) — NOT copied from an event
  mode               String(16)            -- "timer" | "stopwatch"
  duration_seconds    Integer nullable      -- timer mode only: the countdown target
  accumulated_seconds  Integer default 0    -- frozen elapsed total while paused
  started_at          DateTime nullable     -- set while running; null while paused. Live value = accumulated_seconds + (now - started_at) if running
  status             String(16)            -- "running" | "paused" | "completed"
  event_id            String(36) nullable   -- optional link to a calendar event
  attention_class      String(16)           -- user-chosen if event_id is null, else inherited at link time (a snapshot, not a live join — see note)
  canvas_event_type    String(16) nullable   -- only meaningful if event-linked; null for freestanding timers
  r                  Numeric(4,3)          -- 0..1 radial distance, user-dragged (center=urgent, per the original issue framing)
  theta              Numeric(6,3)          -- degrees, user-dragged
  created_at / updated_at / deleted_at    -- standard soft-delete CRUD, unlike the first draft's session-scoped "dismissed_at"

canvas_position_history
  id             UUIDv7 PK
  canvas_item_id  String(36)
  user_id         String(36)
  r_before / theta_before
  r_after / theta_after
  moved_at

canvas_alarms   -- unchanged in shape from the first draft, now attached to a
                -- timer/stopwatch item instead of an event-snapshot item
  id               UUIDv7 PK
  canvas_item_id    String(36)
  user_id           String(36)
  alarm_class        String(24)   -- "passive_check" | "focus_checkpoint" | "break" | "refresh"
  label             String(80) nullable
  offset_seconds     Integer      -- relative to the item's start/duration; can be negative or positive
  fires_at          DateTime
  status            String(16)    -- "pending" | "fired" | "acknowledged" | "snoozed" | "dismissed"
  fired_at / acknowledged_at / snoozed_until  nullable
```

`canvas_sessions` from the first draft is **dropped**. It modeled the canvas
as something you "open" and "close" per working session; a directly-CRUD-able
list of persistent timer/stopwatch objects doesn't fit that shape — you don't
"open a session" to see your to-dos or your chores either. The canvas is
simply "the current set of timers/stopwatches the user has going," queried
like any other resource.

`attention_class` snapshot vs. live join: when a timer is linked to an
event, its `attention_class` is copied in at link time, not joined live on
every read. If the underlying event's attention class changes later, the
canvas item keeps its placement until the user re-links or manually repositions
— avoids a surprising jump in the canvas layout from an unrelated edit
elsewhere in the app.

## Architecture

- `Models/canvas.py` — `CanvasItem`, `CanvasPositionHistory`, `CanvasAlarm`.
- `Repositories/canvas_repo.py` — `list_for_user`, `get_item`, `add_item`,
  alarm CRUD.
- `Services/canvas_service.py`:
  - `create_timer(session, user_id, data_key, title, mode, duration_seconds?,
    r, theta, event_id?) -> CanvasItemOut` — if `event_id` given, validates
    ownership and snapshots `attention_class`/`canvas_event_type`; else
    `attention_class` comes from the request (client offers a picker,
    defaulting per spec 005's `attention_classes` if available).
  - `start_item` / `pause_item` / `reset_item` — pure transitions on
    `status`/`started_at`/`accumulated_seconds`:
    - start: `status="running"`, `started_at=now`.
    - pause: `status="paused"`, `accumulated_seconds += (now - started_at)`,
      `started_at=None`.
    - reset: `status="paused"`, `accumulated_seconds=0`, `started_at=None`.
    - The **elapsed-seconds arithmetic itself** (`live_elapsed(item, now) ->
      int`) is a pure function taking the persisted fields + a timestamp —
      unit-testable without touching a clock in real time.
  - `edit_item(session, user_id, item_id, title?, duration_seconds?, r?,
    theta?)` — the CRUD "update" path from clicking an item.
  - `delete_item(session, user_id, item_id)` — soft delete. **Does not**
    touch the linked event, if any — same "canvas never mutates the
    calendar" invariant as the first draft.
  - `move_item` — same as the first draft: writes `canvas_position_history`,
    updates `r`/`theta`.
  - Alarm CRUD, offsets computed relative to the item's `started_at`/
    `duration_seconds` instead of an event's `start_at` (the item may not
    have a linked event at all).
- **API**:
  - `GET /canvas/items` — the user's current timers/stopwatches.
  - `POST /canvas/items` — create (the core action).
  - `PATCH /canvas/items/{id}` — title/duration/position edits.
  - `POST /canvas/items/{id}/start` · `/pause` · `/reset`.
  - `DELETE /canvas/items/{id}`.
  - `POST /canvas/items/{id}/alarms`, `PATCH /canvas/alarms/{id}` (ack/snooze).
- **Frontend** — its own page, own nav item (the app is already at 4-5 nav
  items after issues #12/#25; group Canvas with Routines under a "More" menu
  if the header gets crowded, implementer's call, but it does **not** live
  inside the calendar or focus pages):
  - Canvas rendering via `<canvas>` with a hand-rolled r/theta layout (this
    repo's convention: reach for `<canvas>`/WebGL over hand-authored SVG
    path data for anything generative).
  - Each item renders **title + MM:SS**, ticking locally every second while
    `status === "running"` (a `setInterval` computing `live_elapsed`
    client-side against the item's `started_at`/`accumulated_seconds`, the
    same pattern `session-timer.tsx` already uses for the pomodoro clock —
    reuse its formatter, don't write a second one).
  - Clicking an item opens an inline edit card (title field, duration field
    for timer mode, Start/Pause/Reset, Delete) — the CRUD surface the
    direction calls for.
  - Dragging updates `r`/`theta` optimistically, `PATCH` on drag-end.
  - "New timer" / "New stopwatch" are the two primary creation actions,
    front and center on the page — this is the core flow, not a secondary
    affordance.

## Non-goals

- No automated placement suggestion — `r`/`theta` is user-dragged.
- Does not change `assign_canvas_type`/`canvas_event_type` computation.
- A timer completing (countdown reaches 0) does not auto-create a
  notification/OS-level alert in this spec — `status="completed"` is a data
  state; a toast/sound is a frontend nice-to-have, not a blocking
  acceptance item.

## Acceptance criteria

- [ ] Creating a timer or stopwatch appends it to the canvas immediately and
      it's independently queryable/editable without any linked event.
- [ ] `live_elapsed` is a pure, unit-tested function: given
      `(accumulated_seconds, started_at, status, now)`, returns the correct
      elapsed seconds for running, paused, and just-reset states.
- [ ] Clicking an item and editing its title/duration persists via `PATCH`;
      deleting it removes it from the list and — if it was event-linked —
      leaves the underlying event completely untouched (verified: the event
      still exists, unmodified, via `GET /events/{id}`).
- [ ] Start → wait → Pause → Reset produces the exact expected
      `accumulated_seconds` at each step (an integration test driving the
      three transitions in sequence).
- [ ] A timer's `duration_seconds` reaching 0 while running transitions its
      `status` to `"completed"` (checked lazily on read/tick, not via a
      background poller — same "no I/O in the hot path" discipline as the
      rest of this backend).
- [ ] No plaintext title is stored anywhere outside `title_enc` — live-DB-read
      test, same pattern as `test_titles_encrypted_at_rest`.
