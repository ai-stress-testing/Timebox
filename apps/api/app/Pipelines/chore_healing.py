"""Missed-occurrence transitions + drift-triggered healing math (spec 008) —
pure functions, zero I/O (same pure-core/I-O-shell split as the MC scheduler
in Pipelines/monte_carlo.py).

Part 1 (`decide_transitions`): given a snapshot of scheduled occurrences and
their linked events' current status, decide which occurrences flip to
"completed" or "missed". The DB read (which occurrences are due, what status
their linked event is in) and the write-back live in
Services/chore_missed_detection_service.py.

Part 2 (`compute_drift_ratio`, `nudge_n_toward_original`): the arithmetic
behind drift-triggered healing; the occurrence-counting query and the
ChoreDefinition/history writes live in Services/chore_healing_service.py.
"""
from dataclasses import dataclass
from datetime import datetime

DRIFT_THRESHOLD = 0.4

_EVENT_STATUS_COMPLETED = "completed"
_OCCURRENCE_STATUS_SCHEDULED = "scheduled"


@dataclass(frozen=True)
class OccurrenceWindow:
    """Just enough of a `ChoreOccurrence` for the transition decision —
    decoupled from the ORM model so this module stays DB-free."""

    id: str
    status: str
    event_id: str | None
    proposed_end_at: datetime


@dataclass(frozen=True)
class OccurrenceTransition:
    occurrence_id: str
    new_status: str  # "completed" | "missed"


def decide_transitions(
    rows: list[tuple[OccurrenceWindow, str | None, datetime]],
) -> list[OccurrenceTransition]:
    """`rows` is a list of (occurrence, linked_event_status, now).

    `linked_event_status` is `None` when the occurrence has no `event_id`
    yet, or when the linked event was deleted (a soft-deleted event reads
    back as "not found" by the caller).

    Rule: an occurrence whose window (`proposed_end_at`) hasn't passed `now`
    yet, or that has no `event_id` at all, is left alone. Otherwise: linked
    event status "completed" -> occurrence "completed"; anything else
    (deleted, or never reached "completed") -> occurrence "missed".
    """
    decisions: list[OccurrenceTransition] = []
    for occurrence, event_status, now in rows:
        if occurrence.status != _OCCURRENCE_STATUS_SCHEDULED:
            continue
        if occurrence.event_id is None:
            continue
        if occurrence.proposed_end_at > now:
            continue
        new_status = "completed" if event_status == _EVENT_STATUS_COMPLETED else "missed"
        decisions.append(OccurrenceTransition(occurrence.id, new_status))
    return decisions


def compute_drift_ratio(missed: int, completed: int) -> float:
    """missed / (missed + completed); 0.0 when there's nothing to divide by
    (an all-completed history is also 0.0; an all-missed history is 1.0)."""
    total = missed + completed
    if total == 0:
        return 0.0
    return missed / total


def nudge_n_toward_original(n_current: int, n_original: int, n_min: int, n_max: int) -> int:
    """Relax `n_current` halfway back toward `n_original` (at least one day
    of movement), clamped to `[n_min, n_max]`.

    A chronically-missed chore is overcommitted (scheduled too often for
    what actually gets done), so healing always moves toward the original
    cadence — never past it, never further away from it.
    """
    if n_current == n_original:
        return min(max(n_current, n_min), n_max)
    distance = abs(n_original - n_current)
    step = max(1, distance // 2)
    if n_current < n_original:
        new_n = min(n_current + step, n_original)
    else:
        new_n = max(n_current - step, n_original)
    return min(max(new_n, n_min), n_max)
