"""Event queries — range and overlap lookups on the live-row index."""
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.event import Event


async def list_in_range(
    session: AsyncSession, user_id: str, start_at: datetime, end_at: datetime
) -> list[Event]:
    stmt = (
        select(Event)
        .where(
            Event.user_id == user_id,
            Event.deleted_at.is_(None),
            Event.start_at < end_at,
            Event.end_at > start_at,
        )
        .order_by(Event.start_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def list_for_window(
    session: AsyncSession, user_id: str, window_start: datetime, window_end: datetime
) -> list[Event]:
    """Rows relevant to a calendar-display window: non-recurring events that
    overlap it (same rule as `list_in_range`), UNION recurring masters whose
    series may still be running during it (anchored before the window ends,
    and not finished before the window starts). The master's row is a single
    stub — expanding it into per-day occurrences is a calendar-display concern
    handled by the service layer, not this query.

    NOTE: `list_busy_in_range` / `list_in_range` (used by scheduling and AI
    busy-window checks) intentionally keep the old overlap-only rule and are
    NOT recurrence-aware yet — a recurring master only blocks its own anchor
    slot for those callers. Widening that is out of scope for this issue.
    """
    stmt = (
        select(Event)
        .where(
            Event.user_id == user_id,
            Event.deleted_at.is_(None),
            or_(
                and_(
                    Event.is_recurring.is_(False),
                    Event.start_at < window_end,
                    Event.end_at > window_start,
                ),
                and_(
                    Event.is_recurring.is_(True),
                    Event.start_at < window_end,
                    or_(
                        Event.recurrence_end.is_(None),
                        Event.recurrence_end >= window_start,
                    ),
                ),
            ),
        )
        .order_by(Event.start_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


_NON_BLOCKING_STATUSES = ("cancelled", "skipped")


async def list_busy_in_range(
    session: AsyncSession, user_id: str, start_at: datetime, end_at: datetime
) -> list[Event]:
    """Events that actually occupy time — cancelled/skipped ones don't block slots."""
    events = await list_in_range(session, user_id, start_at, end_at)
    return [event for event in events if event.status not in _NON_BLOCKING_STATUSES]


async def list_overlapping(
    session: AsyncSession,
    user_id: str,
    start_at: datetime,
    end_at: datetime,
    exclude_id: str | None,
) -> list[Event]:
    overlapping = await list_in_range(session, user_id, start_at, end_at)
    return [event for event in overlapping if event.id != exclude_id]


async def get_event(session: AsyncSession, user_id: str, event_id: str) -> Event | None:
    stmt = select(Event).where(
        Event.id == event_id,
        Event.user_id == user_id,
        Event.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def add_event(session: AsyncSession, event: Event) -> Event:
    session.add(event)
    return event
