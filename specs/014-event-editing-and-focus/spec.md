# Spec 014 — Focus is not a page: edit-event as the after-the-fact interface (GitHub #9)

**Status:** implemented. This is a decision record, not a forward-looking
architecture doc — the design question is resolved and the concrete gap it
identified is shipped; written for the historical record and so future specs
(005–013) don't reopen the question.

## The question

Issue #9 originally asked to "make the edit event feature contain more
feature-rich content... the current focus page or view is going to be
reworked... more feature-rich content based off of the data structures." That
was two things tangled together: (1) three concrete, named quick actions
(move to tomorrow, extend duration, log an actual), and (2) an open-ended
"rework the focus page" direction with no specified shape.

## The decision

**Focus does not get its own interface.** It stays baked into the edit-event
drawer, exactly where `estimated_minutes` already lives. This is not a
compromise — it's the correct shape given a constraint already stated in the
constitution: this system does not monitor in real time (Article I, zero
surveillance; the entire attention-monitoring track — Editor Engine,
Chronobiology — was deliberately dropped from the backlog in this same
pass). A system that doesn't watch you work has nothing to show on a live
"focus" screen beyond what pomodoro already provides during a session. What
it *can* do is let you correct the record **after the fact** — which is
exactly what `estimated_minutes`/`actual_minutes` on an event already are:
a before-guess and an after-correction, no monitoring required.

The one real gap in that model, identified during this decision: **there was
no way to say "this block was actually two things."** A user logging
`actual_minutes` on a single event can't split a 2-hour "Deep work" block
into "1 hour on the report, 1 hour on email" after the fact — the after-the-
fact editing model was incomplete without it.

## What shipped

- **Quick actions** (`Components/calendar/event-quick-actions.tsx`, sprint 1,
  issue #9 partial): move to tomorrow, extend +15m/+30m, log actual minutes
  — all direct `EventPatch` calls, no new subsystem, non-recurring events
  only (shifting a virtual occurrence would move the whole series anchor).
- **Split event** (this decision's follow-up,
  `POST /events/{id}/split`, `event_service.split_event`): splits one event
  into two adjacent events at a chosen time. The original row becomes the
  first half; a new row is created for the second half. Both halves clear
  `estimated_minutes`/`actual_minutes` — neither figure is accurate for a
  sub-span of the original block, so the user re-logs them per half rather
  than inheriting a stale number. Guarded against recurring and all-day
  events (409), and against a split point outside the event's own span
  (400). Frontend: a "Split at [time]" quick action next to the existing
  three, defaulting to the event's midpoint.

## Non-goals (explicitly rejected, not deferred)

- A standalone focus page/view showing "what you're focused on right now" —
  rejected, not deferred, because it would need real-time signal this system
  doesn't and shouldn't collect.
- Any keystroke, idle-time, or attention-monitoring signal feeding into
  event editing — same reasoning; this is the same line specs 005–013 drew
  when steering away from the Editor Engine / Chronobiology direction.

## What this doesn't foreclose

Specs 006 (`event_memory`) and 007 (`duration_profiles`) still make editing
*smarter* — prefilling estimates from history — without contradicting this
decision, because prefill-from-history is still purely after-the-fact
statistical reasoning, not live monitoring. If a future spec proposes
anything that watches a session in progress rather than record what already
happened, it should cite this decision and make the case explicitly rather
than assume the door is open.

## Acceptance criteria (already met)

- [x] Move to tomorrow, extend +15m/+30m, log actual: shipped, tested, live
      browser-verified (sprint 1).
- [x] Split event: shipped, 3 backend tests (`test_split_event_creates_two_adjacent_events`,
      `test_split_event_rejects_out_of_range_point`,
      `test_split_recurring_event_rejected`) plus a live API round-trip
      confirming the exact split boundary and cleared estimate/actual
      fields on both halves.
- [x] No new focus-page surface was built — confirmed by its absence: the
      `focus-page.tsx` that exists today is unchanged by this decision, and
      no new top-nav item was added for it (contrast with issue #12's
      "To do," which *did* get a new nav item because it's a genuinely new
      surface, not a rework of an existing one).
