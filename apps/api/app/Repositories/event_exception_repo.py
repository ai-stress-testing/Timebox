"""Event exception queries — per-occurrence cancellations, live rows only."""
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.event_exception import EventException


def add_exception(
    session: AsyncSession, master_event_id: str, user_id: str, occurrence_date: str
) -> EventException:
    exception = EventException(
        master_event_id=master_event_id,
        user_id=user_id,
        occurrence_date=occurrence_date,
    )
    session.add(exception)
    return exception


async def list_cancelled_dates(
    session: AsyncSession, user_id: str, master_ids: list[str]
) -> dict[str, set[str]]:
    """Master id -> set of cancelled "YYYY-MM-DD" dates, live rows only.
    Bounded by `master_ids` (the masters already loaded for the query window).
    """
    if not master_ids:
        return {}
    stmt = select(EventException.master_event_id, EventException.occurrence_date).where(
        EventException.user_id == user_id,
        EventException.master_event_id.in_(master_ids),
        EventException.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    cancelled: dict[str, set[str]] = defaultdict(set)
    for master_id, occurrence_date in result.all():
        cancelled[master_id].add(occurrence_date)
    return dict(cancelled)
