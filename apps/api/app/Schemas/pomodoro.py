"""Pomodoro + residual schemas."""
from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from app.Schemas.base import ApiModel, UtcDateTime


class PomodoroStatus(str, Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"


class PromptStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    completed = "completed"
    timed_out = "timed_out"
    dismissed = "dismissed"


class SessionStart(ApiModel):
    event_id: str
    intended_minutes: int = Field(gt=0, le=8 * 60)


class SessionFinish(ApiModel):
    completion_flag: bool
    meaningful_minutes: int | None = Field(default=None, ge=0, le=24 * 60)
    notes: str | None = Field(default=None, max_length=2000)


class SessionOut(ApiModel):
    id: str
    event_id: str
    intended_minutes: int
    actual_minutes: int | None
    meaningful_minutes: int | None
    status: PomodoroStatus
    completion_flag: bool
    notes: str | None
    started_at: UtcDateTime
    ended_at: UtcDateTime | None


class PromptOut(ApiModel):
    id: str
    pomodoro_session_id: str
    event_id: str
    status: PromptStatus
    prompted_at: UtcDateTime
    timeout_at: UtcDateTime
    user_remaining_minutes: int | None
    residual_id: str | None


class ResidualOut(ApiModel):
    id: str
    origin_event_id: str
    remaining_minutes: int
    session_count: int
    status: str
    next_event_id: str | None


class FinishResponse(ApiModel):
    session: SessionOut
    break_minutes: int
    residual_prompt: PromptOut | None


class PromptRespond(ApiModel):
    response: Literal["completed", "confirmed", "dismissed"]
    remaining_minutes: int | None = Field(default=None, gt=0, le=24 * 60)

    @model_validator(mode="after")
    def check_remaining(self) -> "PromptRespond":
        needs_minutes = self.response == "confirmed" and self.remaining_minutes is None
        if needs_minutes:
            raise ValueError("confirmed response requires remaining_minutes")
        return self


class PromptRespondResponse(ApiModel):
    prompt: PromptOut
    residual: ResidualOut | None
