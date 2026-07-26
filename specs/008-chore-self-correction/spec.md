# Spec 008 — Chore self-correction: history, healing log, drift-triggered rebalancing (GitHub #18)

**Status:** proposed — architecture + acceptance criteria only, not yet implemented.
**Depends on:** a real completion/missed-detection pass, which does not exist
yet (see gap below) — this spec includes building it, it isn't a prerequisite
someone else owns.

## Problem

`ChoreOccurrence.status` already has `missed` and `healed` values in the
`OccurrenceStatus` enum (`Schemas/schedule.py`) — but nothing in
`schedule_service.py` ever transitions an occurrence into either state.
Today an occurrence only ever moves `proposed → scheduled` (on apply); once
scheduled, nothing checks whether its window passed without the linked event
being completed. So "chores drift when occurrences are missed" is currently
true by omission, not by a broken correction mechanism — there's no
detection at all yet. This spec has two parts: (1) the missing
missed-detection pass, and (2) the healing/history logging on top of it that
issue #18 actually asked for.

## Data model

```
chore_n_history
  id                  UUIDv7 PK
  chore_id            String(36)
  user_id             String(36)
  n_before            Integer
  n_after             Integer
  reason              String(32)   -- "manual" | "healing" | "entropy" (spec 012 writes here too)
  schedule_run_id      String(36) nullable
  recorded_at

schedule_healing_log
  id                     UUIDv7 PK
  user_id                String(36)
  schedule_run_id         String(36)
  trigger                 String(32)   -- "missed_threshold" | "manual"
  occurrences_missed      Integer
  occurrences_healed      Integer
  n_adjustments           Integer
  drift_rate              Numeric(6,4)   -- missed / (missed + completed) over the lookback window
  healed_at
```

Both append-only, no soft delete needed (history logs aren't edited or
removed).

## Architecture

**Part 1 — missed-detection (the actual gap).** A periodic pass (same shape
as the existing `purge_service.run_purge` background task wired in
`main.py`'s lifespan — reuse that pattern, don't invent a second scheduling
mechanism) that:
- Finds `ChoreOccurrence` rows with `status == "scheduled"`, linked
  `event_id` set, whose `proposed_end_at` has passed.
- If the linked event's `status` is `completed` → occurrence becomes
  `completed`. If the event was deleted or its `status` never left
  `scheduled` past the window → occurrence becomes `missed`.
- This pass is pure bookkeeping, no chore-parameter changes — part 2 reads
  its output.

**Part 2 — drift detection + healing**, `Services/chore_healing_service.py`:
- `compute_drift(session, user_id, chore_id, lookback_days=28) -> float` —
  `missed / (missed + completed)` over recent occurrences for one chore.
  Pure once given the counts; the counting query itself lives in
  `Repositories/schedule_repo.py` (or wherever occurrence queries already
  live) as a plain aggregate `SELECT`.
- `heal_if_needed(session, user_id, chore_id, schedule_run_id) ->
  HealResult | None` — if `compute_drift(...)` crosses a threshold (e.g.
  `> 0.4`, i.e. more than 40% missed recently), nudge `ChoreDefinition.n_current`
  *toward* `n_original` bounded by `n_min`/`n_max` (a chore that's
  chronically missed at `n_current=3` days should relax toward its original
  cadence, not tighten further) — write a `chore_n_history` row with
  `reason="healing"`, and roll the outcome into one `schedule_healing_log`
  row per triggering run (not per chore — one row aggregates all chores
  healed in that pass, matching the table's `occurrences_healed`/
  `n_adjustments` being pass-level counters).
- Call site: end of the missed-detection pass above, once per user per pass,
  iterating chores with at least one occurrence counted in the lookback
  window.

**Explicitly distinct from spec 012 (Chore Entropy)**: this spec answers "am
I keeping up with the plan as scheduled?" (drift = missed vs. completed);
spec 012 answers "is the plan's cadence right for how fast the chore
actually needs doing?" (entropy = observed need vs. scheduled `n`). Both
write to `chore_n_history` with different `reason` values and can coexist —
build in either order, they don't share code beyond that table.

## Non-goals

- No user-facing "why did my chore's frequency change" UI in this spec (the
  `chore_n_history` log is queryable via a future `GET
  /chores/{id}/history` endpoint, not required to land with this spec).
- No retroactive healing of occurrences that were missed before this spec
  shipped — healing only acts on occurrences the new detection pass itself
  observes going forward.

## Acceptance criteria

- [ ] The missed-detection pass is a unit-testable pure function given a
      list of `(occurrence, linked_event_status, now)` tuples → transition
      decisions, with the actual DB read/write as a thin wrapper (same
      split as the MC scheduler: pure core, I/O shell).
- [ ] An occurrence whose window passed with its event still `completed`
      transitions to `completed`; one whose event was deleted or never
      completed transitions to `missed`.
- [ ] `compute_drift` returns 0.0 for an all-completed history and 1.0 for
      an all-missed history; unit-tested against hand-built occurrence sets.
- [ ] A chore crossing the drift threshold gets `n_current` moved toward
      `n_original` within `[n_min, n_max]`, and exactly one
      `chore_n_history` row + one `schedule_healing_log` row is written per
      triggering pass.
- [ ] A chore below the threshold is untouched — no spurious history rows on
      every pass for chores that are on track.
