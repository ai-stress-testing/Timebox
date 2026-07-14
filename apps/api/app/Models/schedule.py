"""Monte Carlo schedule runs + proposed chore occurrences (DB-Schemas.md, trimmed)."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, EntityMixin


class ScheduleRun(Base, EntityMixin):
    __tablename__ = "schedule_runs"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    run_type: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)

    window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    iterations: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(BigInteger, nullable=False)

    score: Mapped[float | None] = mapped_column(Numeric(10, 4), default=None)
    chores_scheduled: Mapped[int | None] = mapped_column(Integer, default=None)
    mean_daily_load: Mapped[float | None] = mapped_column(Numeric(6, 2), default=None)
    load_variance: Mapped[float | None] = mapped_column(Numeric(8, 4), default=None)
    overloaded_days: Mapped[int | None] = mapped_column(Integer, default=None)
    underloaded_days: Mapped[int | None] = mapped_column(Integer, default=None)

    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    __table_args__ = (Index("idx_schedule_runs_user", "user_id", "created_at"),)


class ChoreOccurrence(Base, EntityMixin):
    __tablename__ = "chore_occurrences"

    schedule_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    chore_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)

    proposed_start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    proposed_end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    load_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="proposed", nullable=False)
    event_id: Mapped[str | None] = mapped_column(String(36), default=None)

    __table_args__ = (
        Index("idx_occurrences_run", "schedule_run_id"),
        Index("idx_occurrences_chore", "chore_id", "proposed_start_at"),
    )
