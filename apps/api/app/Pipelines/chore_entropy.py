"""Chore decay-rate recommendation (spec 012) — pure functions, zero I/O.

Reuses `welford_update` from spec 007's `duration_stats` verbatim rather than
reimplementing the running mean/variance update.
"""
from datetime import datetime


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


def days_until_due(next_due_at: datetime | None, now: datetime) -> int | None:
    """Days from `now` until `next_due_at`; negative when overdue.

    `None` when the chore has no `next_due_at` yet (e.g. never scheduled).
    """
    if next_due_at is None:
        return None
    return (next_due_at - now).days
