"""Pomodoro service — sessions, break rule, residual prompt → residual flow."""
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.Core import crypto
from app.dispatch_maps.break_rules import get_break_minutes
from app.Models.base import utc_now
from app.Models.pomodoro import PomodoroSession, ResidualPrompt, TaskResidual
from app.Repositories import event_repo, pomodoro_repo
from app.Schemas.base import AttentionClass
from app.Schemas.pomodoro import (
    FinishResponse,
    PromptOut,
    PromptRespond,
    PromptRespondResponse,
    PromptStatus,
    PomodoroStatus,
    ResidualOut,
    SessionFinish,
    SessionOut,
    SessionStart,
)

_PROMPT_TIMEOUT_MINUTES = 60


class PomodoroError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _session_out(entity: PomodoroSession, data_key: bytes) -> SessionOut:
    notes = crypto.decrypt_field(data_key, entity.notes_enc) if entity.notes_enc else None
    return SessionOut(
        id=entity.id,
        event_id=entity.event_id,
        intended_minutes=entity.intended_minutes,
        actual_minutes=entity.actual_minutes,
        meaningful_minutes=entity.meaningful_minutes,
        status=PomodoroStatus(entity.status),
        completion_flag=entity.completion_flag,
        notes=notes,
        started_at=entity.started_at,
        ended_at=entity.ended_at,
    )


def _prompt_out(prompt: ResidualPrompt) -> PromptOut:
    return PromptOut(
        id=prompt.id,
        pomodoro_session_id=prompt.pomodoro_session_id,
        event_id=prompt.event_id,
        status=PromptStatus(prompt.status),
        prompted_at=prompt.prompted_at,
        timeout_at=prompt.timeout_at,
        user_remaining_minutes=prompt.user_remaining_minutes,
        residual_id=prompt.residual_id,
    )


def _residual_out(residual: TaskResidual) -> ResidualOut:
    return ResidualOut(
        id=residual.id,
        origin_event_id=residual.origin_event_id,
        remaining_minutes=residual.remaining_minutes,
        session_count=residual.session_count,
        status=residual.status,
        next_event_id=residual.next_event_id,
    )


async def start_session(
    session: AsyncSession, user_id: str, data_key: bytes, payload: SessionStart
) -> SessionOut:
    event = await event_repo.get_event(session, user_id, payload.event_id)
    if event is None:
        raise PomodoroError(404, "event not found")
    if event.attention_class != AttentionClass.active.value:
        raise PomodoroError(409, "pomodoro applies only to active-attention events")
    open_session = await pomodoro_repo.get_open_session(session, user_id)
    if open_session is not None:
        raise PomodoroError(409, "a pomodoro session is already open")
    entity = PomodoroSession(
        user_id=user_id, event_id=event.id, intended_minutes=payload.intended_minutes
    )
    pomodoro_repo.add_entity(session, entity)
    event.status = "in_progress"
    await session.commit()
    return _session_out(entity, data_key)


def _close_session(
    entity: PomodoroSession, payload: SessionFinish, data_key: bytes
) -> int:
    ended = utc_now()
    elapsed_minutes = max(1, round((ended - entity.started_at).total_seconds() / 60))
    entity.ended_at = ended
    entity.actual_minutes = elapsed_minutes
    entity.meaningful_minutes = payload.meaningful_minutes
    entity.completion_flag = payload.completion_flag
    entity.status = PomodoroStatus.completed.value
    if payload.notes is not None:
        entity.notes_enc = crypto.encrypt_field(data_key, payload.notes)
    return elapsed_minutes


async def finish_session(
    session: AsyncSession, user_id: str, data_key: bytes, session_id: str, payload: SessionFinish
) -> FinishResponse:
    entity = await pomodoro_repo.get_session_by_id(session, user_id, session_id)
    if entity is None:
        raise PomodoroError(404, "pomodoro session not found")
    if entity.status != PomodoroStatus.active.value:
        raise PomodoroError(409, "session already finished")
    elapsed_minutes = _close_session(entity, payload, data_key)
    event = await event_repo.get_event(session, user_id, entity.event_id)
    prompt: ResidualPrompt | None = None
    if event is not None and payload.completion_flag:
        event.status = "completed"
        event.actual_minutes = (event.actual_minutes or 0) + elapsed_minutes
    if event is not None and not payload.completion_flag:
        event.actual_minutes = (event.actual_minutes or 0) + elapsed_minutes
        prompt = ResidualPrompt(
            user_id=user_id,
            pomodoro_session_id=entity.id,
            event_id=entity.event_id,
            timeout_at=utc_now() + timedelta(minutes=_PROMPT_TIMEOUT_MINUTES),
        )
        pomodoro_repo.add_entity(session, prompt)
    await session.commit()
    return FinishResponse(
        session=_session_out(entity, data_key),
        break_minutes=get_break_minutes(elapsed_minutes),
        residual_prompt=_prompt_out(prompt) if prompt is not None else None,
    )


async def list_sessions(
    session: AsyncSession, user_id: str, data_key: bytes, limit: int
) -> list[SessionOut]:
    sessions = await pomodoro_repo.list_sessions(session, user_id, limit)
    return [_session_out(entity, data_key) for entity in sessions]


async def list_prompts(
    session: AsyncSession, user_id: str, status: str | None
) -> list[PromptOut]:
    prompts = await pomodoro_repo.list_prompts(session, user_id, status)
    return [_prompt_out(prompt) for prompt in prompts]


def _respond_completed(prompt: ResidualPrompt) -> None:
    prompt.status = PromptStatus.completed.value


def _respond_dismissed(prompt: ResidualPrompt) -> None:
    prompt.status = PromptStatus.dismissed.value


async def respond_to_prompt(
    session: AsyncSession, user_id: str, prompt_id: str, payload: PromptRespond
) -> PromptRespondResponse:
    prompt = await pomodoro_repo.get_prompt(session, user_id, prompt_id)
    if prompt is None:
        raise PomodoroError(404, "residual prompt not found")
    if prompt.status != PromptStatus.pending.value:
        raise PomodoroError(409, "prompt already resolved")
    prompt.responded_at = utc_now()
    residual: TaskResidual | None = None
    if payload.response == "confirmed":
        residual = TaskResidual(
            user_id=user_id,
            origin_event_id=prompt.event_id,
            origin_session_id=prompt.pomodoro_session_id,
            remaining_minutes=payload.remaining_minutes or 0,
        )
        pomodoro_repo.add_entity(session, residual)
        await session.flush()
        prompt.status = PromptStatus.confirmed.value
        prompt.user_remaining_minutes = payload.remaining_minutes
        prompt.residual_id = residual.id
    simple_responses = {"completed": _respond_completed, "dismissed": _respond_dismissed}
    handler = simple_responses.get(payload.response)
    if handler is not None:
        handler(prompt)
    await session.commit()
    return PromptRespondResponse(
        prompt=_prompt_out(prompt),
        residual=_residual_out(residual) if residual is not None else None,
    )
