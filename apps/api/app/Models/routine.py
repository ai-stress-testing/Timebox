"""Routines: reusable ordered step sequences + their executions (spec 013).

Four related tables, one file (same convention as `pomodoro.py`). `routines`
deliberately has NO stored `estimated_minutes` column — it's derived by
summing live `routine_steps.estimated_minutes` on read (see
`routine_service.derived_estimated_minutes`), so it can never drift from its
steps. `routine_steps.position` is kept contiguous (0..n-1) by the service
layer on every add/reorder/delete so the run view's "next step" logic can
stay a simple `position + 1` lookup.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, EntityMixin, utc_now


class Routine(Base, EntityMixin):
    __tablename__ = "routines"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name_enc: Mapped[str] = mapped_column(Text, nullable=False)
    description_enc: Mapped[str | None] = mapped_column(Text, default=None)
    color: Mapped[str] = mapped_column(String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (Index("idx_routines_user", "user_id"),)


class RoutineStep(Base, EntityMixin):
    __tablename__ = "routine_steps"

    routine_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name_enc: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("idx_routine_steps_routine", "routine_id", "position"),
        Index("idx_routine_steps_user", "user_id"),
    )


class RoutineRun(Base, EntityMixin):
    __tablename__ = "routine_runs"

    routine_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="in_progress", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    total_actual_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    event_id: Mapped[str | None] = mapped_column(String(36), default=None)

    __table_args__ = (Index("idx_routine_runs_user", "user_id", "routine_id"),)


class RoutineStepRun(Base, EntityMixin):
    __tablename__ = "routine_step_runs"

    routine_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    routine_step_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    actual_minutes: Mapped[int | None] = mapped_column(Integer, default=None)

    __table_args__ = (Index("idx_routine_step_runs_run", "routine_run_id"),)
