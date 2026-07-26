"""Pure unit tests for `live_elapsed`/`is_timer_complete` — no DB, no
`unlocked` fixture, no clock reads: hand-built inputs only."""
from datetime import datetime, timedelta

from app.Pipelines.canvas_timer import is_timer_complete, live_elapsed

_NOW = datetime(2026, 7, 26, 12, 0, 0)


def test_live_elapsed_paused_returns_accumulated() -> None:
    assert live_elapsed(120, None, "paused", _NOW) == 120


def test_live_elapsed_running_adds_delta() -> None:
    started = _NOW - timedelta(seconds=45)
    assert live_elapsed(30, started, "running", _NOW) == 75


def test_live_elapsed_just_reset_is_zero() -> None:
    assert live_elapsed(0, None, "paused", _NOW) == 0


def test_live_elapsed_running_with_no_started_at_is_defensive_noop() -> None:
    # Should never happen (running always carries a started_at), but the
    # pure function must not explode if it does.
    assert live_elapsed(10, None, "running", _NOW) == 10


def test_live_elapsed_completed_ignores_started_at() -> None:
    started = _NOW - timedelta(minutes=10)
    assert live_elapsed(600, started, "completed", _NOW) == 600


def test_is_timer_complete_true_at_target() -> None:
    assert is_timer_complete("timer", 300, 300) is True


def test_is_timer_complete_true_past_target() -> None:
    assert is_timer_complete("timer", 300, 301) is True


def test_is_timer_complete_false_below_target() -> None:
    assert is_timer_complete("timer", 300, 299) is False


def test_is_timer_complete_stopwatch_never_completes() -> None:
    assert is_timer_complete("stopwatch", None, 10_000) is False


def test_is_timer_complete_timer_without_duration_never_completes() -> None:
    assert is_timer_complete("timer", None, 10_000) is False
