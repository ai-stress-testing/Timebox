"""Pomodoro session, residual prompt, and task residual queries."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.pomodoro import PomodoroSession, ResidualPrompt, TaskResidual


async def get_open_session(session: AsyncSession, user_id: str) -> PomodoroSession | None:
    stmt = select(PomodoroSession).where(
        PomodoroSession.user_id == user_id,
        PomodoroSession.status == "active",
        PomodoroSession.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_session_by_id(
    session: AsyncSession, user_id: str, session_id: str
) -> PomodoroSession | None:
    stmt = select(PomodoroSession).where(
        PomodoroSession.id == session_id,
        PomodoroSession.user_id == user_id,
        PomodoroSession.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_sessions(
    session: AsyncSession, user_id: str, limit: int
) -> list[PomodoroSession]:
    stmt = (
        select(PomodoroSession)
        .where(PomodoroSession.user_id == user_id, PomodoroSession.deleted_at.is_(None))
        .order_by(PomodoroSession.started_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def list_prompts(
    session: AsyncSession, user_id: str, status: str | None
) -> list[ResidualPrompt]:
    stmt = (
        select(ResidualPrompt)
        .where(ResidualPrompt.user_id == user_id, ResidualPrompt.deleted_at.is_(None))
        .order_by(ResidualPrompt.prompted_at.desc())
    )
    if status is not None:
        stmt = stmt.where(ResidualPrompt.status == status)
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_prompt(
    session: AsyncSession, user_id: str, prompt_id: str
) -> ResidualPrompt | None:
    stmt = select(ResidualPrompt).where(
        ResidualPrompt.id == prompt_id,
        ResidualPrompt.user_id == user_id,
        ResidualPrompt.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def add_entity(
    session: AsyncSession, entity: PomodoroSession | ResidualPrompt | TaskResidual
) -> None:
    session.add(entity)
