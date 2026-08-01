# Spec 015 — Batch Schedule: assign many to-dos to time slots in one pass

**Status:** proposed — architecture + acceptance criteria only, not yet implemented.
**Source:** user-uploaded feature request/user-flows doc (batch scheduling
modal). Reconciled below against what issue #12 already shipped — the doc
was written generically ("Task" model, a from-scratch `scheduled_at` field)
without reference to this codebase's actual to-do funnel, so several of its
technical requirements are superseded by what already exists. Read the
"Reconciliation" section before the rest — it explains every place this
spec deviates from the uploaded doc and why.

## Problem

Scheduling a to-do today means opening `ScheduleTodoForm` per item — a
5-field form (Date, Starts, Ends, Type, Attention) — one at a time. A user
who's just brain-dumped ten to-dos has no way to place them all on today's
timeline in one pass; they must reopen the form, five fields, ten times.

## Reconciliation with what's already built

The uploaded doc proposes a `Task` model with its own `scheduled_at:
DateTime | null` and `attention_type: AttentionType` columns, decoupled from
any calendar event. That conflicts with issue #12's design, which this app
already ships and which Flow 4 of the doc itself assumes still works
("scheduled tasks appear as events in the calendar view"): a `Todo` funnels
into a **real `Event`** via `schedule_todo` — the todo gets `is_done=true` +
`scheduled_event_id` set, and the created event gets full encryption,
canvas-type auto-assignment, and every other pipeline events already have.
Adding a second, parallel "a todo can also just have a bare `scheduled_at`"
representation would mean two divergent ways to know "when is this
happening," and calendar view would only show one of them. **Decision: no
schema change to `Todo`.** Batch scheduling is a new *entry point* to the
exact same `schedule_todo` mechanism, just fired for many todos in one
request instead of one form submission per todo.

Other reconciliations:
- **`attention_type` default `"personal"`, hidden field** → Timebox's real
  enum is `AttentionClass` (`active | involved | passive`); there is no
  `"personal"` value, and introducing one would break every place that
  branches on the three real classes (canvas-type assignment, pomodoro
  applicability). The doc's own later "hidden field" note effectively asks
  to not expose this choice in v1 anyway — so this spec defaults every
  batch-scheduled event to `AttentionClass.active` (the same default
  `EventCreate`/`TodoScheduleRequest` already use) and does **not** render a
  per-task attention selector in the confirmation summary. The value stays
  editable afterward the same way any event's attention class is editable
  today (the edit-event drawer) — matching the doc's "chosen after
  assignment" intent without inventing a fourth enum value.
- **Task selection: multi-select vs. one-at-a-time.** The doc's early "User
  Flows" draft says shift-click range selection; its later, more specific
  "Technical Requirements" restatement says "Users select one task at a
  time via click." The later section is more prescriptive and is what this
  spec follows: the task dish is single-select — click a task, then either
  drag it or double-click a slot to place it, then click the next task.
- **Time grid scope**: the later section is explicit — "for only the
  current day," half-hour slots, vertical scroll only. This spec builds a
  new single-day half-hour grid, not a reuse of the existing 7-day
  `WeekGrid` (different shape entirely), though it shares `lib/time.ts`
  conventions (`day_start_hour`, wall-clock composition via
  `compose_local_iso`).
- **"Task" naming** throughout this spec means `Todo` — this app has no
  separate `Task` entity.

## User flow (as specced, reconciled)

1. On the To-do page, the user selects one or more open to-dos (checkboxes
   on `TodoList` rows — new; today's rows have no selection affordance) and
   clicks **"Batch schedule"** (a toolbar button that appears once ≥1 is
   selected; `Ctrl+Shift+S` also opens it against the current selection).
2. A **modal** opens (`role="dialog"`, `aria-modal="true"`, built on the
   existing `use_drawer_behavior` hook — it already gives focus-on-open,
   Escape-to-close, and Tab-trap, so this spec adds zero new accessibility
   plumbing, just reuses what `DeleteScopeDialog` already proves out):
   - **Top panel — time grid**: today's date, half-hour cells from
     `day_start_hour` to `day_end_hour`, vertical scroll only
     (`overflow-y-auto overflow-x-hidden`). Each cell shows a count badge
     once ≥1 task is assigned to it.
   - **Bottom panel — task dish**: the selected todos as title-truncated
     badges (10 chars + "…"), horizontal scroll only. Click one to make it
     "armed" (highlighted, ready for placement).
3. **Assign**: drag the armed task onto a grid cell (native HTML5 drag —
   `draggable`, `onDragStart`/`onDragOver`/`onDrop`, no library — the first
   use of native DnD in this codebase; everywhere else that drags today,
   like the Radial Canvas or event-drawer resize, uses pointer events, not
   HTML5 DnD, because those need continuous coordinates — a discrete
   cell-drop doesn't). Double-click a task for a fallback: a small dropdown
   of remaining slots, keyboard-operable. Assigning a task already assigned
   elsewhere **moves** it (with a brief "moved from 2:00pm" toast) rather
   than creating a duplicate — this is what "warn on duplicate row" reduces
   to for a single-select model where a task can only ever hold one slot at
   a time.
4. Dropping onto a slot whose start has already passed today: rejected
   client-side (shake animation + toast, "That time has already passed") —
   no backend round-trip for something checkable from `now` alone.
5. All of this is **in-memory only** — a local `assignments: Map<todo_id,
   iso_start>` in the modal's component state. Nothing is sent to the API
   until confirm, matching the existing `EventDraft` pattern of staging a
   full form locally before one submit.
6. **Confirm → "Schedule All"**: a summary screen lists each assignment
   ("Buy groceries → 10:30 AM") and a total count, then **one** batch
   request. On success: modal closes, toast "N tasks scheduled." Any
   per-item failures (see API below) are reported in the same toast pass
   and those todos stay in the modal, unassigned, so the user can retry
   without redoing the ones that worked.
7. **Cancel**, or closing with unsaved assignments, prompts "Save these N
   assignments or discard them?" (two buttons — Save runs the same confirm
   path, Discard closes with nothing persisted).

## Data model

No new columns. No migration (this app has none — schema is `create_all`
at boot, per constitution Article IV). Reuses `Todo.scheduled_event_id` /
`Todo.is_done` exactly as issue #12 built them.

## Architecture

- **Backend** — one new endpoint, no new tables:
  - `Schemas/todo.py`: `BatchScheduleItem { todo_id: str, start_at:
    UtcDateTime, event_type: str, attention_class: AttentionClassField =
    AttentionClass.active }` (attention defaults silently, per the
    reconciliation above — no client has to send it), `BatchScheduleRequest
    { items: list[BatchScheduleItem] }` (`min_length=1`),
    `BatchScheduleResult { todo_id: str, ok: bool, event: EventOut | None,
    detail: str | None }`, `BatchScheduleResponse { results:
    list[BatchScheduleResult] }`.
  - `Services/todo_service.py::batch_schedule` — loops `items`, calling the
    **existing** `schedule_todo` per item (end_at derived from the todo's
    `estimated_minutes` exactly like `schedule_todo` already does, default
    30 min if unset — same constant `ScheduleTodoForm` already uses on the
    frontend). Each item is caught independently: a `TodoError` (404
    missing, 409 already scheduled) becomes one failed `BatchScheduleResult`
    without aborting the rest — items that already committed via their own
    `schedule_todo` call stay committed (each is its own transaction, same
    as calling the single-item endpoint N times, just server-side and in
    one request).
  - `Routers/todos.py`: `POST /todos/batch-schedule` → always 200 (the
    per-item `ok` flags carry failure, not the HTTP status — a batch with 8
    successes and 2 failures isn't a request failure).
  - Tests: all-success, one-of-three-fails-with-rest-committed, empty
    `items` rejected (422, `min_length=1` on the schema handles this for
    free), and a duplicate-`todo_id`-in-one-batch case (the second occurrence
    fails with 409 the same way scheduling an already-scheduled todo does,
    since the first item in the loop already set `scheduled_event_id`).
- **Frontend**:
  - `Components/todos/todo-list.tsx`: selection checkboxes + a "Batch
    schedule (N)" button, wired to open the new modal with the selected ids.
  - `Components/todos/batch-schedule-modal.tsx` (+ `time-grid-panel.tsx`,
    `task-dish.tsx` if that split reads better): the modal described above.
    New half-hour row generator alongside `visible_hours` in `lib/time.ts`
    (e.g. `half_hour_slots()` returning `{hour, minute}` pairs for
    `day_start_hour..day_end_hour`), reusing `compose_local_iso`/
    `date_input_value` for composing each slot's `start_at`.
  - `Hooks/use-todos.ts`: `use_batch_schedule()` — one mutation, invalidates
    both the todos and events query keys on success (same as
    `use_schedule_todo` already does).
  - A new `tb-shake` keyframe in `index.css`'s `@theme` block (token-driven,
    same convention as the existing `tb-pop-in`/`tb-fade-in`) for the
    past-slot-rejection feedback.
  - `zod` schemas for the batch request/response in `api-schemas.ts`, and
    every field validated with `.safeParse()` before the request goes out,
    per this app's standing rule.

## Non-goals

- No `Task`/`scheduled_at`/`attention_type` schema — see Reconciliation.
- No multi-day view in the batch grid — today only, per the doc's own
  later, more specific requirement.
- No attention-type selector in the confirmation summary in v1 — silent
  default to `active`, editable afterward via the existing event edit flow.
- Recurring todos don't exist (todos have no recurrence concept), so there's
  no batch-recurrence interaction to design here.

## Acceptance criteria

- [ ] Selecting 3 todos and batch-scheduling all 3 in one request creates 3
      real events (verified via `GET /events`) and flips `is_done`/
      `scheduled_event_id` on all 3 todos.
- [ ] One item in a batch that's already scheduled fails with `ok: false`
      while the other items in the same batch still succeed and commit.
- [ ] An empty `items` array is rejected (422) before any processing.
- [ ] Every batch-scheduled event's `attention_class` is `active` unless a
      caller explicitly overrides it — no `"personal"` value ever reaches
      the database (there's no such enum member to reach).
- [ ] The modal is keyboard-operable end-to-end without a mouse: Tab cycles
      only within the modal (`use_drawer_behavior`'s existing trap), Enter/
      Space on a task arms it, Enter/Space on a slot (or the double-click
      dropdown) assigns it.
- [ ] Dropping on a past-today slot never reaches the API — rejected
      client-side with the shake + toast.
- [ ] Assigning an already-assigned task to a new slot moves it (one
      assignment per task in local state), never creates two.
- [ ] Closing the modal with ≥1 unsaved assignment prompts Save/Discard;
      closing with zero assignments closes silently.
- [ ] Opens and renders with 20 selected todos in well under 500ms in a
      local dev build (no formal perf harness required for the prototype —
      this is a sanity bound, not a CI gate).
