"""Pomodoro sessions, residual prompts, task residuals (DB-Schemas.md, trimmed)."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, EntityMixin, utc_now


class PomodoroSession(Base, EntityMixin):
    __tablename__ = "pomodoro_sessions"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False)

    intended_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    meaningful_minutes: Mapped[int | None] = mapped_column(Integer, default=None)

    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    completion_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes_enc: Mapped[str | None] = mapped_column(Text, default=None)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    __table_args__ = (Index("idx_pomodoro_user", "user_id", "started_at"),)


class ResidualPrompt(Base, EntityMixin):
    __tablename__ = "residual_prompts"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    pomodoro_session_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False)

    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    prompted_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    timeout_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    user_remaining_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    residual_id: Mapped[str | None] = mapped_column(String(36), default=None)

    __table_args__ = (Index("idx_residual_prompts_user_status", "user_id", "status"),)


class TaskResidual(Base, EntityMixin):
    __tablename__ = "task_residuals"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    origin_event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    origin_session_id: Mapped[str] = mapped_column(String(36), nullable=False)

    remaining_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    session_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)
    next_event_id: Mapped[str | None] = mapped_column(String(36), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    __table_args__ = (Index("idx_residuals_user_status", "user_id", "status"),)
