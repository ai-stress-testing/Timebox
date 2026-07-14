"""Schedule service — snapshot DB → pure MC pipeline → persist run + occurrences.

Production swap: this whole call becomes a Celery task; the pipeline is
already pure so nothing else changes (constitution Article II).
"""
import json
import secrets
from datetime import datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.Core import crypto
from app.Models.base import utc_now
from app.Models.chore import ChoreDefinition
from app.Models.schedule import ChoreOccurrence, ScheduleRun
from app.Pipelines.monte_carlo import (
    BusyInterval,
    ChoreSpec,
    ScheduleInput,
    ScheduleResult,
    run_monte_carlo,
)
from app.Repositories import chore_repo, event_repo, schedule_repo
from app.Schemas.event import EventCreate
from app.Schemas.base import EventType, AttentionClass
from app.Schemas.schedule import (
    ApplyResponse,
    OccurrenceOut,
    OccurrenceStatus,
    RunDetailOut,
    RunOut,
    RunRequest,
    RunStatus,
)
from app.Services import event_service


class ScheduleError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _hhmm_to_minutes(value: str | None) -> int | None:
    if value is None:
        return None
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _first_due_offset(chore: ChoreDefinition, window_start: datetime) -> int:
    if chore.last_completed_at is None:
        return 0
    elapsed_days = (window_start - chore.last_completed_at).days
    return max(0, chore.n_current - elapsed_days)


def _to_spec(chore: ChoreDefinition, window_start: datetime) -> ChoreSpec:
    return ChoreSpec(
        chore_id=chore.id,
        estimated_minutes=chore.estimated_minutes,
        priority=chore.priority,
        n_current=chore.n_current,
        first_due_offset=_first_due_offset(chore, window_start),
        preferred_days=frozenset(json.loads(chore.preferred_days)),
        avoid_days=frozenset(json.loads(chore.avoid_days)),
        preferred_start_minute=_hhmm_to_minutes(chore.preferred_time_start),
        preferred_end_minute=_hhmm_to_minutes(chore.preferred_time_end),
        weight=float(chore.mc_weight),
    )


async def _snapshot(
    session: AsyncSession, user_id: str, window_start: datetime, window_days: int
) -> tuple[tuple[ChoreSpec, ...], tuple[BusyInterval, ...]]:
    chores = await chore_repo.list_chores(session, user_id, active_only=True)
    window_end = window_start + timedelta(days=window_days)
    events = await event_repo.list_busy_in_range(session, user_id, window_start, window_end)
    specs = tuple(_to_spec(chore, window_start) for chore in chores)
    busy = tuple(BusyInterval(event.start_at, event.end_at) for event in events)
    return specs, busy


def _run_to_out(run: ScheduleRun) -> RunOut:
    return RunOut(
        id=run.id,
        run_type=run.run_type,
        status=RunStatus(run.status),
        window_start=run.window_start,
        window_end=run.window_end,
        window_days=run.window_days,
        iterations=run.iterations,
        seed=run.seed,
        score=float(run.score) if run.score is not None else None,
        chores_scheduled=run.chores_scheduled,
        mean_daily_load=float(run.mean_daily_load) if run.mean_daily_load is not None else None,
        load_variance=float(run.load_variance) if run.load_variance is not None else None,
        overloaded_days=run.overloaded_days,
        underloaded_days=run.underloaded_days,
        created_at=run.created_at,
        completed_at=run.completed_at,
    )


def _occurrence_to_out(occ: ChoreOccurrence, chore_names: dict[str, str]) -> OccurrenceOut:
    return OccurrenceOut(
        id=occ.id,
        chore_id=occ.chore_id,
        chore_name=chore_names.get(occ.chore_id, "(unknown chore)"),
        proposed_start_at=occ.proposed_start_at,
        proposed_end_at=occ.proposed_end_at,
        confidence_score=float(occ.confidence_score),
        load_score=float(occ.load_score),
        status=OccurrenceStatus(occ.status),
        event_id=occ.event_id,
    )


async def _chore_names(session: AsyncSession, user_id: str, data_key: bytes) -> dict[str, str]:
    chores = await chore_repo.list_chores(session, user_id)
    return {chore.id: crypto.decrypt_field(data_key, chore.name_enc) for chore in chores}


def _persist_result(
    session: AsyncSession, run: ScheduleRun, result: ScheduleResult
) -> None:
    run.status = RunStatus.completed.value
    run.completed_at = utc_now()
    run.score = result.metrics.score
    run.chores_scheduled = result.metrics.chores_scheduled
    run.mean_daily_load = result.metrics.mean_daily_load
    run.load_variance = result.metrics.load_variance
    run.overloaded_days = result.metrics.overloaded_days
    run.underloaded_days = result.metrics.underloaded_days
    for slot in result.slots:
        occurrence = ChoreOccurrence(
            schedule_run_id=run.id,
            chore_id=slot.chore_id,
            user_id=run.user_id,
            proposed_start_at=slot.start_at,
            proposed_end_at=slot.end_at,
            confidence_score=slot.confidence_score,
            load_score=slot.load_score,
        )
        schedule_repo.add_occurrence(session, occurrence)


async def create_run(
    session: AsyncSession, user_id: str, data_key: bytes, payload: RunRequest
) -> RunDetailOut:
    window_start = datetime.combine(utc_now().date() + timedelta(days=1), time.min)
    seed = payload.seed if payload.seed is not None else secrets.randbelow(2**31)
    run = ScheduleRun(
        user_id=user_id,
        status=RunStatus.running.value,
        window_start=window_start,
        window_end=window_start + timedelta(days=payload.window_days),
        window_days=payload.window_days,
        iterations=payload.iterations,
        seed=seed,
    )
    schedule_repo.add_run(session, run)
    await session.flush()
    specs, busy = await _snapshot(session, user_id, window_start, payload.window_days)
    result = run_monte_carlo(
        ScheduleInput(
            window_start=window_start,
            window_days=payload.window_days,
            chores=specs,
            busy=busy,
            iterations=payload.iterations,
            seed=seed,
        )
    )
    _persist_result(session, run, result)
    await session.commit()
    return await get_run_detail(session, user_id, data_key, run.id)


async def get_run_detail(
    session: AsyncSession, user_id: str, data_key: bytes, run_id: str
) -> RunDetailOut:
    run = await schedule_repo.get_run(session, user_id, run_id)
    if run is None:
        raise ScheduleError(404, "schedule run not found")
    occurrences = await schedule_repo.list_occurrences(session, run.id)
    names = await _chore_names(session, user_id, data_key)
    occurrence_out = [_occurrence_to_out(occ, names) for occ in occurrences]
    return RunDetailOut(**_run_to_out(run).model_dump(), occurrences=occurrence_out)


async def list_runs(session: AsyncSession, user_id: str, limit: int) -> list[RunOut]:
    runs = await schedule_repo.list_runs(session, user_id, limit)
    return [_run_to_out(run) for run in runs]


async def apply_run(
    session: AsyncSession, user_id: str, data_key: bytes, run_id: str
) -> ApplyResponse:
    run = await schedule_repo.get_run(session, user_id, run_id)
    if run is None:
        raise ScheduleError(404, "schedule run not found")
    occurrences = await schedule_repo.list_occurrences(session, run.id)
    pending = [occ for occ in occurrences if occ.status == OccurrenceStatus.proposed.value]
    if not pending:
        raise ScheduleError(409, "run has no proposed occurrences to apply")
    names = await _chore_names(session, user_id, data_key)
    chores = await chore_repo.list_chores(session, user_id)
    attention_by_chore = {chore.id: AttentionClass(chore.attention_class) for chore in chores}
    created = 0
    for occ in pending:
        event_out = await event_service.create_event(
            session,
            user_id,
            data_key,
            EventCreate(
                title=names.get(occ.chore_id, "Chore"),
                event_type=EventType.chore,
                attention_class=attention_by_chore.get(occ.chore_id, AttentionClass.active),
                start_at=occ.proposed_start_at,
                end_at=occ.proposed_end_at,
            ),
            commit=False,
        )
        occ.event_id = event_out.id
        occ.status = OccurrenceStatus.scheduled.value
        created += 1
    # Single commit: a failure mid-loop rolls the whole apply back (idempotent retry).
    await session.commit()
    return ApplyResponse(events_created=created)
