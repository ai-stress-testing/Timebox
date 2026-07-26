# Spec 012 — Chore Entropy: decay-rate tracking (GitHub #24)

**Status:** proposed — architecture + acceptance criteria only, not yet implemented.
**Depends on:** nothing structurally; shares `chore_n_history` with spec 008
(different `reason` values — see "Distinct from spec 008" below). Build in
either order.

## Problem

Chores don't decay at their scheduled interval. Floors are visibly dirty by
**day 4** but the schedule runs them **every 7** — so the plan itself is
wrong, not just drifting. `ChoreDefinition` today stores only the
**scheduled** cadence (`n_current`, bounded by `n_min`/`n_max`) plus
`last_completed_at`; nothing captures how fast a chore actually needs
doing. Chore entropy learns each chore's real "soil rate" and surfaces the
mismatch so the plan can be corrected toward reality.

**Distinct from spec 008 (chore self-correction / healing)**: spec 008 asks
"am I keeping up with the plan as scheduled?" (drift = occurrences missed
vs. completed). This spec asks a different question: **is the plan's
cadence right for how fast this chore actually decays?** A chore can have
zero missed occurrences (spec 008 sees no drift at all) and still be
badly under-scheduled if the user is diligently doing it every 7 days on
schedule while it's visibly gross by day 4 — spec 008's signal is silent on
that; entropy's isn't.

## Signals learned from

1. **Completion-state capture** — when a chore is marked done, optionally
   record how overdue it already was in one tap: `fresh | due | overdue |
   well_overdue` (or a 1–5 soil level).
2. **Actual completion gaps** — the real interval between completions (from
   `last_completed_at`). If floors are consistently done on ~day 4 of a
   7-day schedule, observed cadence ≈ 4.
3. *(optional)* an "it's already dirty" flag raised any time, decoupled from
   completion.

## Data model

- New append-only `chore_completions`:
  `id, chore_id, user_id, completed_at, days_since_previous, soil_state
  (enum), notes_enc?` — `notes_enc` uses the same field crypto as event
  titles if free-text notes are allowed; the `soil_state` enum itself is not
  sensitive (four fixed labels) and stays plaintext, same reasoning as
  `EventStatus`/`AttentionClass` staying plaintext enums today.
- Add to `chore_definitions` (a `chore_entropy` sibling table, one row per
  chore, rather than more columns bolted onto `ChoreDefinition` — keeps the
  Welford state next to the thing it belongs to and out of the hot-path
  chore-read query):
  `chore_id, decay_days_mean, decay_days_m2, decay_sample_count` (Welford
  running estimate of the real cadence — reuses the exact
  `welford_update` pure function from spec 007's `Pipelines/duration_stats.py`,
  applied to "days between completions" instead of "minutes per session" —
  same math, different quantity, don't write a second Welford implementation),
  `entropy_ratio` (= `n_current / decay_days_mean`), `last_entropy_at`.
- `entropy_ratio > 1` ⇒ **under-scheduled** (dirty before it's due — the
  floors case). `< 1` ⇒ **over-scheduled** (still clean when done).

## Architecture

- `Models/chore_entropy.py` — `ChoreCompletion` + `ChoreEntropy` tables above.
- `Repositories/chore_entropy_repo.py` — `add_completion`,
  `get_entropy(chore_id)`, `upsert_entropy`.
- `Services/chore_entropy_service.py`:
  - `record_completion(session, user_id, chore_id, soil_state, completed_at)`
    — writes a `chore_completions` row (`days_since_previous` computed from
    the chore's own `last_completed_at` before it's overwritten), applies
    `welford_update` (imported from spec 007's pipeline — a real dependency,
    not just a shared pattern) to `decay_days_mean`/`decay_days_m2`,
    recomputes `entropy_ratio`, then updates `ChoreDefinition.last_completed_at`/
    `next_due_at` as the existing completion path already does.
  - `chore_health(entropy: ChoreEntropy, chore: ChoreDefinition) -> str` —
    pure function, one of `"on_track" | "under_scheduled" |
    "over_scheduled"` from `entropy_ratio` thresholds (e.g. `>1.15` /
    `<0.85` bands around 1.0 to avoid flapping on noise).
  - `tighten_to_real_rate(session, user_id, chore_id)` — moves `n_current`
    toward `decay_days_mean`, bounded by `n_min`/`n_max`, writes a
    `chore_n_history` row with `reason="entropy"` (spec 008 uses `"healing"`
    for the same table — both readable from one history view, distinguished
    by `reason`).
  - Feed `entropy_ratio` into `ChoreDefinition.mc_weight` (same column spec
    007 writes to for duration-based weighting) as a second input — an
    under-scheduled chore should be prioritized by the MC scheduler even if
    its *duration* estimate is accurate; combine rather than overwrite
    (implementer's call on the exact blend, e.g. average or max of the two
    weight signals — document whichever is chosen in the PR, not guessed at
    here).
- **API**:
  - `POST /chores/{id}/complete { soil_state?, completed_at? }` → log
    completion, update entropy, refresh `last_completed_at`/`next_due_at`.
    (Note: there may not be an existing "complete a chore" endpoint at all
    today — check `Routers/chores.py` at implementation time; if completion
    currently only happens implicitly via a scheduled event's status, this
    endpoint is new plumbing, not a modification of existing plumbing.)
  - `GET /chores` response gains entropy fields (decay estimate, ratio,
    health) — additive to `ChoreOut`.
  - `GET /chores/{id}/entropy` → detail (completion history + samples).
  - `POST /chores/{id}/tighten` → applies `tighten_to_real_rate`.
- **Frontend**: a per-chore health chip (on-track/under/over, plain
  language: "needs doing ~every 4 days, scheduled every 7") in the chores
  list, and a "Tighten to real rate" button that appears only when
  under-scheduled. Optional one-tap soil-state capture on the existing
  chore-completion interaction, wherever that lives today.

## Non-goals

- No change to the MC scheduler's core algorithm — `mc_weight` is an input
  it already reads; this spec only changes what feeds that input, same as
  spec 007.
- No soil-state capture requirement — it's explicitly optional per the
  signals list; `decay_days_mean` still updates from completion gaps alone
  if the user never taps a soil state.

## Acceptance criteria

- [ ] Repeatedly completing a chore earlier than its schedule drives
      `decay_days_mean` below `n_current` and flags it **under-scheduled**.
- [ ] The health indicator renders per chore with the plain-language rate
      comparison ("needs doing ~every N days, scheduled every M").
- [ ] "Tighten to real rate" adjusts `n_current` within `[n_min, n_max]`
      bounds; the next schedule run reflects it; a `chore_n_history` row
      with `reason="entropy"` is written.
- [ ] The Welford entropy update reuses spec 007's `welford_update` function
      verbatim (not a re-implementation) — a unit test constructs the same
      known sequence used in spec 007's test and confirms identical
      mean/variance output for the "days between completions" quantity.
- [ ] A chore with `entropy_ratio` within the on-track band is not flagged,
      even after several completions — no false positives from normal
      variance.
