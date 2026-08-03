"""Missed-detection pass (spec 008) — the thin I/O shell around the pure
transition core in Pipelines/chore_healing.py.

Nothing in `schedule_service.py` ever moved a `ChoreOccurrence` out of
`scheduled`; this is the missing periodic pass that does. Wire
`run_missed_detection` the same way `purge_service.run_purge` is wired in
`main.py`'s lifespan (see that module for the loop/task-cancel shape) — this
module intentionally doesn't touch `main.py` itself.
"""
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.logging import get_logger
from app.Models.base import utc_now
from app.Pipelines.chore_healing import OccurrenceWindow, decide_transitions
from app.Repositories import event_repo, schedule_repo
from app.Schemas.base import EventStatus
from app.Services import chore_healing_service

_log = get_logger(__name__)
_EVENT_STATUS_COMPLETED = EventStatus.completed.value


async def _linked_event_status(
    session: AsyncSession, user_id: str, event_id: str | None
) -> str | None:
    """None when there's no linked event, or when it was (soft-)deleted —
    both read back as "not found" to the caller, which is exactly the
    "missed" case the pure core expects."""
    if event_id is None:
        return None
    event = await event_repo.get_event(session, user_id, event_id)
    return event.status if event is not None else None


async def run_missed_detection(session: AsyncSession) -> int:
    """Transition every `scheduled` occurrence whose window has passed into
    `completed` or `missed`, then run the drift-healing pass (spec 008 part
    2) once per (user, schedule_run) group touched by a transition. Returns
    the number of occurrences transitioned.
    """
    now = utc_now()
    occurrences = await schedule_repo.list_scheduled_past_window(session, now)
    if not occurrences:
        return 0

    by_id = {occurrence.id: occurrence for occurrence in occurrences}
    rows = []
    for occurrence in occurrences:
        event_status = await _linked_event_status(session, occurrence.user_id, occurrence.event_id)
        rows.append(
            (
                OccurrenceWindow(
                    id=occurrence.id,
                    status=occurrence.status,
                    event_id=occurrence.event_id,
                    proposed_end_at=occurrence.proposed_end_at,
                ),
                event_status,
                now,
            )
        )

    decisions = decide_transitions(rows)

    # Group by (user, schedule_run) so the healing pass below can write one
    # schedule_healing_log row per group (schedule_run_id is NOT NULL there).
    missed_counts: dict[tuple[str, str], int] = defaultdict(int)
    touched_chores: dict[tuple[str, str], set[str]] = defaultdict(set)

    for decision in decisions:
        occurrence = by_id[decision.occurrence_id]
        occurrence.status = decision.new_status
        key = (occurrence.user_id, occurrence.schedule_run_id)
        touched_chores[key].add(occurrence.chore_id)
        if decision.new_status == "missed":
            missed_counts[key] += 1

    await session.commit()

    for (user_id, run_id), chore_ids in touched_chores.items():
        await chore_healing_service.heal_pass(
            session,
            user_id=user_id,
            chore_ids=sorted(chore_ids),
            schedule_run_id=run_id,
            occurrences_missed=missed_counts.get((user_id, run_id), 0),
        )

    if decisions:
        _log.info(f"missed-detection pass transitioned {len(decisions)} occurrence(s)")
    return len(decisions)
