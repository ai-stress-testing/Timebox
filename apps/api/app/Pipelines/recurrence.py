"""Weekly-by-weekday recurrence expansion — pure function (NASA rule 2/3).

No I/O, no DB, no clock reads. Given an anchor event's start/end and a weekly
weekday rule, expands the *virtual* occurrences that fall inside
[window_start, window_end). Occurrences are never persisted — the service
layer calls this on every read and discards the result after building
response DTOs. Deterministic: same inputs always produce the same tuple.

Weekday convention: Sun=0 .. Sat=6, matching the chores dispatch
(`Pipelines/monte_carlo.py::_weekday_sun0`) — Python's `date.weekday()` is
Mon=0, so it is rotated by one before comparison.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta

MAX_OCCURRENCES = 400


@dataclass(frozen=True)
class Occurrence:
    start_at: datetime
    end_at: datetime
    occurrence_date: date


def _weekday_sun0(day: date) -> int:
    return (day.weekday() + 1) % 7


def expand_occurrences(
    anchor_start: datetime,
    anchor_end: datetime,
    weekdays: frozenset[int],
    series_end: datetime | None,
    window_start: datetime,
    window_end: datetime,
) -> tuple[Occurrence, ...]:
    """One occurrence per day in the window whose weekday is in `weekdays`,
    on/after the anchor's date and on/before `series_end` (if set), carrying
    the anchor's time-of-day and duration. Hard-capped at MAX_OCCURRENCES
    iterations regardless of how wide a window the caller passes.
    """
    duration = anchor_end - anchor_start
    time_of_day = anchor_start.time()
    current = max(anchor_start.date(), window_start.date())
    last_date = window_end.date()
    occurrences: list[Occurrence] = []
    for _ in range(MAX_OCCURRENCES):
        if current > last_date:
            break
        if _weekday_sun0(current) in weekdays:
            occ_start = datetime.combine(current, time_of_day)
            occ_end = occ_start + duration
            in_window = occ_start < window_end and occ_end > window_start
            in_series = series_end is None or occ_start <= series_end
            if in_window and in_series:
                occurrences.append(Occurrence(occ_start, occ_end, current))
        current += timedelta(days=1)
    return tuple(occurrences)
