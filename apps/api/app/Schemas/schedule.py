"""Schedule run schemas — seeded, reproducible, bounded."""
from enum import Enum

from pydantic import Field

from app.Core.config import settings
from app.Schemas.base import ApiModel, UtcDateTime


class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    superseded = "superseded"


class OccurrenceStatus(str, Enum):
    proposed = "proposed"
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    missed = "missed"
    healed = "healed"
    cancelled = "cancelled"


class RunRequest(ApiModel):
    window_days: int = Field(default=settings.mc_default_window_days, ge=1, le=90)
    iterations: int = Field(
        default=settings.mc_default_iterations, ge=1, le=settings.mc_max_iterations
    )
    seed: int | None = Field(default=None, ge=0)


class OccurrenceOut(ApiModel):
    id: str
    chore_id: str
    chore_name: str
    proposed_start_at: UtcDateTime
    proposed_end_at: UtcDateTime
    confidence_score: float
    load_score: float
    status: OccurrenceStatus
    event_id: str | None


class RunOut(ApiModel):
    id: str
    run_type: str
    status: RunStatus
    window_start: UtcDateTime
    window_end: UtcDateTime
    window_days: int
    iterations: int
    seed: int
    score: float | None
    chores_scheduled: int | None
    mean_daily_load: float | None
    load_variance: float | None
    overloaded_days: int | None
    underloaded_days: int | None
    created_at: UtcDateTime
    completed_at: UtcDateTime | None


class RunDetailOut(RunOut):
    occurrences: list[OccurrenceOut]


class ApplyResponse(ApiModel):
    events_created: int
