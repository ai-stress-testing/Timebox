"""Routine schemas — ordered step sequences + their executions (spec 013).

`RoutineOut.estimated_minutes` is always the *derived* sum of live steps
(`routine_service.derived_estimated_minutes`), never a stored, driftable
value. `RoutineScheduleRequest` mirrors `TodoScheduleRequest` (issue #12's
funnel) but carries no `end_at` — the block's duration comes entirely from
the routine's derived estimate, not a client-supplied range.
"""
from enum import Enum

from pydantic import Field

from app.Schemas.base import ApiModel, AttentionClassField, CalendarColorField, UtcDateTime
from app.Schemas.event import EventOut


class RoutineRunStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"


class RoutineStepRunStatus(str, Enum):
    pending = "pending"
    active = "active"
    done = "done"
    skipped = "skipped"


# ------------------------------------------------------------------ routine


class RoutineCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    color: CalendarColorField


class RoutinePatch(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    color: CalendarColorField | None = None
    is_active: bool | None = None


class RoutineOut(ApiModel):
    id: str
    name: str
    description: str | None
    color: str
    is_active: bool
    step_count: int
    estimated_minutes: int | None
    created_at: UtcDateTime
    updated_at: UtcDateTime


# ------------------------------------------------------------------- steps


class RoutineStepCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    estimated_minutes: int = Field(gt=0, le=24 * 60)
    is_optional: bool = False


class RoutineStepPatch(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    estimated_minutes: int | None = Field(default=None, gt=0, le=24 * 60)
    is_optional: bool | None = None


class RoutineStepOut(ApiModel):
    id: str
    routine_id: str
    position: int
    name: str
    estimated_minutes: int
    is_optional: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime


class RoutineStepReorderRequest(ApiModel):
    ordered_step_ids: list[str] = Field(min_length=1)


# --------------------------------------------------------------------- runs


class RoutineStepRunOut(ApiModel):
    id: str
    routine_step_id: str
    status: RoutineStepRunStatus
    step_name: str
    estimated_minutes: int
    is_optional: bool
    started_at: UtcDateTime | None
    ended_at: UtcDateTime | None
    actual_minutes: int | None


class RoutineRunOut(ApiModel):
    id: str
    routine_id: str
    status: RoutineRunStatus
    started_at: UtcDateTime
    ended_at: UtcDateTime | None
    total_actual_minutes: int | None
    event_id: str | None
    steps: list[RoutineStepRunOut]


class RoutineAdvanceRequest(ApiModel):
    actual_minutes: int | None = Field(default=None, ge=0, le=24 * 60)
    skipped: bool = False


class RoutineScheduleRequest(ApiModel):
    start_at: UtcDateTime
    event_type: str = Field(min_length=1, max_length=80)
    attention_class: AttentionClassField | None = None


class RoutineScheduleResponse(ApiModel):
    run: RoutineRunOut
    event: EventOut
