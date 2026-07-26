# Spec 012 — Chore Entropy: decay-rate tracking (GitHub #24)

**Status:** proposed — architecture + acceptance criteria only, not yet implemented.
**Depends on:** spec 007's `welford_update` (`Pipelines/duration_stats.py`) —
a real code dependency, reused verbatim, not reimplemented. Shares
`chore_n_history` with spec 008 (different `reason` values). Build any of
the three in any order; wire the cross-references at whichever point they
all exist.
**Revision note:** simplified from the first draft's health-chip +
discrete-soil-state-buttons + separate "tighten" button down to a single
slider interaction, per direction. The underlying Welford/entropy math is
unchanged; the UI and the exact recommendation formula are new.

## Problem

Chores don't decay at their scheduled interval. Floors are visibly dirty by
**day 4** but the schedule runs them **every 7** — so the plan itself is
wrong, not just drifting. `ChoreDefinition` today stores only the
**scheduled** cadence (`n_current`, bounded by `n_min`/`n_max`) plus
`last_completed_at`/`next_due_at`; nothing captures how fast a chore
actually needs doing, and the chores page never surfaces the gap between
"due" and "now" at all.

**Distinct from spec 008 (chore self-correction / healing)**: spec 008 asks
"am I keeping up with the plan as scheduled?" (drift = occurrences missed
vs. completed). This spec asks a different question: **is the plan's
cadence right for how fast this chore actually decays?** A chore can have
zero missed occurrences and still be badly under-scheduled if the user is
diligently doing it on schedule while it's visibly gross days before that
schedule comes around — spec 008's signal is silent on that; entropy's isn't.

## The interaction: one slider, not four buttons

Every chore on the chores page gets **one slider**, replacing the first
draft's separate soil-state taps + health chip + "tighten" button:

- The chore row shows **days until due** (`next_due_at` minus today —
  already stored on `ChoreDefinition`, just never rendered until this spec)
  alongside the slider.
- The slider's track spans a bounded cadence range (`n_min`..`n_max`, the
  same bounds `n_current` is already clamped to). Its handle rests, by
  default, at the **recommended cadence** — a whole number computed from
  observed completion history (see algorithm below), not at `n_current`
  itself, so the gap between "where it's scheduled" and "where the data
  says it should be" is visually immediate.
- Dragging the slider and releasing it directly sets `n_current` to that
  value (a `PATCH`, same as any other chore edit) — this **is** the
  "tighten to real rate" action from the first draft, just continuous
  instead of a discrete button.
- No separate one-tap soil-state buttons. If a future spec wants a richer
  completion-time signal, it can extend `chore_completions` below — this
  spec's v1 learns entirely from **completion gaps**, which requires no new
  interaction beyond however chores are already marked done today.

## Data model

```
chore_completions          -- append-only
  id                  UUIDv7 PK
  chore_id             String(36)
  user_id              String(36)
  completed_at
  days_since_previous   Numeric(6,2)   -- computed from the chore's prior last_completed_at

chore_entropy               -- one row per chore, sibling table (keeps Welford
                             -- state out of the hot-path chore-read query)
  chore_id             String(36) PK / unique
  decay_days_mean       Numeric(6,3)   -- Welford mean of days_since_previous
  decay_days_m2         Numeric(10,4)  -- Welford M2
  decay_sample_count     Integer default 0
  recommended_n          Integer nullable   -- cached "new split," recomputed on every completion
  last_computed_at
```

`entropy_ratio` from the first draft (`n_current / decay_days_mean`) is kept
as a **derived** value computed on read, not stored — `recommended_n` is the
number that actually matters for the UI (the slider's default position), and
storing both invites them to drift out of sync.

## The recommendation algorithm

```python
# app/Pipelines/chore_entropy.py
from app.Pipelines.duration_stats import welford_update  # spec 007, reused verbatim

def recommended_split(
    n_current: int,
    expectation_days: float,
    sample_count: int,
    n_min: int,
    n_max: int,
    prior_strength: float = 3.0,
) -> int:
    """Blend the observed expectation with the currently scheduled cadence,
    trusting the observation more as samples accumulate (Bayesian-shrinkage
    style: weight -> 1 as sample_count grows, weight -> 0 with few samples,
    so a chore with one weird early completion doesn't immediately swing the
    recommendation).
    """
    weight = sample_count / (sample_count + prior_strength)
    blended = weight * expectation_days + (1 - weight) * n_current
    return min(max(round(blended), n_min), n_max)
```

This is the "expectation and weighted average... nearest whole number"
mechanism precisely: `expectation_days` is `decay_days_mean` (the Welford
running mean — the same pure core spec 007 already establishes, applied to
"days between completions" instead of "minutes per session"), the weighted
average blends it against the current schedule, and `round()` produces the
whole-number "split." Pure function, zero I/O, unit-tested directly against
hand-picked `(n_current, expectation, sample_count)` triples.

## Architecture

- `Models/chore_entropy.py` — `ChoreCompletion` + `ChoreEntropy` tables.
- `Repositories/chore_entropy_repo.py` — `add_completion`, `get_entropy`,
  `upsert_entropy`.
- `Pipelines/chore_entropy.py` — `recommended_split` above (pure, imports
  `welford_update` from spec 007 rather than duplicating it).
- `Services/chore_entropy_service.py`:
  - `record_completion(session, user_id, chore_id, completed_at)` — computes
    `days_since_previous` from the chore's current `last_completed_at`
    (before it's overwritten), writes a `chore_completions` row, applies
    `welford_update` to `chore_entropy`'s Welford fields, calls
    `recommended_split(...)` and caches the result on `recommended_n`, then
    proceeds with the existing completion path (`last_completed_at`/
    `next_due_at` refresh — whatever that path is today; if there's no
    explicit "complete a chore" endpoint yet, this spec adds one, see API).
  - `days_until_due(chore: ChoreDefinition, now: date) -> int` — pure,
    `(next_due_at - now).days`, can be negative (overdue). This is the
    chores-page day-awareness the direction calls for; trivial, but it
    needs to exist as a named, tested function rather than inline frontend
    date math, since spec 008's missed-detection pass likely wants the same
    calculation.
  - Feed `recommended_n` vs `n_current` into `ChoreDefinition.mc_weight`
    alongside spec 007's duration-based signal (same column, same
    "combine, don't overwrite" note as the first draft — implementer's call
    on the exact blend).
- **API**:
  - `POST /chores/{id}/complete { completed_at? }` → log completion, update
    entropy, refresh `last_completed_at`/`next_due_at`, return the chore
    with its new `recommended_n`. (Check `Routers/chores.py` at
    implementation time — if chore completion currently only happens
    implicitly via a scheduled event's status, this is new plumbing.)
  - `GET /chores` response gains `days_until_due` and `recommended_n` —
    additive to `ChoreOut`, both needed by the slider on first render (no
    second round-trip to place the handle).
  - `PATCH /chores/{id} { n_current }` — **already exists** as a plain chore
    edit; the slider's release action is not new API surface, just an
    existing endpoint driven by a new control.
- **Frontend**: `ChoreList`/`ChoreRow` (`Components/chores/chore-list.tsx`)
  gains the "due in N days" text (from `days_until_due`, already computable
  client-side from the existing `next_due_at` field even before the backend
  work lands, but centralizing it server-side keeps the "how many days" math
  in one tested place per the point above) and a slider control
  (`ui/slider.tsx` — new primitive if one doesn't exist yet) bounded
  `[n_min, n_max]`, defaulting to `recommended_n`, `PATCH`-ing `n_current` on
  release.

## Non-goals

- No change to the MC scheduler's core algorithm — `mc_weight` is an input
  it already reads; this spec only changes what feeds that input.
- No discrete soil-state capture UI — dropped in favor of the slider, see
  above. `decay_days_mean` learns entirely from completion-gap timing.
- No slider-driven *mid-cycle* signal ("it's dirty right now, before I've
  completed it") in v1 — the slider acts on completion history only;
  a live "flag it dirty now" input is a plausible fast-follow, not required
  to ship.

## Acceptance criteria

- [ ] `recommended_split` is a pure, unit-tested function: a chore with 1
      early completion barely moves off `n_current` (low `weight`); the same
      chore after 10 consistent early completions moves close to
      `expectation_days` (`weight` near 1) — proves the shrinkage behaves as
      described, not just that it compiles.
- [ ] `recommended_split`'s output is always clamped to `[n_min, n_max]`,
      even when the raw blended value would fall outside those bounds.
- [ ] Repeatedly completing a chore earlier than its schedule drives
      `decay_days_mean` down and `recommended_n` below `n_current`.
- [ ] `GET /chores` returns `days_until_due` matching a hand-computed value
      for a chore with a known `next_due_at`, including the negative
      (overdue) case.
- [ ] Dragging the chores-page slider and releasing it calls the existing
      `PATCH /chores/{id}` with the new `n_current` — no new mutation
      endpoint needed for the accept action itself.
- [ ] The Welford update reuses spec 007's `welford_update` verbatim — a
      unit test constructs the same known sequence used in spec 007's test
      and confirms identical mean/variance output for this spec's quantity.
