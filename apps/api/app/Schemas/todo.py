"""Todo schemas — the to-do-to-schedule funnel (issue #12).

`TodoScheduleRequest.event_type` is a required `type_key` string, validated
dynamically against the caller's `event_types` rows (same convention as
`EventCreate.event_type`, spec 004) — there is no safe hardcoded default
since event types are per-user.
"""
from pydantic import Field, model_validator

from app.Schemas.base import ApiModel, AttentionClassField, UtcDateTime
from app.Schemas.event import EventOut


class TodoCreate(ApiModel):
    title: str = Field(min_length=1, max_length=300)
    estimated_minutes: int | None = Field(default=None, gt=0, le=24 * 60)


class TodoPatch(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    estimated_minutes: int | None = Field(default=None, gt=0, le=24 * 60)
    is_done: bool | None = None


class TodoOut(ApiModel):
    id: str
    title: str
    estimated_minutes: int | None
    is_done: bool
    scheduled_event_id: str | None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class TodoScheduleRequest(ApiModel):
    start_at: UtcDateTime
    end_at: UtcDateTime
    event_type: str = Field(min_length=1, max_length=80)
    attention_class: AttentionClassField | None = None

    @model_validator(mode="after")
    def check_range(self) -> "TodoScheduleRequest":
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class TodoScheduleResponse(ApiModel):
    todo: TodoOut
    event: EventOut
