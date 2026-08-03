"""Schedule run + occurrence queries."""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.schedule import ChoreOccurrence, ScheduleRun


async def list_runs(session: AsyncSession, user_id: str, limit: int) -> list[ScheduleRun]:
    stmt = (
        select(ScheduleRun)
        .where(ScheduleRun.user_id == user_id, ScheduleRun.deleted_at.is_(None))
        .order_by(ScheduleRun.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_run(session: AsyncSession, user_id: str, run_id: str) -> ScheduleRun | None:
    stmt = select(ScheduleRun).where(
        ScheduleRun.id == run_id,
        ScheduleRun.user_id == user_id,
        ScheduleRun.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_occurrences(session: AsyncSession, run_id: str) -> list[ChoreOccurrence]:
    stmt = (
        select(ChoreOccurrence)
        .where(ChoreOccurrence.schedule_run_id == run_id, ChoreOccurrence.deleted_at.is_(None))
        .order_by(ChoreOccurrence.proposed_start_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


def add_run(session: AsyncSession, run: ScheduleRun) -> ScheduleRun:
    session.add(run)
    return run


def add_occurrence(session: AsyncSession, occurrence: ChoreOccurrence) -> ChoreOccurrence:
    session.add(occurrence)
    return occurrence


async def list_scheduled_past_window(
    session: AsyncSession, now: datetime
) -> list[ChoreOccurrence]:
    """Occurrences (any user) still `scheduled`, linked to an event, whose
    window has passed — the missed-detection pass's candidate set (spec 008).
    """
    stmt = select(ChoreOccurrence).where(
        ChoreOccurrence.status == "scheduled",
        ChoreOccurrence.event_id.is_not(None),
        ChoreOccurrence.proposed_end_at < now,
        ChoreOccurrence.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def count_missed_and_completed(
    session: AsyncSession, user_id: str, chore_id: str, since: datetime
) -> tuple[int, int]:
    """(missed, completed) occurrence counts for one chore since `since` —
    the plain aggregate query behind `chore_healing_service.compute_drift`.
    """
    stmt = (
        select(ChoreOccurrence.status, func.count())
        .where(
            ChoreOccurrence.user_id == user_id,
            ChoreOccurrence.chore_id == chore_id,
            ChoreOccurrence.deleted_at.is_(None),
            ChoreOccurrence.proposed_end_at >= since,
            ChoreOccurrence.status.in_(("missed", "completed")),
        )
        .group_by(ChoreOccurrence.status)
    )
    result = await session.execute(stmt)
    counts = dict(result.all())
    return counts.get("missed", 0), counts.get("completed", 0)
