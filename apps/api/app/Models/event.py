"""Events — typed columns per DB-Schemas.md; sensitive text encrypted at rest."""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, EntityMixin


class Event(Base, EntityMixin):
    __tablename__ = "events"

    calendar_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)

    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    attention_class: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    canvas_event_type: Mapped[str | None] = mapped_column(String(16), default=None)
    status: Mapped[str] = mapped_column(String(16), default="scheduled", nullable=False)

    title_enc: Mapped[str] = mapped_column(Text, nullable=False)
    description_enc: Mapped[str | None] = mapped_column(Text, default=None)
    location_enc: Mapped[str | None] = mapped_column(Text, default=None)

    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Weekly-by-weekday recurrence. A recurring row is the *master*; instances
    # are expanded virtually in the read path (see Pipelines/recurrence.py),
    # never persisted. recurrence_weekdays is a JSON array of ints, Sun=0..Sat=6.
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence_weekdays: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    recurrence_end: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    estimated_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    actual_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    meaningful_minutes: Mapped[int | None] = mapped_column(Integer, default=None)

    residual_of: Mapped[str | None] = mapped_column(String(36), default=None)
    residual_sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chore_occurrence_id: Mapped[str | None] = mapped_column(String(36), default=None)

    __table_args__ = (
        CheckConstraint("end_at > start_at", name="chk_end_after_start"),
        Index("idx_events_user_range", "user_id", "start_at", "end_at"),
        Index("idx_events_calendar_range", "calendar_id", "start_at", "end_at"),
    )
