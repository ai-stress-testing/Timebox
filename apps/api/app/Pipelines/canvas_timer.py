"""Canvas timer arithmetic — pure functions (NASA rule 2/3), no I/O, no DB,
no clock reads. `live_elapsed` takes the persisted elapsed-tracking fields
plus an externally supplied `now` and returns the elapsed seconds at that
instant; `is_timer_complete` takes the result and decides whether a
countdown has finished. The service layer is the only caller that ever
passes a real `datetime.now()` in — deterministic and unit-testable without
touching a clock in real time.
"""
from datetime import datetime


def live_elapsed(
    accumulated_seconds: int,
    started_at: datetime | None,
    status: str,
    now: datetime,
) -> int:
    """Elapsed seconds for a canvas timer/stopwatch at instant `now`.

    Running: accumulated_seconds + (now - started_at), the growing figure a
    live client tick would show. Paused/completed (or a running row missing
    its `started_at`, which should never happen but is handled defensively):
    just the frozen accumulated_seconds.
    """
    if status == "running" and started_at is not None:
        delta_seconds = (now - started_at).total_seconds()
        return accumulated_seconds + max(0, int(delta_seconds))
    return accumulated_seconds


def is_timer_complete(mode: str, duration_seconds: int | None, elapsed_seconds: int) -> bool:
    """True once a timer's (never a stopwatch's) live elapsed has reached or
    passed its countdown target. Checked lazily by the caller on read/tick —
    no background poller.
    """
    if mode != "timer" or duration_seconds is None:
        return False
    return elapsed_seconds >= duration_seconds
