"""Event-type queries — live rows only (soft delete)."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.event_type import EventType


async def list_active(session: AsyncSession, user_id: str) -> list[EventType]:
    stmt = (
        select(EventType)
        .where(EventType.user_id == user_id, EventType.deleted_at.is_(None))
        .order_by(EventType.sort_order, EventType.created_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_event_type(
    session: AsyncSession, user_id: str, event_type_id: str
) -> EventType | None:
    stmt = select(EventType).where(
        EventType.id == event_type_id,
        EventType.user_id == user_id,
        EventType.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_key(session: AsyncSession, user_id: str, key: str) -> EventType | None:
    stmt = select(EventType).where(
        EventType.user_id == user_id,
        EventType.key == key,
        EventType.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def count_for_user(session: AsyncSession, user_id: str) -> int:
    stmt = select(func.count()).select_from(EventType).where(
        EventType.user_id == user_id, EventType.deleted_at.is_(None)
    )
    result = await session.execute(stmt)
    return int(result.scalar_one())


def add_event_type(session: AsyncSession, event_type: EventType) -> EventType:
    session.add(event_type)
    return event_type
