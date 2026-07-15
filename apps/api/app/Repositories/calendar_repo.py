"""Calendar queries — live rows only (soft delete)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.calendar import Calendar


async def list_calendars(session: AsyncSession, user_id: str) -> list[Calendar]:
    stmt = (
        select(Calendar)
        .where(Calendar.user_id == user_id, Calendar.deleted_at.is_(None))
        .order_by(Calendar.created_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_default_calendar(session: AsyncSession, user_id: str) -> Calendar | None:
    stmt = select(Calendar).where(
        Calendar.user_id == user_id,
        Calendar.color.is_(None),
        Calendar.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_calendar(session: AsyncSession, user_id: str, calendar_id: str) -> Calendar | None:
    stmt = select(Calendar).where(
        Calendar.id == calendar_id,
        Calendar.user_id == user_id,
        Calendar.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def add_calendar(session: AsyncSession, calendar: Calendar) -> Calendar:
    session.add(calendar)
    return calendar
