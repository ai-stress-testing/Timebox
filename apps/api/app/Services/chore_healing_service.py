"""Drift detection + healing (spec 008) — the DB-facing half of
Pipelines/chore_healing.py. A chore "drifts" when its occurrences are
routinely missed rather than completed; healing relaxes its cadence back
toward `n_original` (never tightens it further) and logs both the per-chore
adjustment (`chore_n_history`) and one pass-level rollup row
(`schedule_healing_log`).

Distinct from spec 012 (Chore Entropy): this answers "am I keeping up with
the plan as scheduled" (missed vs. completed), entropy answers "is the
scheduled cadence right for how fast the chore actually needs doing". Both
write to `chore_n_history` with different `reason` values.
"""
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.base import utc_now
from app.Models.chore_healing import ChoreNHistory, ScheduleHealingLog
from app.Pipelines.chore_healing import (
    DRIFT_THRESHOLD,
    compute_drift_ratio,
    nudge_n_toward_original,
)
from app.Repositories import chore_healing_repo, chore_repo, schedule_repo

_LOOKBACK_DAYS = 28
_HEALING_REASON = "healing"
_TRIGGER_MISSED_THRESHOLD = "missed_threshold"


@dataclass(frozen=True)
class HealResult:
    chore_id: str
    n_before: int
    n_after: int
    drift_rate: float
    missed_count: int


async def _drift_and_counts(
    session: AsyncSession, user_id: str, chore_id: str, lookback_days: int
) -> tuple[float, int, int]:
    since = utc_now() - timedelta(days=lookback_days)
    missed, completed = await schedule_repo.count_missed_and_completed(
        session, user_id, chore_id, since
    )
    return compute_drift_ratio(missed, completed), missed, completed


async def compute_drift(
    session: AsyncSession, user_id: str, chore_id: str, lookback_days: int = _LOOKBACK_DAYS
) -> float:
    """missed / (missed + completed) over the last `lookback_days` for one
    chore. 0.0 for an all-completed history (or no history at all), 1.0 for
    an all-missed one."""
    drift, _missed, _completed = await _drift_and_counts(session, user_id, chore_id, lookback_days)
    return drift


async def heal_if_needed(
    session: AsyncSession,
    user_id: str,
    chore_id: str,
    schedule_run_id: str,
    lookback_days: int = _LOOKBACK_DAYS,
) -> HealResult | None:
    """If this chore's drift crosses `DRIFT_THRESHOLD`, nudge `n_current`
    toward `n_original` (bounded by `[n_min, n_max]`) and log one
    `chore_n_history` row with `reason="healing"`. Returns None (writes
    nothing) when the chore is on track or already sitting at its bound."""
    drift, missed, _completed = await _drift_and_counts(session, user_id, chore_id, lookback_days)
    if drift <= DRIFT_THRESHOLD:
        return None
    chore = await chore_repo.get_chore(session, user_id, chore_id)
    if chore is None:
        return None
    n_before = chore.n_current
    n_after = nudge_n_toward_original(n_before, chore.n_original, chore.n_min, chore.n_max)
    if n_after == n_before:
        return None
    chore.n_current = n_after
    chore_healing_repo.add_n_history(
        session,
        ChoreNHistory(
            chore_id=chore.id,
            user_id=user_id,
            n_before=n_before,
            n_after=n_after,
            reason=_HEALING_REASON,
            schedule_run_id=schedule_run_id,
        ),
    )
    return HealResult(
        chore_id=chore.id,
        n_before=n_before,
        n_after=n_after,
        drift_rate=drift,
        missed_count=missed,
    )


async def heal_pass(
    session: AsyncSession,
    user_id: str,
    chore_ids: list[str],
    schedule_run_id: str,
    occurrences_missed: int,
    lookback_days: int = _LOOKBACK_DAYS,
) -> ScheduleHealingLog | None:
    """Run `heal_if_needed` for every chore the triggering missed-detection
    pass touched, and roll the outcome into ONE `schedule_healing_log` row
    for the whole pass (not one per chore) — matching the table's
    `occurrences_healed`/`n_adjustments` being pass-level counters. Writes
    nothing (returns None) if no chore in `chore_ids` crossed the threshold,
    so chores on track never produce spurious rows.
    """
    results = [
        result
        for chore_id in chore_ids
        if (
            result := await heal_if_needed(
                session, user_id, chore_id, schedule_run_id, lookback_days
            )
        )
        is not None
    ]
    if not results:
        return None

    log = ScheduleHealingLog(
        user_id=user_id,
        schedule_run_id=schedule_run_id,
        trigger=_TRIGGER_MISSED_THRESHOLD,
        occurrences_missed=occurrences_missed,
        occurrences_healed=sum(result.missed_count for result in results),
        n_adjustments=len(results),
        drift_rate=sum(result.drift_rate for result in results) / len(results),
    )
    chore_healing_repo.add_healing_log(session, log)
    await session.commit()
    return log
