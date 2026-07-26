"""Canvas items — directly-CRUD timers/stopwatches placed on the Radial
Canvas (spec 010). Not a snapshot/view of `events`: `title_enc` is the
item's own encrypted title, never copied from a linked event. `event_id` is
an optional plain cross-reference (no FK constraint, same convention as
`Event.calendar_id`/`Todo.scheduled_event_id`).
"""
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, EntityMixin, utc_now


class CanvasItem(Base, EntityMixin):
    __tablename__ = "canvas_items"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title_enc: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    accumulated_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    status: Mapped[str] = mapped_column(String(16), default="paused", nullable=False)

    event_id: Mapped[str | None] = mapped_column(String(36), default=None)
    # Snapshot at link time, not a live join (see spec 010) — an unrelated
    # edit to the linked event must not silently reshuffle canvas placement.
    attention_class: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    canvas_event_type: Mapped[str | None] = mapped_column(String(16), default=None)

    r: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5, nullable=False)
    theta: Mapped[float] = mapped_column(Numeric(6, 3), default=0.0, nullable=False)

    __table_args__ = (Index("idx_canvas_items_user", "user_id"),)


class CanvasPositionHistory(Base, EntityMixin):
    __tablename__ = "canvas_position_history"

    canvas_item_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    r_before: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    theta_before: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    r_after: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    theta_after: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    moved_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (Index("idx_canvas_position_history_item", "canvas_item_id"),)


class CanvasAlarm(Base, EntityMixin):
    __tablename__ = "canvas_alarms"

    canvas_item_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    alarm_class: Mapped[str] = mapped_column(String(24), nullable=False)
    label: Mapped[str | None] = mapped_column(String(80), default=None)
    offset_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    fires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    fired_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    __table_args__ = (Index("idx_canvas_alarms_item", "canvas_item_id"),)
