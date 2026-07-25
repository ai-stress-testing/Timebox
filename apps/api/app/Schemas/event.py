"""Event schemas — canvas_event_type is server-assigned, never client-set.

`event_type` (on Create/Patch/Out) is a `type_key` string validated dynamically
against the caller's `event_types` rows in the service layer — NOT the static
`EventType` enum in `Schemas.base` (that enum stays for other callers, e.g.
chores, but events opted out so users can define their own types).
"""
from pydantic import Field, field_validator, model_validator

from app.Schemas.base import (
    ApiModel,
    AttentionClass,
    AttentionClassField,
    CalendarColor,
    CalendarColorField,
    CanvasEventType,
    EventStatus,
    EventStatusField,
    UtcDateTime,
)

# Weekday convention shared with chores: Sun=0 .. Sat=6 (see Schemas/chore.py).
_WEEKDAY_RANGE = range(0, 7)


class EventCreate(ApiModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    location: str | None = Field(default=None, max_length=300)
    calendar_id: str | None = None
    event_type: str = Field(min_length=1, max_length=80)
    attention_class: AttentionClassField = AttentionClass.active
    start_at: UtcDateTime
    end_at: UtcDateTime
    is_all_day: bool = False
    estimated_minutes: int | None = Field(default=None, gt=0, le=24 * 60)
    is_recurring: bool = False
    recurrence_weekdays: list[int] = Field(default_factory=list, max_length=7)
    recurrence_end: UtcDateTime | None = None

    @field_validator("recurrence_weekdays")
    @classmethod
    def check_weekdays(cls, days: list[int]) -> list[int]:
        invalid = [d for d in days if d not in _WEEKDAY_RANGE]
        if invalid:
            raise ValueError("recurrence_weekdays must be 0 (Sun) through 6 (Sat)")
        return sorted(set(days))

    @model_validator(mode="after")
    def check_range(self) -> "EventCreate":
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        if self.is_recurring and not self.recurrence_weekdays:
            raise ValueError("recurrence_weekdays must be non-empty when is_recurring")
        return self


class EventPatch(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    location: str | None = Field(default=None, max_length=300)
    calendar_id: str | None = None
    event_type: str | None = Field(default=None, min_length=1, max_length=80)
    attention_class: AttentionClassField | None = None
    status: EventStatusField | None = None
    start_at: UtcDateTime | None = None
    end_at: UtcDateTime | None = None
    is_all_day: bool | None = None
    estimated_minutes: int | None = Field(default=None, gt=0, le=24 * 60)
    actual_minutes: int | None = Field(default=None, ge=0, le=24 * 60)


class EventOut(ApiModel):
    id: str
    calendar_id: str
    title: str
    description: str | None
    location: str | None
    event_type: str
    attention_class: AttentionClass
    canvas_event_type: CanvasEventType
    status: EventStatus
    start_at: UtcDateTime
    end_at: UtcDateTime
    is_all_day: bool
    estimated_minutes: int | None
    actual_minutes: int | None
    residual_of: str | None
    is_recurring: bool
    recurrence_weekdays: list[int]
    recurrence_end: UtcDateTime | None
    master_event_id: str | None
    occurrence_date: str | None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class EventSplitRequest(ApiModel):
    split_at: UtcDateTime


class EventSplitResponse(ApiModel):
    first: EventOut
    second: EventOut


class EventTitleSuggestion(ApiModel):
    """One autocomplete entry: a title the user has used before, how often,
    and the typical duration (learned from prior events of that title).
    """
    title: str
    occurrence_count: int
    avg_minutes: int | None


class EventTypeSummary(ApiModel):
    id: str
    key: str
    label: str
    color: CalendarColor
    is_preset: bool
    is_active: bool
    sort_order: int


class EventTypeCreate(ApiModel):
    label: str = Field(min_length=1, max_length=80)
    color: CalendarColorField


class EventTypePatch(ApiModel):
    label: str | None = Field(default=None, min_length=1, max_length=80)
    color: CalendarColorField | None = None
    is_active: bool | None = None
    sort_order: int | None = None
