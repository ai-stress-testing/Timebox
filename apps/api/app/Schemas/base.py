"""Shared schema base: strict validation, UTC datetime codec, enums."""
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer


def _to_naive_utc(value: object) -> object:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _serialize_utc(value: datetime) -> str:
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


UtcDateTime = Annotated[
    datetime,
    BeforeValidator(_to_naive_utc),
    PlainSerializer(_serialize_utc, return_type=str),
]


class ApiModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


def _coerce_enum(enum_cls: type[Enum]):  # type: ignore[no-untyped-def]
    def inner(value: object) -> object:
        if isinstance(value, str):
            return enum_cls(value)
        return value

    return BeforeValidator(inner)


class EventType(str, Enum):
    meeting = "meeting"
    task = "task"
    personal = "personal"
    chore = "chore"
    homework = "homework"
    passive = "passive"
    physical = "physical"


class AttentionClass(str, Enum):
    active = "active"
    involved = "involved"
    passive = "passive"


class CanvasEventType(str, Enum):
    focus_only = "focus_only"
    involved_only = "involved_only"
    passive_multi = "passive_multi"
    focus_passive = "focus_passive"


class EventStatus(str, Enum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"
    cancelled = "cancelled"


class CalendarColor(str, Enum):
    slate = "slate"
    rose = "rose"
    amber = "amber"
    violet = "violet"
    emerald = "emerald"
    sky = "sky"
    stone = "stone"
    orange = "orange"


# Request-side annotated aliases: accept the enum's string value under strict
# mode via an explicit, validated coercion (invalid values still 422).
EventTypeField = Annotated[EventType, _coerce_enum(EventType)]
AttentionClassField = Annotated[AttentionClass, _coerce_enum(AttentionClass)]
EventStatusField = Annotated[EventStatus, _coerce_enum(EventStatus)]
CalendarColorField = Annotated[CalendarColor, _coerce_enum(CalendarColor)]
