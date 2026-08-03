"""Attention-class queries — global, read-only rows (no user_id filter)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.attention_class import AttentionClass


async def list_all(session: AsyncSession) -> list[AttentionClass]:
    stmt = select(AttentionClass).order_by(AttentionClass.value)
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_by_value(session: AsyncSession, value: str) -> AttentionClass | None:
    stmt = select(AttentionClass).where(AttentionClass.value == value)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def add_entity(session: AsyncSession, entity: AttentionClass) -> AttentionClass:
    session.add(entity)
    return entity
