"""Event queries — range and overlap lookups on the live-row index."""
from datetime import datetime

from sqlalchemy import select
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
