"""Chore definition queries."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.chore import ChoreDefinition


async def list_chores(
    session: AsyncSession, user_id: str, active_only: bool = False
) -> list[ChoreDefinition]:
    stmt = (
        select(ChoreDefinition)
        .where(ChoreDefinition.user_id == user_id, ChoreDefinition.deleted_at.is_(None))
        .order_by(ChoreDefinition.created_at)
    )
    if active_only:
        stmt = stmt.where(ChoreDefinition.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_chore(
    session: AsyncSession, user_id: str, chore_id: str
) -> ChoreDefinition | None:
    stmt = select(ChoreDefinition).where(
        ChoreDefinition.id == chore_id,
        ChoreDefinition.user_id == user_id,
        ChoreDefinition.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def add_chore(session: AsyncSession, chore: ChoreDefinition) -> ChoreDefinition:
    session.add(chore)
    return chore
