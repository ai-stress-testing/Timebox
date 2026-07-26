"""Welford update — pure function, hand-verified against a known sequence."""
from app.Pipelines.duration_stats import WelfordState, variance, welford_update


def test_welford_matches_hand_computed_mean_and_variance() -> None:
    state = WelfordState(count=0, mean=0.0, m2=0.0)
    for value in (10.0, 20.0, 30.0):
        state = welford_update(state, value)
    assert state.count == 3
    assert state.mean == 20.0
    assert variance(state) == 100.0  # sample variance of [10, 20, 30]


def test_welford_single_observation_has_zero_variance() -> None:
    state = welford_update(WelfordState(count=0, mean=0.0, m2=0.0), 42.0)
    assert state.count == 1
    assert state.mean == 42.0
    assert variance(state) == 0.0


def test_welford_is_order_independent_for_mean() -> None:
    forward = WelfordState(count=0, mean=0.0, m2=0.0)
    for value in (5.0, 15.0, 25.0, 35.0):
        forward = welford_update(forward, value)
    backward = WelfordState(count=0, mean=0.0, m2=0.0)
    for value in (35.0, 25.0, 15.0, 5.0):
        backward = welford_update(backward, value)
    assert forward.mean == backward.mean
    assert abs(forward.m2 - backward.m2) < 1e-9
