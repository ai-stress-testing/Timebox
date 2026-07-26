"""Chore schemas — every-n-days frequency with bounds."""
from pydantic import Field, field_validator, model_validator

from app.Core.patterns import TIME_HHMM
from app.Schemas.base import (
    ApiModel,
    AttentionClass,
    AttentionClassField,
    CalendarColor,
    CalendarColorField,
    UtcDateTime,
)

_DAY_RANGE = range(0, 7)


class ChoreCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    estimated_minutes: int = Field(gt=0, le=8 * 60)
    priority: int = Field(default=3, ge=1, le=5)
    attention_class: AttentionClassField = AttentionClass.active
    color: CalendarColorField | None = None
    n_days: int = Field(ge=1, le=365)
    n_min: int = Field(default=1, ge=1)
    n_max: int = Field(default=30, ge=1)
    preferred_days: list[int] = Field(default_factory=list, max_length=7)
    avoid_days: list[int] = Field(default_factory=list, max_length=7)
    preferred_time_start: str | None = None
    preferred_time_end: str | None = None

    @field_validator("preferred_days", "avoid_days")
    @classmethod
    def check_days(cls, days: list[int]) -> list[int]:
        invalid = [d for d in days if d not in _DAY_RANGE]
        if invalid:
            raise ValueError("days must be 0 (Sun) through 6 (Sat)")
        return sorted(set(days))

    @field_validator("preferred_time_start", "preferred_time_end")
    @classmethod
    def check_time(cls, value: str | None) -> str | None:
        if value is not None and not TIME_HHMM.match(value):
            raise ValueError("time must be HH:MM (24h)")
        return value

    @model_validator(mode="after")
    def check_bounds(self) -> "ChoreCreate":
        if self.n_min > self.n_max:
            raise ValueError("n_min must be <= n_max")
        if not self.n_min <= self.n_days <= self.n_max:
            raise ValueError("n_days must lie within [n_min, n_max]")
        return self


class ChorePatch(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    estimated_minutes: int | None = Field(default=None, gt=0, le=8 * 60)
    priority: int | None = Field(default=None, ge=1, le=5)
    attention_class: AttentionClassField | None = None
    color: CalendarColorField | None = None
    n_days: int | None = Field(default=None, ge=1, le=365)
    preferred_days: list[int] | None = Field(default=None, max_length=7)
    avoid_days: list[int] | None = Field(default=None, max_length=7)
    preferred_time_start: str | None = None
    preferred_time_end: str | None = None
    is_active: bool | None = None

    @field_validator("preferred_days", "avoid_days")
    @classmethod
    def check_days(cls, days: list[int] | None) -> list[int] | None:
        if days is None:
            return None
        invalid = [d for d in days if d not in _DAY_RANGE]
        if invalid:
            raise ValueError("days must be 0 (Sun) through 6 (Sat)")
        return sorted(set(days))

    @field_validator("preferred_time_start", "preferred_time_end")
    @classmethod
    def check_time(cls, value: str | None) -> str | None:
        if value is not None and not TIME_HHMM.match(value):
            raise ValueError("time must be HH:MM (24h)")
        return value


class ChoreOut(ApiModel):
    id: str
    name: str
    estimated_minutes: int
    priority: int
    attention_class: AttentionClass
    color: CalendarColor | None
    n_days: int
    n_original: int
    n_current: int
    n_min: int
    n_max: int
    preferred_days: list[int]
    avoid_days: list[int]
    preferred_time_start: str | None
    preferred_time_end: str | None
    is_active: bool
    last_completed_at: UtcDateTime | None
    next_due_at: UtcDateTime | None
    days_until_due: int | None
    recommended_n: int | None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class ChoreComplete(ApiModel):
    completed_at: UtcDateTime | None = None
