"""Routine service — CRUD, the run-execution state machine, and the
routine-to-schedule funnel (spec 013, same shape as issue #12's
`todo_service.schedule_todo`: builds an `EventCreate` and calls the
existing `event_service.create_event` rather than duplicating event
creation logic). Routine/step names are AES-GCM encrypted at rest via
`crypto.encrypt_field`/`decrypt_field`, same as event titles.
"""
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.Core import crypto
from app.Models.base import utc_now
from app.Models.routine import Routine, RoutineRun, RoutineStep, RoutineStepRun
from app.Pipelines.routine_steps import StepRef, renumber_after_delete, renumber_positions
from app.Repositories import routine_repo
from app.Schemas.base import AttentionClass
from app.Schemas.event import EventCreate
from app.Schemas.routine import (
    RoutineAdvanceRequest,
    RoutineCreate,
    RoutineOut,
    RoutinePatch,
    RoutineRunOut,
    RoutineRunStatus,
    RoutineScheduleRequest,
    RoutineScheduleResponse,
    RoutineStepCreate,
    RoutineStepOut,
    RoutineStepPatch,
    RoutineStepRunOut,
    RoutineStepRunStatus,
)
from app.Services import event_service


class RoutineError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


# ------------------------------------------------------------------ output


async def _routine_to_out(session: AsyncSession, routine: Routine, data_key: bytes) -> RoutineOut:
    steps = await routine_repo.list_steps(session, routine.user_id, routine.id)
    estimated = sum(step.estimated_minutes for step in steps) if steps else None
    return RoutineOut(
        id=routine.id,
        name=crypto.decrypt_field(data_key, routine.name_enc),
        description=(
            crypto.decrypt_field(data_key, routine.description_enc)
            if routine.description_enc
            else None
        ),
        color=routine.color,
        is_active=routine.is_active,
        step_count=len(steps),
        estimated_minutes=estimated,
        created_at=routine.created_at,
        updated_at=routine.updated_at,
    )


def _step_to_out(step: RoutineStep, data_key: bytes) -> RoutineStepOut:
    return RoutineStepOut(
        id=step.id,
        routine_id=step.routine_id,
        position=step.position,
        name=crypto.decrypt_field(data_key, step.name_enc),
        estimated_minutes=step.estimated_minutes,
        is_optional=step.is_optional,
        created_at=step.created_at,
        updated_at=step.updated_at,
    )


async def _step_run_to_out(
    session: AsyncSession, step_run: RoutineStepRun, data_key: bytes
) -> RoutineStepRunOut:
    step = await routine_repo.get_step_by_id(session, step_run.routine_step_id)
    step_name = crypto.decrypt_field(data_key, step.name_enc) if step else "(deleted step)"
    return RoutineStepRunOut(
        id=step_run.id,
        routine_step_id=step_run.routine_step_id,
        status=RoutineStepRunStatus(step_run.status),
        step_name=step_name,
        estimated_minutes=step.estimated_minutes if step else 0,
        is_optional=step.is_optional if step else False,
        started_at=step_run.started_at,
        ended_at=step_run.ended_at,
        actual_minutes=step_run.actual_minutes,
    )


async def _run_to_out(session: AsyncSession, run: RoutineRun, data_key: bytes) -> RoutineRunOut:
    step_runs = await routine_repo.list_step_runs(session, run.id)
    steps_out = [await _step_run_to_out(session, step_run, data_key) for step_run in step_runs]
    return RoutineRunOut(
        id=run.id,
        routine_id=run.routine_id,
        status=RoutineRunStatus(run.status),
        started_at=run.started_at,
        ended_at=run.ended_at,
        total_actual_minutes=run.total_actual_minutes,
        event_id=run.event_id,
        steps=steps_out,
    )


async def _require_routine(session: AsyncSession, user_id: str, routine_id: str) -> Routine:
    routine = await routine_repo.get_routine(session, user_id, routine_id)
    if routine is None:
        raise RoutineError(404, "routine not found")
    return routine


async def _require_step(
    session: AsyncSession, user_id: str, routine_id: str, step_id: str
) -> RoutineStep:
    step = await routine_repo.get_step(session, user_id, routine_id, step_id)
    if step is None:
        raise RoutineError(404, "routine step not found")
    return step


async def _require_run(session: AsyncSession, user_id: str, run_id: str) -> RoutineRun:
    run = await routine_repo.get_run(session, user_id, run_id)
    if run is None:
        raise RoutineError(404, "routine run not found")
    return run


# --------------------------------------------------------------- routines


async def create_routine(
    session: AsyncSession, user_id: str, data_key: bytes, payload: RoutineCreate
) -> RoutineOut:
    routine = Routine(
        user_id=user_id,
        name_enc=crypto.encrypt_field(data_key, payload.name),
        description_enc=(
            crypto.encrypt_field(data_key, payload.description) if payload.description else None
        ),
        color=payload.color.value,
        is_active=True,
    )
    routine_repo.add_routine(session, routine)
    await session.commit()
    return await _routine_to_out(session, routine, data_key)


async def list_routines(session: AsyncSession, user_id: str, data_key: bytes) -> list[RoutineOut]:
    routines = await routine_repo.list_routines(session, user_id)
    return [await _routine_to_out(session, routine, data_key) for routine in routines]


async def patch_routine(
    session: AsyncSession, user_id: str, data_key: bytes, routine_id: str, payload: RoutinePatch
) -> RoutineOut:
    routine = await _require_routine(session, user_id, routine_id)
    if payload.name is not None:
        routine.name_enc = crypto.encrypt_field(data_key, payload.name)
    if payload.description is not None:
        routine.description_enc = crypto.encrypt_field(data_key, payload.description)
    if payload.color is not None:
        routine.color = payload.color.value
    if payload.is_active is not None:
        routine.is_active = payload.is_active
    await session.commit()
    return await _routine_to_out(session, routine, data_key)


async def delete_routine(session: AsyncSession, user_id: str, routine_id: str) -> None:
    routine = await _require_routine(session, user_id, routine_id)
    routine.deleted_at = utc_now()
    await session.commit()


# ------------------------------------------------------------------ steps


async def add_step(
    session: AsyncSession,
    user_id: str,
    data_key: bytes,
    routine_id: str,
    payload: RoutineStepCreate,
) -> RoutineStepOut:
    await _require_routine(session, user_id, routine_id)
    current = await routine_repo.list_steps(session, user_id, routine_id)
    next_position = max((step.position for step in current), default=-1) + 1
    step = RoutineStep(
        routine_id=routine_id,
        user_id=user_id,
        position=next_position,
        name_enc=crypto.encrypt_field(data_key, payload.name),
        estimated_minutes=payload.estimated_minutes,
        is_optional=payload.is_optional,
    )
    routine_repo.add_step(session, step)
    await session.commit()
    return _step_to_out(step, data_key)


async def list_steps(
    session: AsyncSession, user_id: str, data_key: bytes, routine_id: str
) -> list[RoutineStepOut]:
    await _require_routine(session, user_id, routine_id)
    steps = await routine_repo.list_steps(session, user_id, routine_id)
    return [_step_to_out(step, data_key) for step in steps]


async def patch_step(
    session: AsyncSession,
    user_id: str,
    data_key: bytes,
    routine_id: str,
    step_id: str,
    payload: RoutineStepPatch,
) -> RoutineStepOut:
    step = await _require_step(session, user_id, routine_id, step_id)
    if payload.name is not None:
        step.name_enc = crypto.encrypt_field(data_key, payload.name)
    if payload.estimated_minutes is not None:
        step.estimated_minutes = payload.estimated_minutes
    if payload.is_optional is not None:
        step.is_optional = payload.is_optional
    await session.commit()
    return _step_to_out(step, data_key)


async def delete_step(
    session: AsyncSession, user_id: str, data_key: bytes, routine_id: str, step_id: str
) -> list[RoutineStepOut]:
    """Soft-delete the step, then renumber the remaining live steps to stay
    contiguous (pure function, no gaps — see Pipelines/routine_steps.py)."""
    step = await _require_step(session, user_id, routine_id, step_id)
    current = await routine_repo.list_steps(session, user_id, routine_id)
    step.deleted_at = utc_now()
    new_positions = renumber_after_delete([StepRef(id=s.id) for s in current], deleted_id=step_id)
    by_id = {s.id: s for s in current if s.id != step_id}
    for step_id_key, position in new_positions.items():
        by_id[step_id_key].position = position
    await session.commit()
    remaining = await routine_repo.list_steps(session, user_id, routine_id)
    return [_step_to_out(s, data_key) for s in remaining]


async def reorder_steps(
    session: AsyncSession,
    user_id: str,
    data_key: bytes,
    routine_id: str,
    ordered_step_ids: list[str],
) -> list[RoutineStepOut]:
    current = await routine_repo.list_steps(session, user_id, routine_id)
    try:
        new_positions = renumber_positions([StepRef(id=s.id) for s in current], ordered_step_ids)
    except ValueError as exc:
        raise RoutineError(400, str(exc)) from exc
    by_id = {s.id: s for s in current}
    for step_id, position in new_positions.items():
        by_id[step_id].position = position
    await session.commit()
    reordered = await routine_repo.list_steps(session, user_id, routine_id)
    return [_step_to_out(s, data_key) for s in reordered]


async def derived_estimated_minutes(
    session: AsyncSession, user_id: str, routine_id: str
) -> int | None:
    await _require_routine(session, user_id, routine_id)
    return await routine_repo.sum_estimated_minutes(session, routine_id)


# -------------------------------------------------------------------- runs


async def start_run(
    session: AsyncSession, user_id: str, data_key: bytes, routine_id: str
) -> RoutineRunOut:
    await _require_routine(session, user_id, routine_id)
    steps = await routine_repo.list_steps(session, user_id, routine_id)
    if not steps:
        raise RoutineError(409, "routine has no steps to run")

    run = RoutineRun(routine_id=routine_id, user_id=user_id, status="in_progress")
    await routine_repo.add_run(session, run)
    await session.flush()

    now = utc_now()
    for index, step in enumerate(steps):
        step_run = RoutineStepRun(
            routine_run_id=run.id,
            routine_step_id=step.id,
            user_id=user_id,
            status="active" if index == 0 else "pending",
            started_at=now if index == 0 else None,
        )
        routine_repo.add_step_run(session, step_run)
    await session.commit()
    return await _run_to_out(session, run, data_key)


def _elapsed_minutes(started_at, ended_at) -> int:  # type: ignore[no-untyped-def]
    seconds = (ended_at - started_at).total_seconds()
    return max(0, round(seconds / 60))


async def _sum_done_minutes(session: AsyncSession, run_id: str) -> int:
    step_runs = await routine_repo.list_step_runs(session, run_id)
    return sum(
        (step_run.actual_minutes or 0) for step_run in step_runs if step_run.status == "done"
    )


async def advance_step(
    session: AsyncSession,
    user_id: str,
    data_key: bytes,
    run_id: str,
    step_run_id: str,
    payload: RoutineAdvanceRequest,
) -> RoutineRunOut:
    run = await _require_run(session, user_id, run_id)
    if run.status != "in_progress":
        raise RoutineError(409, "run is not in progress")
    step_run = await routine_repo.get_step_run(session, user_id, run_id, step_run_id)
    if step_run is None:
        raise RoutineError(404, "step run not found")
    if step_run.status != "active":
        raise RoutineError(409, "step is not the active step")

    now = utc_now()
    if payload.skipped:
        step = await routine_repo.get_step_by_id(session, step_run.routine_step_id)
        if step is None or not step.is_optional:
            raise RoutineError(409, "only optional steps may be skipped")
        step_run.status = "skipped"
        step_run.actual_minutes = 0
    else:
        step_run.status = "done"
        step_run.actual_minutes = (
            payload.actual_minutes
            if payload.actual_minutes is not None
            else _elapsed_minutes(step_run.started_at or now, now)
        )
    step_run.ended_at = now

    step_runs = await routine_repo.list_step_runs(session, run_id)
    next_pending = next((sr for sr in step_runs if sr.status == "pending"), None)
    if next_pending is not None:
        next_pending.status = "active"
        next_pending.started_at = now
        await session.commit()
        return await _run_to_out(session, run, data_key)

    # No steps remain — auto-complete the run.
    run.status = "completed"
    run.ended_at = now
    run.total_actual_minutes = await _sum_done_minutes(session, run_id)
    await session.commit()
    return await _run_to_out(session, run, data_key)


async def finish_run(
    session: AsyncSession, user_id: str, data_key: bytes, run_id: str
) -> RoutineRunOut:
    run = await _require_run(session, user_id, run_id)
    if run.status != "in_progress":
        raise RoutineError(409, "run is not in progress")
    run.status = "completed"
    run.ended_at = utc_now()
    run.total_actual_minutes = await _sum_done_minutes(session, run_id)
    await session.commit()
    return await _run_to_out(session, run, data_key)


async def abandon_run(
    session: AsyncSession, user_id: str, data_key: bytes, run_id: str
) -> RoutineRunOut:
    """Abandon mid-sequence: completed steps' actuals are left untouched, and
    the routine definition itself is never touched — only this run row."""
    run = await _require_run(session, user_id, run_id)
    if run.status != "in_progress":
        raise RoutineError(409, "run is not in progress")
    run.status = "abandoned"
    run.ended_at = utc_now()
    run.total_actual_minutes = await _sum_done_minutes(session, run_id)
    await session.commit()
    return await _run_to_out(session, run, data_key)


async def list_runs(
    session: AsyncSession, user_id: str, data_key: bytes, routine_id: str, limit: int
) -> list[RoutineRunOut]:
    await _require_routine(session, user_id, routine_id)
    runs = await routine_repo.list_runs(session, user_id, routine_id, limit)
    return [await _run_to_out(session, run, data_key) for run in runs]


# --------------------------------------------------------------- schedule


async def schedule_routine(
    session: AsyncSession,
    user_id: str,
    data_key: bytes,
    routine_id: str,
    payload: RoutineScheduleRequest,
) -> RoutineScheduleResponse:
    routine = await _require_routine(session, user_id, routine_id)
    estimated = await routine_repo.sum_estimated_minutes(session, routine_id)
    if not estimated:
        raise RoutineError(409, "routine has no steps to estimate a duration from")

    title = crypto.decrypt_field(data_key, routine.name_enc)
    end_at = payload.start_at + timedelta(minutes=estimated)
    event_create = EventCreate(
        title=title,
        event_type=payload.event_type,
        attention_class=payload.attention_class or AttentionClass.active,
        start_at=payload.start_at,
        end_at=end_at,
        estimated_minutes=estimated,
    )
    created_event = await event_service.create_event(session, user_id, data_key, event_create)

    run = RoutineRun(
        routine_id=routine_id,
        user_id=user_id,
        status="pending",
        event_id=created_event.id,
    )
    await routine_repo.add_run(session, run)
    await session.commit()
    run_out = await _run_to_out(session, run, data_key)
    return RoutineScheduleResponse(run=run_out, event=created_event)
