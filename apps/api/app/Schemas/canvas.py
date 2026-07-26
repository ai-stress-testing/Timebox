"""Canvas item + alarm schemas — timers/stopwatches directly CRUD-able on
the Radial Canvas, optionally linked to a calendar event (spec 010).

`mode`/`status`/`alarm_class`/alarm `status` are plain `Literal` string
unions (same convention as `PromptRespond.response` in Schemas/pomodoro.py)
rather than the `_coerce_enum` Annotated-alias trick in Schemas/base.py —
that trick exists for the shared, cross-feature enums that live in base.py
itself; these are local to canvas and a `Literal` validates identically
under `ApiModel`'s strict mode for client-supplied JSON strings.
"""
from typing import Literal

from pydantic import Field, model_validator

from app.Schemas.base import ApiModel, AttentionClass, AttentionClassField, UtcDateTime

CanvasMode = Literal["timer", "stopwatch"]
CanvasStatus = Literal["running", "paused", "completed"]
AlarmClass = Literal["passive_check", "focus_checkpoint", "break", "refresh"]
AlarmStatus = Literal["pending", "fired", "acknowledged", "snoozed", "dismissed"]

_MAX_DURATION_SECONDS = 24 * 60 * 60


class CanvasItemCreate(ApiModel):
    title: str = Field(min_length=1, max_length=300)
    mode: CanvasMode
    duration_seconds: int | None = Field(default=None, gt=0, le=_MAX_DURATION_SECONDS)
    attention_class: AttentionClassField = AttentionClass.active
    event_id: str | None = None
    r: float = Field(default=0.5, ge=0, le=1)
    theta: float = Field(default=0.0, ge=0, lt=360)

    @model_validator(mode="after")
    def check_timer_has_duration(self) -> "CanvasItemCreate":
        if self.mode == "timer" and self.duration_seconds is None:
            raise ValueError("duration_seconds is required for a timer")
        return self


class CanvasItemPatch(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    duration_seconds: int | None = Field(default=None, gt=0, le=_MAX_DURATION_SECONDS)
    r: float | None = Field(default=None, ge=0, le=1)
    theta: float | None = Field(default=None, ge=0, lt=360)


class CanvasItemOut(ApiModel):
    id: str
    title: str
    mode: CanvasMode
    duration_seconds: int | None
    accumulated_seconds: int
    elapsed_seconds: int
    started_at: UtcDateTime | None
    status: CanvasStatus
    event_id: str | None
    attention_class: AttentionClass
    canvas_event_type: str | None
    r: float
    theta: float
    created_at: UtcDateTime
    updated_at: UtcDateTime


class CanvasAlarmCreate(ApiModel):
    alarm_class: AlarmClass
    label: str | None = Field(default=None, max_length=80)
    offset_seconds: int = Field(ge=-_MAX_DURATION_SECONDS, le=_MAX_DURATION_SECONDS)


class CanvasAlarmPatch(ApiModel):
    """Ack/snooze/dismiss an existing alarm — the only mutations a client
    ever makes to one (creation covers everything else)."""
    status: AlarmStatus | None = None
    snoozed_until: UtcDateTime | None = None


class CanvasAlarmOut(ApiModel):
    id: str
    canvas_item_id: str
    alarm_class: AlarmClass
    label: str | None
    offset_seconds: int
    fires_at: UtcDateTime
    status: AlarmStatus
    fired_at: UtcDateTime | None
    acknowledged_at: UtcDateTime | None
    snoozed_until: UtcDateTime | None
