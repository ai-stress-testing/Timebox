# Spec 007 — `duration_profiles`: Welford running-stats duration forecasting (GitHub #16)

**Status:** proposed — architecture + acceptance criteria only, not yet implemented.
**Depends on:** nothing to build; shares the `normalize_title`/`hash_title`
helper introduced in spec 006 (build either first, they don't block each
other structurally — 006 links `duration_profile_id` to this table's `id`
once both exist).
**Feeds:** spec 006 (`event_memory.duration_profile_id`), the existing
`ChoreDefinition.mc_weight` column (already in the schema, currently a
static `default=1.0` nobody updates), and event/todo estimate prefill.

## Problem

Timebox already logs the raw signal this needs — `Event.actual_minutes`,
`Event.estimated_minutes`, `PomodoroSession.actual_minutes` /
`meaningful_minutes` — but nothing aggregates it. `ChoreDefinition.mc_weight`
exists in the schema *today*, `default=1.0`, and is read by the Monte Carlo
scheduler, but no code path ever writes a different value — it's a dead
knob. This spec is the missing write side: a running mean/variance per
label, updated incrementally (Welford's algorithm — numerically stable, O(1)
per update, no re-scan of history), that both prefills estimates and
finally drives `mc_weight` off real data instead of a constant.

## Data model

```
duration_profiles
  id                     UUIDv7 PK
  user_id                String(36)
  label_hash             String(64) nullable  -- title_hash (spec 006's helper), for event-title profiles
  chore_id               String(36) nullable  -- for chore profiles
  attention_class        String(16) nullable

  total_sample_count     Integer default 0
  total_mean             Numeric(8,3) default 0     -- Welford mean of total minutes
  total_m2               Numeric(12,4) default 0    -- Welford M2 (sum of squared deviations)

  meaningful_sample_count Integer default 0
  meaningful_mean         Numeric(8,3) default 0
  meaningful_m2           Numeric(12,4) default 0

  dow_total_mean          Text default '{}'   -- JSON: {"0".."6": mean}, same day-of-week convention as recurrence_weekdays (Sun=0)
  dow_sample_count        Text default '{}'   -- JSON: {"0".."6": count}

  mc_weight                Numeric(6,4) default 1.0  -- mirrors ChoreDefinition.mc_weight's scale; written here, read by the scheduler
  last_updated_at
  created_at / updated_at

  unique index on (user_id, label_hash) where label_hash is not null and deleted_at is null
  unique index on (user_id, chore_id) where chore_id is not null and deleted_at is null
  check: exactly one of (label_hash, chore_id) is set
```

`residual_count` / `mean_residual_minutes` / `mean_residual_sessions` from
the original issue body are **deferred**: they require joining
`TaskResidual` chains and are a distinct enough aggregation (residual-chain
length, not single-session duration) that bolting them onto this table's
first version would blur what "one update" means. Track as a fast-follow
once the core mean/variance path is proven; not blocking.

## Architecture — the pure core

The Welford update itself must be a **pure, unit-testable function with no
I/O**, per constitution Article III ("pure-function pipelines... the Monte
Carlo scheduler performs no I/O" — this is the same discipline applied to a
new pipeline):

```python
# app/Pipelines/duration_stats.py
@dataclass(frozen=True)
class WelfordState:
    count: int
    mean: float
    m2: float

def welford_update(state: WelfordState, new_value: float) -> WelfordState:
    count = state.count + 1
    delta = new_value - state.mean
    mean = state.mean + delta / count
    delta2 = new_value - mean
    m2 = state.m2 + delta * delta2
    return WelfordState(count=count, mean=mean, m2=m2)
```

No loops, no bounds needed (single-value update, not a re-scan) — this is
the simplest possible pure core, but it still belongs in `Pipelines/` next
to `recurrence.py` and the MC scheduler, not inlined in the service, so it
gets the same isolated unit tests they do.

- `Models/duration_profile.py` — table above.
- `Repositories/duration_profile_repo.py` — `get_by_label_hash`,
  `get_by_chore_id`, `upsert`.
- `Services/duration_profile_service.py`:
  - `record_event_completion(session, user_id, title, attention_class,
    total_minutes, meaningful_minutes, occurred_on: date)` — loads or
    creates the profile row, applies `welford_update` to `total_*` (and to
    `meaningful_*` if `meaningful_minutes is not None`), updates the
    relevant `dow_total_mean` bucket (itself a small Welford-equivalent: a
    per-bucket mean means storing a per-bucket count too — reuse
    `welford_update` per-bucket rather than inventing a second formula),
    writes back.
  - `record_chore_completion(session, user_id, chore_id, total_minutes)` —
    same shape, keyed by `chore_id`; also recomputes `mc_weight` from the
    updated `total_mean` vs. the chore's own `estimated_minutes` (e.g.
    `mc_weight = clamp(estimated_minutes / total_mean, 0.25, 4.0)` — a chore
    that consistently runs 2x its estimate gets upweighted; exact formula is
    an implementation-time call, the *shape* — bounded, derived from real
    vs. estimated — is the spec).
  - Call sites: `event_service` on event completion (needs a definition of
    "completed" — likely `EventPatch.status == completed` or
    `actual_minutes` being set, whichever this spec's implementer confirms
    matches how the frontend actually marks things done today), and
    wherever chore occurrences get marked done (`schedule_service` /
    the chore-completion path spec 008/012 also touch — coordinate ordering
    if built alongside those).
- **API**: `GET /duration-profiles/{label_hash|chore_id}` for debugging/UI
  use; not required for the write path (writes are server-internal, fired
  from existing completion flows, not a new user-facing endpoint).
- **Consumers** (why this table exists):
  - Event/todo creation: if spec 006 exists, `event_memory.estimated_minutes`
    already gets refreshed from raw last-used values — swap that source to
    `duration_profiles.total_mean` once this table has samples, falling back
    to last-used when `total_sample_count == 0`.
  - `ChoreDefinition.mc_weight`: updated by `record_chore_completion` above,
    read unchanged by the existing MC scheduler (no scheduler code changes
    needed — it already reads this column, it's just been static).

## Non-goals

- No semantic/fuzzy matching between similar-but-not-identical labels — that
  is spec 011 (ChromaDB), explicitly layered on top of this table as a
  fallback when `total_sample_count` is low.
- No UI for viewing a duration profile directly in this spec (a "you usually
  spend 45 min on X, ±12" chip is a nice-to-have for a later spec).

## Acceptance criteria

- [ ] `welford_update` is unit-tested against a hand-computed mean/variance
      for a known sequence of values (e.g. `[10, 20, 30]` → mean 20,
      verified variance) — pure function, no DB/session needed for this test.
- [ ] Recording 3 completions of the same event title produces
      `total_sample_count == 3` and `total_mean` equal to their arithmetic
      mean (within floating rounding).
- [ ] Recording a chore completion updates `ChoreDefinition.mc_weight` away
      from its `1.0` default, and a subsequent MC scheduler run (existing,
      unmodified code) visibly weights that chore differently — proves the
      write side actually reaches the read side already in the codebase.
- [ ] `dow_total_mean`/`dow_sample_count` correctly bucket by day-of-week
      using the Sun=0 convention shared with `recurrence_weekdays`.
- [ ] No full-table re-scan anywhere in the update path — each completion
      does one row read + one row write, independent of history size.
