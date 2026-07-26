"""Welford's online mean/variance algorithm — pure function (NASA rule 2/3).

No I/O, no DB. A numerically stable running mean/M2 update, O(1) per call,
independent of history size. Shared by every "learn a typical value from a
stream of observations" pipeline in this codebase (duration_profiles' typical
session length, chore_entropy's typical days-between-completions, ...) —
those specs import `welford_update` from here rather than each writing their
own copy of the same three lines of algebra.
"""
from dataclasses import dataclass


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


def variance(state: WelfordState) -> float:
    """Sample variance; 0.0 for fewer than 2 observations (undefined otherwise)."""
    return state.m2 / (state.count - 1) if state.count > 1 else 0.0
