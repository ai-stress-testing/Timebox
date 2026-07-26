"""Routine/step/run queries — live rows only (soft delete), steps ordered by
`position`, step-runs ordered by creation order (== step position order,
since `start_run` creates one step-run per step in position order)."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.routine import Routine, RoutineRun, RoutineStep, RoutineStepRun

# --------------------------------------------------------------- routines


async def list_routines(session: AsyncSession, user_id: str) -> list[Routine]:
    stmt = (
        select(Routine)
        .where(Routine.user_id == user_id, Routine.deleted_at.is_(None))
        .order_by(Routine.created_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_routine(session: AsyncSession, user_id: str, routine_id: str) -> Routine | None:
    stmt = select(Routine).where(
        Routine.id == routine_id,
        Routine.user_id == user_id,
        Routine.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def add_routine(session: AsyncSession, routine: Routine) -> Routine:
    session.add(routine)
    return routine


# ----------------------------------------------------------- routine steps


async def list_steps(session: AsyncSession, user_id: str, routine_id: str) -> list[RoutineStep]:
    stmt = (
        select(RoutineStep)
        .where(
            RoutineStep.routine_id == routine_id,
            RoutineStep.user_id == user_id,
            RoutineStep.deleted_at.is_(None),
        )
        .order_by(RoutineStep.position)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_step(
    session: AsyncSession, user_id: str, routine_id: str, step_id: str
) -> RoutineStep | None:
    stmt = select(RoutineStep).where(
        RoutineStep.id == step_id,
        RoutineStep.routine_id == routine_id,
        RoutineStep.user_id == user_id,
        RoutineStep.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def add_step(session: AsyncSession, step: RoutineStep) -> RoutineStep:
    session.add(step)
    return step


async def get_step_by_id(session: AsyncSession, step_id: str) -> RoutineStep | None:
    """Unscoped-by-routine lookup (including soft-deleted rows) — used when
    rendering a run's step names, since a step may have been edited/deleted
    after the run that references it started."""
    stmt = select(RoutineStep).where(RoutineStep.id == step_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def sum_estimated_minutes(session: AsyncSession, routine_id: str) -> int | None:
    """`SELECT SUM(estimated_minutes) FROM routine_steps WHERE routine_id = ...
    AND deleted_at IS NULL` — the derived-on-read total the service layer
    uses instead of a stored, driftable column."""
    stmt = select(func.sum(RoutineStep.estimated_minutes)).where(
        RoutineStep.routine_id == routine_id,
        RoutineStep.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# --------------------------------------------------------------------- runs


async def add_run(session: AsyncSession, run: RoutineRun) -> RoutineRun:
    session.add(run)
    return run


async def get_run(session: AsyncSession, user_id: str, run_id: str) -> RoutineRun | None:
    stmt = select(RoutineRun).where(RoutineRun.id == run_id, RoutineRun.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_runs(
    session: AsyncSession, user_id: str, routine_id: str, limit: int
) -> list[RoutineRun]:
    stmt = (
        select(RoutineRun)
        .where(RoutineRun.user_id == user_id, RoutineRun.routine_id == routine_id)
        .order_by(RoutineRun.started_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


def add_step_run(session: AsyncSession, step_run: RoutineStepRun) -> RoutineStepRun:
    session.add(step_run)
    return step_run


async def list_step_runs(session: AsyncSession, run_id: str) -> list[RoutineStepRun]:
    stmt = (
        select(RoutineStepRun)
        .where(RoutineStepRun.routine_run_id == run_id)
        .order_by(RoutineStepRun.created_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_step_run(
    session: AsyncSession, user_id: str, run_id: str, step_run_id: str
) -> RoutineStepRun | None:
    stmt = select(RoutineStepRun).where(
        RoutineStepRun.id == step_run_id,
        RoutineStepRun.routine_run_id == run_id,
        RoutineStepRun.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
