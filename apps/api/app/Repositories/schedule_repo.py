"""Schedule run + occurrence queries."""
from sqlalchemy import select
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
