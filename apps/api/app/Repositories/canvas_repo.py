"""Canvas item, position-history, and alarm queries — live rows only
(soft delete)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.canvas import CanvasAlarm, CanvasItem, CanvasPositionHistory


async def list_for_user(session: AsyncSession, user_id: str) -> list[CanvasItem]:
    stmt = (
        select(CanvasItem)
        .where(CanvasItem.user_id == user_id, CanvasItem.deleted_at.is_(None))
        .order_by(CanvasItem.created_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_item(session: AsyncSession, user_id: str, item_id: str) -> CanvasItem | None:
    stmt = select(CanvasItem).where(
        CanvasItem.id == item_id,
        CanvasItem.user_id == user_id,
        CanvasItem.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def add_item(session: AsyncSession, item: CanvasItem) -> CanvasItem:
    session.add(item)
    return item


def add_position_history(
    session: AsyncSession, entry: CanvasPositionHistory
) -> CanvasPositionHistory:
    session.add(entry)
    return entry


async def get_alarm(session: AsyncSession, user_id: str, alarm_id: str) -> CanvasAlarm | None:
    stmt = select(CanvasAlarm).where(
        CanvasAlarm.id == alarm_id,
        CanvasAlarm.user_id == user_id,
        CanvasAlarm.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def add_alarm(session: AsyncSession, alarm: CanvasAlarm) -> CanvasAlarm:
    session.add(alarm)
    return alarm
